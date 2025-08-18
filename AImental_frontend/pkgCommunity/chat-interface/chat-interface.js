// pages/ai-community/chat-interface/chat-interface.js
const API_BASE_URL = 'https://api.feelyourself.cn/api/v1/community';
const WS_BASE_URL = 'wss://api.feelyourself.cn/api/v1/community';
const app = getApp();

const { getShareInfo, getTimelineInfo } = require('../../utils/share.js');
Page({
  data: {
    // --- 原有 data ---
    statusBarHeight: 0, 
    aiId: null,
    aiName: '',
    aiAvatar: '',
    userAvatar: '',
    aiCurrentStatus: '在线',
    messageList: [],
    scrollToView: '',
    inputValue: '',
    isSendDisabled: true,
    socketTask: null,
    isSocketOpen: false,
    heartbeatTimer: null,
    reconnectTimer: null,
    isLeavingPage: false,
    isAiTyping: false,
    typingTimer: null,
    peekTimer: null,
    
    // --- 功能 data ---
    dailyMessageCount: 0,
    messageLimit: 50,
    isMessageLimitReached: false,
    showCustomModal: false,
    modalTitle: '',
    modalContent: '',

    // --- BUG修复 data ---
    isSending: false, 
  },

  // ---------------------------------------------------
  // 页面生命周期 (已修复)
  // ---------------------------------------------------

  onLoad: function (options) {
    // 【最终修复 1】onLoad 只负责一次性的初始化工作
    const { aiId, name, avatar } = options;
    const userInfo = wx.getStorageSync('userInfo');
    this.setData({
      aiId,
      aiName: decodeURIComponent(name),
      aiAvatar: decodeURIComponent(avatar),
      userAvatar: userInfo ? userInfo.avatar_url : '/images/default-avatar.png',
      statusBarHeight: app.globalData.statusBarHeight || 20
    });
    
    app.webSocketManager.registerListener(this);
    // 初始历史记录只加载一次
    this.loadInitialDataWithFallback();
  },

  // 【最终修复 1】新增 onShow 生命周期，处理每次页面显示时的逻辑
  onShow: function() {
    console.log("页面显示 (onShow)，开始刷新状态...");
    // 每次进入页面，都重新检查消息限制，确保状态持久
    this.checkMessageLimit();
    // 每次进入页面，都启动“窥视”心跳
    this.notifyPeek();
    this.startPeeking();
  },

  // 【最终修复 1】新增 onHide 生命周期，处理页面隐藏
  onHide: function() {
    // 页面隐藏时，停止窥视心跳，节省资源
    console.log("页面隐藏 (onHide)，停止窥视心跳。");
    this.stopPeeking();
  },

  onUnload: function() {
    // 页面被销毁时，注销监听器
    app.webSocketManager.unregisterListener();
    this.stopPeeking(); // 双重保险
  },

  // ---------------------------------------------------
  // 核心功能函数 (已修复)
  // ---------------------------------------------------
  
  checkMessageLimit: function() {
    this._request({
      url: `/chats/status`,
      method: 'GET',
    }).then(res => {
      console.log("获取消息限制状态:", res);
      const limitReached = res.daily_count >= res.limit;
      this.setData({
        dailyMessageCount: res.daily_count,
        messageLimit: res.limit,
        isMessageLimitReached: limitReached,
        isSendDisabled: !this.data.inputValue.trim() || limitReached || this.data.isSending
      });
    }).catch(err => {
      console.error("获取消息限制状态失败:", err);
    });
  },

  showLimitModal: function(content) {
    this.setData({
      showCustomModal: true,
      modalTitle: '提示',
      modalContent: content
    });
  },
  
  onModalConfirm: function() {
    this.setData({
      showCustomModal: false
    });
  },

  onInput: function(e) {
    const value = e.detail.value;
    this.setData({ 
      inputValue: value,
      isSendDisabled: !value.trim() || this.data.isMessageLimitReached || this.data.isSending
    });
  },

  sendMessage: function() {
    if (this.data.isSending) {
      console.warn("正在发送中，请勿重复点击...");
      return;
    }

    if (this.data.isMessageLimitReached) {
      this.showLimitModal(`您今天发送的总消息条数已经达到${this.data.messageLimit}条限额啦~明天再来吧~`);
      return;
    }
    
    if (this.data.isSendDisabled) return;

    const content = this.data.inputValue.trim();
    if (!content) {
        return;
    }
    
    const tempId = Date.now() + '_user';
    const userMessage = {
      id: tempId,
      role: 'user',
      content: content,
      time: this.formatTimestamp(Date.now() / 1000),
      status: 'sending' 
    };

    this.setData({
      messageList: [...this.data.messageList, userMessage],
      inputValue: '',
      isSendDisabled: true,
      isSending: true,      
    });

    this.scrollToBottom();

    this._request({
      url: `/chats/${this.data.aiId}/messages`,
      method: 'POST',
      data: { content },
      success: (data) => {
        const newCount = this.data.dailyMessageCount + 1;
        const limitReached = newCount >= this.data.messageLimit;
        this.setData({
            dailyMessageCount: newCount,
            isMessageLimitReached: limitReached,
            isSendDisabled: limitReached,
        });
        setTimeout(() => {
          this.updateMessageStatus(tempId, 'sent');
        }, 1000);
      },
      fail: (err) => {
        console.error("发送失败:", err);

        if (err && err.statusCode === 429) {
          this.showLimitModal(err.data.detail || '今日消息已达上限');
          this.setData({
              isMessageLimitReached: true,
              isSendDisabled: true
          });
          const currentMessageList = this.data.messageList;
          const messageIndex = currentMessageList.findIndex(msg => msg.id === tempId);
          if (messageIndex !== -1) {
            currentMessageList.splice(messageIndex, 1);
            this.setData({
              messageList: currentMessageList,
              // 【最终修复 2】不再把内容放回输入框，而是确保它被清空
              inputValue: '' 
            });
          }
        } else {
          this.updateMessageStatus(tempId, 'failed');
        }
      }
    })
    .catch(err => {
      console.log("Promise rejection has been handled gracefully.");
    })
    .finally(() => {
      this.setData({ 
        isSending: false,
        isSendDisabled: !this.data.inputValue.trim() || this.data.isMessageLimitReached
      });
    });
  },
  
  // ---------------------------------------------------
  // 其他所有原有函数 (保持不变)
  // ---------------------------------------------------

  onSocketMessage: function(data) {
    if (data.type === 'new_message' && data.from_character_id === this.data.aiId) {
      this.handleNewMessage(data.message);
    }
  },

  startPeeking: function() {
    this.stopPeeking(); 
    const timer = setInterval(() => {
        this.notifyPeek();
    }, 15000);
    this.setData({ peekTimer: timer });
  },

  stopPeeking: function() {
    if (this.data.peekTimer) {
        clearInterval(this.data.peekTimer);
        this.setData({ peekTimer: null });
    }
  },

  notifyPeek: function() {
    if (!this.data.aiId) return;
    this._request({
        url: `/chats/${this.data.aiId}/peek`,
        method: 'POST',
    }).catch(err => {
        console.warn("Notify peek failed:", err);
    });
  },

  handleNewMessage: function(message) {
    const newMessage = {
      id: (message.timestamp || Date.now()) + '_' + Math.random().toString(36).substr(2, 9),
      role: 'ai',
      content: message.content,
      time: this.formatTimestamp(message.timestamp),
      status: 'received'
    };
    clearTimeout(this.data.typingTimer);
    let lastUserMsgIndex = -1;
    for (let i = this.data.messageList.length - 1; i >= 0; i--) {
      if (this.data.messageList[i].role === 'user' && this.data.messageList[i].status === 'sent') {
        lastUserMsgIndex = i;
        break;
      }
    }
    const updatePath = lastUserMsgIndex !== -1 ? `messageList[${lastUserMsgIndex}].status` : '';
    const updates = {
      messageList: [...this.data.messageList, newMessage],
      isAiTyping: true,
    };
    if (updatePath) {
      updates[updatePath] = 'read';
    }
    this.setData(updates);
    this.scrollToBottom();
    const typingTimer = setTimeout(() => {
      this.setData({ isAiTyping: false });
    }, 2500);
    this.setData({ typingTimer });
  },

  loadInitialDataWithFallback: function() {
    this._request({
      url: `/chats/${this.data.aiId}/details`,
      success: (data) => {
        // --- 【核心调试代码】 在这里打印后端返回的完整数据 ---
        console.log("========== 角色状态调试日志 BEGIN ==========");
        console.log("当前请求的角色ID (aiId):", this.data.aiId);
        console.log("后端 /details 接口返回的原始数据 (data):", data);
        console.log("从数据中提取的角色状态 (data.character_status):", data.character_status);
        console.log("========== 角色状态调试日志 END ==========");
        // --- 【调试代码结束】 ---
        const formattedMessages = this.formatMessages(data.history);
        this.setData({ 
          messageList: formattedMessages,
          aiCurrentStatus: data.character_status || '在线'
        });
        this.scrollToBottom();

      },
      fail: () => {
        console.warn("'/details' endpoint failed. Falling back to history only.");
        this._request({
          url: `/chats/${this.data.aiId}`,
          success: (historyData) => {
            const formattedMessages = this.formatMessages(historyData);
            this.setData({ 
              messageList: formattedMessages,
              aiCurrentStatus: '在线' 
            });
            this.scrollToBottom();
          },
          fail: () => wx.showToast({ title: '加载历史消息失败', icon: 'none' })
        });
      }
    });
  },
  
  _request: function(options) {
    return new Promise((resolve, reject) => {
        const token = wx.getStorageSync('token');
        if (!token) { 
            wx.showToast({ title: '请先登录', icon: 'none' });
            if(options.fail) options.fail({errMsg: 'No Token'});
            reject({errMsg: 'No Token'});
            return; 
        }
        wx.request({
            url: API_BASE_URL + options.url,
            method: options.method || 'GET',
            header: { 'Authorization': `Bearer ${token}` },
            data: options.data || {},
            success: (res) => {
                if (res.statusCode >= 200 && res.statusCode < 300) {
                    if(options.success) options.success(res.data);
                    resolve(res.data);
                } else {
                    if(options.fail) options.fail(res);
                    reject(res);
                }
            },
            fail: (err) => { 
                if(options.fail) options.fail(err);
                reject(err);
            }
        });
    });
  },
  
  updateMessageStatus: function(id, status) {
    const index = this.data.messageList.findIndex(msg => msg.id === id);
    if (index !== -1) {
      this.setData({
        [`messageList[${index}].status`]: status
      });
    }
  },
  
  scrollToBottom: function() {
    if (this.data.messageList.length > 0) {
      const lastMessage = this.data.messageList[this.data.messageList.length - 1];
      this.setData({ scrollToView: `msg-${lastMessage.id}` });
    }
  },
  
  formatTimestamp: function(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp * 1000);
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
  },

  formatMessages: function(messages) {
    if (!messages || !Array.isArray(messages)) return [];
    return messages.map(msg => ({
      ...msg,
      id: (msg.timestamp || Date.now()) + '_' + Math.random().toString(36).substr(2, 9),
      time: this.formatTimestamp(msg.timestamp),
      status: msg.role === 'user' ? 'read' : 'received'
    }));
  },

  navigateBack: function() {
    wx.navigateBack();
  },

  onShareAppMessage: function () {
    return getShareInfo();
  },

  onShareTimeline: function () {
    return getTimelineInfo();
  }
});