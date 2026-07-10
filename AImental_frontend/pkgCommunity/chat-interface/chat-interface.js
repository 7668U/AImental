// pages/ai-community/chat-interface/chat-interface.js
const API_BASE_URL = 'http://127.0.0.1:8000/api/v1/community';
const WS_BASE_URL = 'ws://127.0.0.1:8000/api/v1/community';
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
    isProfileCardVisible: false,
    aiProfile: null,
    profileSections: [],
    profileTags: [],
    profileMotto: '',
    affinityHeartSrc: '/images/community-affinity/affinity-heart-000.png',
    affinityScoreText: '0',
    affinityStage: '初识观察',
    affinityNote: '还在初识阶段，适合保持自然、礼貌和不过度亲密的距离。',
    hasAffinityContext: false,

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
      userAvatar: userInfo ? userInfo.avatar_url : 'https://assets.feelyourself.cn/miniprogram/assets/v1/images/default-avatar.png',
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
    this.setData({ isLeavingPage: true });
    app.webSocketManager.unregisterListener();
    this.stopPeeking(); // 双重保险
    this.clearResponsePolling();
    this.clearTypingTimer();
  },

  // ---------------------------------------------------
  // 核心功能函数 (已修复)
  // ---------------------------------------------------

  buildProfileCardData: function(profile = {}) {
    const identity = profile.identity_core || {};
    const traits = profile.personality_traits || {};
    const dialogue = profile.dialogue_style || {};
    const background = profile.background_story || {};
    const lifestyle = profile.lifestyle || {};
    const sections = [];

    const addSection = (label, value, iconKey, iconSrc = '') => {
      if (value === undefined || value === null || value === '') return;
      const displayValue = Array.isArray(value) ? value.join('、') : String(value);
      if (displayValue.trim()) {
        sections.push({ label, value: displayValue, iconKey, iconSrc });
      }
    };

    addSection('MBTI', traits.mbti, 'mbti', '/images/community-profile/profile-icon-mbti-2x.png');
    addSection('说话风格', dialogue.style_summary, 'speech');
    addSection('家乡', background.hometown, 'home');
    addSection('背景', background.background, 'book');
    addSection('喜欢', lifestyle.hobbies, 'like');
    addSection('不喜欢', lifestyle.dislikes, 'dislike');

    return {
      profileSections: sections,
      profileTags: Array.isArray(traits.personality_tags) ? traits.personality_tags : [],
      profileMotto: traits.philosophy || ''
    };
  },

  buildAffinityDisplay: function(context = {}) {
    const rawScore = Number(context.score || 0);
    const score = Math.max(0, Math.min(100, Number.isFinite(rawScore) ? rawScore : 0));
    let level = 0;
    if (score >= 90) {
      level = 100;
    } else if (score >= 70) {
      level = 80;
    } else if (score >= 50) {
      level = 60;
    } else if (score >= 30) {
      level = 40;
    } else if (score >= 10) {
      level = 20;
    }

    const levelText = String(level).padStart(3, '0');
    return {
      affinityHeartSrc: `/images/community-affinity/affinity-heart-${levelText}.png`,
      affinityScoreText: String(Math.round(score)),
      affinityStage: context.stage || '初识观察',
      affinityNote: context.affinity_note || '关系还在慢慢升温，先自然地聊下去就好。',
      hasAffinityContext: true
    };
  },

  showProfileCard: function() {
    this.setData({ isProfileCardVisible: true });
  },

  showProfileCardOnFirstVisit: function() {
    if (!this.data.aiId || !this.data.aiProfile) return;
    const storageKey = `community_profile_seen_${this.data.aiId}`;
    const hasSeenProfile = wx.getStorageSync(storageKey);
    if (hasSeenProfile) return;

    wx.setStorageSync(storageKey, true);
    this.showProfileCard();
  },

  hideProfileCard: function() {
    this.setData({ isProfileCardVisible: false });
  },

  noop: function() {},

  scheduleResponsePollingIfNeeded: function() {
    const wsManager = app.webSocketManager || {};
    if (wsManager.isSocketOpen) return;

    this.clearResponsePolling();
    let attempts = 0;
    const poll = () => {
      if (this.data.isLeavingPage) return;
      attempts += 1;
      this.loadInitialDataWithFallback();
      if (attempts < 6) {
        this.responseRefreshTimer = setTimeout(poll, 5000);
      }
    };

    this.responseRefreshTimer = setTimeout(poll, 6000);
  },

  clearResponsePolling: function() {
    if (this.responseRefreshTimer) {
      clearTimeout(this.responseRefreshTimer);
      this.responseRefreshTimer = null;
    }
  },

  clearTypingTimer: function() {
    if (this.data.typingTimer) {
      clearTimeout(this.data.typingTimer);
      this.setData({ typingTimer: null });
    }
  },

  finishAiReplyState: function() {
    this.clearTypingTimer();
    this.setData({
      isSending: false,
      isAiTyping: false,
      isSendDisabled: !this.data.inputValue.trim() || this.data.isMessageLimitReached
    });
  },

  getNextReplyDelay: function(message, index) {
    const textLength = message && message.content ? String(message.content).length : 0;
    const baseDelay = index === 0 ? 700 : 820;
    const readingDelay = Math.min(textLength * 22, 520);
    return baseDelay + readingDelay;
  },

  appendAiMessagesSequentially: function(messages, onComplete) {
    const aiMessages = Array.isArray(messages) ? messages : [];
    if (!aiMessages.length) {
      if (onComplete) onComplete();
      return;
    }

    let index = 0;
    const appendNext = () => {
      if (this.data.isLeavingPage) return;
      const msg = aiMessages[index];
      const newMessage = {
        id: (msg.timestamp || Date.now()) + '_' + Math.random().toString(36).substr(2, 9),
        role: 'ai',
        content: msg.content,
        time: this.formatTimestamp(msg.timestamp || Date.now() / 1000),
        status: 'received'
      };

      const updates = {
        messageList: [...this.data.messageList, newMessage],
      };

      this.setData(updates);
      this.scrollToBottom();
      index += 1;

      if (index < aiMessages.length) {
        const timer = setTimeout(appendNext, this.getNextReplyDelay(aiMessages[index], index));
        this.setData({ typingTimer: timer });
      } else if (onComplete) {
        const timer = setTimeout(onComplete, 520);
        this.setData({ typingTimer: timer });
      }
    };

    const timer = setTimeout(appendNext, this.getNextReplyDelay(aiMessages[0], 0));
    this.setData({ typingTimer: timer });
  },
  
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
        isSendDisabled: !this.data.inputValue.trim() || limitReached || this.data.isSending || this.data.isAiTyping
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
      isSendDisabled: !value.trim() || this.data.isMessageLimitReached || this.data.isSending || this.data.isAiTyping
    });
  },

  sendMessage: function() {
    if (this.data.isSending || this.data.isAiTyping) {
      wx.showToast({ title: '对方正在回复您哦~稍后再发吧', icon: 'none' });
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
      time: this.formatTimestamp(Date.now() / 1000)
    };

    this.setData({
      messageList: [...this.data.messageList, userMessage],
      inputValue: '',
      isSendDisabled: true,
      isSending: true,
      isAiTyping: true,
    });

    this.scrollToBottom();

    this._request({
      url: `/chats/${this.data.aiId}/messages`,
      method: 'POST',
      timeout: 120000,
      data: { content },
      success: (data) => {
        const returnedCount = typeof data.daily_count === 'number' && data.daily_count >= 0
          ? data.daily_count
          : this.data.dailyMessageCount + 1;
        const newCount = returnedCount;
        const limitReached = newCount >= this.data.messageLimit;
        this.setData({
            dailyMessageCount: newCount,
            isMessageLimitReached: limitReached,
            isSendDisabled: true,
            aiCurrentStatus: data.character_status || this.data.aiCurrentStatus,
        });
        setTimeout(() => {
          this.appendAiMessagesSequentially(data.ai_messages || [], () => {
            this.finishAiReplyState();
          });
        }, 180);
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
        } else if (err && err.statusCode === 409) {
          wx.showToast({ title: err.data.detail || '对方正在回复您哦~稍后再发吧', icon: 'none' });
          const currentMessageList = this.data.messageList;
          const messageIndex = currentMessageList.findIndex(msg => msg.id === tempId);
          if (messageIndex !== -1) {
            currentMessageList.splice(messageIndex, 1);
            this.setData({ messageList: currentMessageList });
          }
        } else {
          this.updateMessageStatus(tempId, 'failed');
        }
        this.finishAiReplyState();
      }
    })
    .catch(err => {
      console.log("Promise rejection has been handled gracefully.");
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
    const updates = {
      messageList: [...this.data.messageList, newMessage],
      isAiTyping: true,
    };
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
        const formattedMessages = this.formatMessages(data.history);
        const character = data.character || {};
        const profile = character.profile || null;
        const profileCardData = this.buildProfileCardData(profile || {});
        const affinityDisplay = this.buildAffinityDisplay(data.favorability_context || {});
        const backendBaseUrl = API_BASE_URL.replace('/api/v1/community', '');
        const avatarUrl = character.avatar_url
          ? (character.avatar_url.startsWith('http') ? character.avatar_url : backendBaseUrl + character.avatar_url)
          : this.data.aiAvatar;

        this.setData({ 
          messageList: formattedMessages,
          aiCurrentStatus: data.character_status || '在线',
          aiName: character.name || this.data.aiName,
          aiAvatar: avatarUrl,
          aiProfile: profile,
          ...affinityDisplay,
          ...profileCardData
        }, () => {
          this.showProfileCardOnFirstVisit();
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
            timeout: options.timeout || 60000,
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
    
      return messages.map((msg, index) => {
        return {
          ...msg,
          id: (msg.timestamp || Date.now()) + '_' + Math.random().toString(36).substr(2, 9),
          time: this.formatTimestamp(msg.timestamp)
        }
      });
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
