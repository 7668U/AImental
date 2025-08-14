// pages/ai-community/chat-interface/chat-interface.js (最终完整版)
const API_BASE_URL = 'http://127.0.0.1:8000/api/v1/community';
const WS_BASE_URL = 'ws://127.0.0.1:8000/api/v1/community';
const app = getApp(); // 在文件顶部获取 App 实例，以便多处使用

Page({
  data: {
    // --- 您的所有原有 data 字段，完全保留 ---
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
    socketTask: null, // (虽然未使用，但为您保留)
    isSocketOpen: false, // (虽然未使用，但为您保留)
    heartbeatTimer: null, // (虽然未使用，但为您保留)
    reconnectTimer: null, // (虽然未使用，但为您保留)
    isLeavingPage: false, // (虽然未使用，但为您保留)
    isAiTyping: false,
    typingTimer: null,

    // --- 【新增】“用户窥视”心跳计时器 ---
    peekTimer: null,
  },

  // --- 页面生命周期 ---

  onLoad: function (options) {
    // 【保留】您的原有功能：获取页面参数和用户信息
    const { aiId, name, avatar } = options;
    const userInfo = wx.getStorageSync('userInfo');
    this.setData({
      aiId,
      aiName: decodeURIComponent(name),
      aiAvatar: decodeURIComponent(avatar),
      userAvatar: userInfo ? userInfo.avatar_url : '/images/default-avatar.png',
      // 从全局获取状态栏高度
      statusBarHeight: app.globalData.statusBarHeight || 20

    });
  
    // 【保留】您的原有功能：接入全局WebSocket管理器
    app.webSocketManager.registerListener(this);
  
    // 【保留】您的原有功能：加载初始聊天记录
    this.loadInitialDataWithFallback();

    // 【新增】启动“用户窥视”逻辑
    this.notifyPeek();
    this.startPeeking();
  },

  onUnload: function() {
    // 【保留】您的原有功能：从全局管理器注销
    app.webSocketManager.unregisterListener();

    // 【新增】停止“用户窥视”心跳
    this.stopPeeking();
  },

  // --- WebSocket 消息处理 (您的原有设计，完全保留) ---
  onSocketMessage: function(data) {
    console.log('聊天页面: 从全局管理器收到消息:', data);
    if (data.type === 'new_message' && data.from_character_id === this.data.aiId) {
      this.handleNewMessage(data.message);
    }
  },

  // --- 【核心新增】“用户窥视”心跳逻辑 ---
  startPeeking: function() {
    this.stopPeeking(); 
    const timer = setInterval(() => {
        this.notifyPeek();
    }, 15000); // 每15秒通知一次，确保“已窥视”状态持续有效
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
    // 调用我们新增的 /peek 接口
    this._request({
        url: `/chats/${this.data.aiId}/peek`,
        method: 'POST',
        // 【优化】这是一个即发即忘的请求，不需要 success 和 fail 回调
    }).catch(err => {
        console.warn("Notify peek failed:", err);
    });
  },

  // --- 您的所有其他函数，全部原封不动地保留 ---

  // --- 旧的WebSocket核心逻辑 (虽然不再被调用，但为您保留代码作为参考) ---
  connectWebSocket: function() { /* 已被全局管理器替代 */ },
  bindSocketEvents: function() { /* 已被全局管理器替代 */ },
  closeWebSocket: function(isLeaving = false) { /* 已被全局管理器替代 */ },
  reconnect: function() { /* 已被全局管理器替代 */ },
  clearReconnectTimer: function() { /* 已被全局管理器替代 */ },
  startHeartbeat: function() { /* 已被全局管理器替代 */ },
  stopHeartbeat: function() { /* 已被全局管理器替代 */ },

  // --- 消息处理 (完全保留) ---
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

  // --- HTTP API 请求 (完全保留) ---
  loadInitialDataWithFallback: function() {
    this._request({
      url: `/chats/${this.data.aiId}/details`,
      success: (data) => {
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
    // 【优化】为您原来的 _request 函数增加了 Promise 支持，使其更现代化
    // 这样既兼容您原来的 success/fail 写法，也能支持 .catch()
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
  
  // --- 页面交互 (完全保留) ---
  onInput: function(e) {
    const value = e.detail.value;
    this.setData({ 
      inputValue: value,
      isSendDisabled: !value.trim() 
    });
  },

  sendMessage: function() {
    if (this.data.isSendDisabled) return;
    const content = this.data.inputValue.trim();
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
      isSendDisabled: true
    });
    this.scrollToBottom();
    this._request({
      url: `/chats/${this.data.aiId}/messages`,
      method: 'POST',
      data: { content },
      success: (data) => {
        setTimeout(() => {
          this.updateMessageStatus(tempId, 'sent');
        }, 2000); // 优化了延迟
      },
      fail: () => {
        this.updateMessageStatus(tempId, 'failed');
      }
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
  
  // --- 工具函数 (完全保留) ---
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
  }
});