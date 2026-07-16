// pages/ai-community/chat-interface/chat-interface.js
const API_BASE_URL = 'http://127.0.0.1:8000/api/v1/community';
const SERVER_BASE_URL = API_BASE_URL.replace('/api/v1/community', '');
const CDN_ASSET_BASE_URL = 'https://assets.feelyourself.cn/miniprogram/assets/v1';
const DEFAULT_USER_AVATAR = `${CDN_ASSET_BASE_URL}/images/default-avatar.png`;
const COMMUNITY_PROFILE_MBTI_ICON = '/images/community-profile-mbti.png';
const REPLY_STATUS_POLL_INTERVAL_MS = 1500;
const app = getApp();

const { getShareInfo, getTimelineInfo } = require('../../utils/share.js');
const {
  isVipQuotaExhaustedError,
  showVipQuotaModal,
} = require('../../utils/vip-quota.js');
Page({
  data: {
    // --- 原有 data ---
    statusBarHeight: 0,
    navBarHeight: 44,
    topBarOffset: 64,
    aiId: null,
    aiName: '',
    aiAvatar: '',
    userAvatar: '',
    aiCurrentStatus: '在线',
    messageList: [],
    scrollTop: 0,
    scrollWithAnimation: false,
    inputValue: '',
    isSendDisabled: true,
    isLeavingPage: false,
    isAiTyping: false,
    typingTimer: null,
    peekTimer: null,
    
    // --- 功能 data ---
    dailyMessageCount: 0,
    messageLimit: 50,
    remainingMessageCount: 50,
    isMessageLimitReached: false,
    showCustomModal: false,
    modalTitle: '',
    modalContent: '',
    isProfileCardVisible: false,
    aiProfile: null,
    profileSections: [],
    profileTags: [],
    profileMotto: '',
    profileIdentityText: '',
    affinityHeartSrc: `${CDN_ASSET_BASE_URL}/images/community-affinity/affinity-heart-000.png`,
    affinityScoreText: '0',
    affinityProgress: 4,
    affinityStage: '初识观察',
    affinityNote: '还在初识阶段，适合保持自然、礼貌和不过度亲密的距离。',
    hasAffinityContext: false,
    isEmojiPanelVisible: false,
    emojiOptions: ['😊', '🙂', '😌', '🥰', '🤗', '😢', '😭', '😔', '😴', '😮', '😤', '✨', '🌙', '☀️', '🍀', '💛', '🧡', '👍'],
    isRewinding: false,
    isHistoryLoading: true,
    isHistoryLoadFailed: false,

    // --- BUG修复 data ---
    isSending: false, 
  },

  // ---------------------------------------------------
  // 页面生命周期 (已修复)
  // ---------------------------------------------------

  getNavigationMetrics: function() {
    let statusBarHeight = app.globalData.statusBarHeight || 20;
    let navBarHeight = app.globalData.compactNavBarHeight || 44;
    let topBarOffset = statusBarHeight + navBarHeight;

    try {
      const windowInfo = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
      const menuButtonInfo = wx.getMenuButtonBoundingClientRect();
      statusBarHeight = windowInfo.statusBarHeight || statusBarHeight;

      if (menuButtonInfo && menuButtonInfo.height) {
        const navGap = Math.max(0, menuButtonInfo.top - statusBarHeight);
        navBarHeight = menuButtonInfo.height + navGap * 2;
      }

      if (menuButtonInfo && typeof menuButtonInfo.bottom === 'number') {
        topBarOffset = Math.ceil(menuButtonInfo.bottom + 6);
      } else {
        topBarOffset = statusBarHeight + navBarHeight;
      }
    } catch (error) {
      console.warn('获取导航栏安全区失败，使用默认值', error);
    }

    return {
      statusBarHeight,
      navBarHeight,
      topBarOffset
    };
  },

  resolveUserAvatar: function(userInfo = {}) {
    const avatar = userInfo.avatar_url || userInfo.avatarUrl || userInfo.avatar || '';
    if (!avatar) return DEFAULT_USER_AVATAR;
    if (avatar.startsWith('/images/')) return `${CDN_ASSET_BASE_URL}${avatar}`;
    if (avatar.startsWith('/')) return `${SERVER_BASE_URL}${avatar}`;
    return avatar;
  },

  onLoad: function (options) {
    // 【最终修复 1】onLoad 只负责一次性的初始化工作
    const { aiId, name, avatar } = options;
    const userInfo = wx.getStorageSync('userInfo');
    const navigationMetrics = this.getNavigationMetrics();
    this.setData({
      aiId,
      aiName: decodeURIComponent(name),
      aiAvatar: decodeURIComponent(avatar),
      userAvatar: this.resolveUserAvatar(userInfo || {}),
      ...navigationMetrics
    });
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
    // 页面重载后，本地请求状态会丢失，需要向服务端确认是否仍在生成回复。
    this.refreshReplyProgress();
  },

  // 【最终修复 1】新增 onHide 生命周期，处理页面隐藏
  onHide: function() {
    // 页面隐藏时，停止窥视心跳，节省资源
    console.log("页面隐藏 (onHide)，停止窥视心跳。");
    this.stopPeeking();
    this.stopReplyRecoveryPolling();
    if (this.data.isEmojiPanelVisible) {
      this.setData({ isEmojiPanelVisible: false });
    }
  },

  onUnload: function() {
    // 页面被销毁时，注销监听器
    this.setData({ isLeavingPage: true });
    this.stopPeeking(); // 双重保险
    this.stopReplyRecoveryPolling();
    this.clearTypingTimer();
  },

  // ---------------------------------------------------
  // 核心功能函数 (已修复)
  // ---------------------------------------------------

  buildProfileCardData: function(profile = {}) {
    const traits = profile.personality_traits || {};
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

    addSection('MBTI', traits.mbti, 'mbti', COMMUNITY_PROFILE_MBTI_ICON);
    addSection('家乡', background.hometown, 'home');
    addSection('背景', background.background, 'book');
    addSection('喜欢', lifestyle.hobbies, 'like');

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
      affinityHeartSrc: `${CDN_ASSET_BASE_URL}/images/community-affinity/affinity-heart-${levelText}.png`,
      affinityScoreText: String(Math.round(score)),
      affinityProgress: Math.max(4, Math.round(score)),
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

  showTimeRewindConfirm: function() {
    if (this.data.isRewinding) return;

    if (this.data.isSending || this.data.isAiTyping) {
      wx.showToast({ title: '请等待当前回复完成', icon: 'none' });
      return;
    }

    wx.showModal({
      title: '时间回溯',
      content: '时间回溯会清空所有聊天历史和好感度，让你们回到初遇时刻，确定要回溯吗？',
      confirmText: '确定回溯',
      cancelText: '取消',
      confirmColor: '#c94f45',
      success: (result) => {
        if (result.confirm) {
          this.rewindConversation();
        }
      }
    });
  },

  rewindConversation: function() {
    if (!this.data.aiId || this.data.isRewinding) return;

    this.setData({ isRewinding: true });
    wx.showLoading({ title: '正在回溯...', mask: true });

    this._request({
      url: `/chats/${this.data.aiId}/rewind`,
      method: 'POST',
      timeout: 30000,
      success: (data) => {
        const formattedMessages = this.formatMessages(data.history || []);
        const affinityDisplay = this.buildAffinityDisplay(data.favorability_context || {});
        this.clearTypingTimer();
        this.setData({
          messageList: formattedMessages,
          inputValue: '',
          isSendDisabled: true,
          isSending: false,
          isAiTyping: false,
          isProfileCardVisible: false,
          isRewinding: false,
          ...affinityDisplay
        }, () => {
          this.scrollToBottom({ animate: false });
        });
        wx.showToast({ title: '已回到初遇时刻', icon: 'success' });
      },
      fail: (err) => {
        this.setData({ isRewinding: false });
        wx.showToast({
          title: (err && err.data && err.data.detail) || '时间回溯失败，请稍后重试',
          icon: 'none'
        });
      },
      complete: () => {
        wx.hideLoading();
      }
    }).catch(() => {
      console.log('Time rewind rejection has been handled.');
    });
  },

  noop: function() {},

  hashMessageContent: function(content) {
    const text = String(content || '');
    let hash = 0;
    for (let i = 0; i < text.length; i += 1) {
      hash = ((hash << 5) - hash + text.charCodeAt(i)) >>> 0;
    }
    return hash.toString(36);
  },

  buildMessageId: function(message, index = 0) {
    const role = message && message.role ? message.role : 'msg';
    const timestamp = message && message.timestamp ? message.timestamp : 0;
    const hash = this.hashMessageContent(message && message.content);
    return `${role}-${timestamp}-${index}-${hash}`;
  },

  normalizeMessage: function(message, index = 0) {
    const timestamp = Number(message && message.timestamp ? message.timestamp : Date.now() / 1000);
    return {
      ...(message || {}),
      id: (message && message.id) || this.buildMessageId(message || {}, index),
      timestamp,
      time: this.formatTimestamp(timestamp),
      status: (message && message.status) || 'received'
    };
  },

  hasMessage: function(targetMessage) {
    if (!targetMessage) return false;
    return (this.data.messageList || []).some((message) => {
      if (message.id && targetMessage.id && message.id === targetMessage.id) return true;
      return message.role === targetMessage.role
        && Number(message.timestamp || 0) === Number(targetMessage.timestamp || 0)
        && String(message.content || '') === String(targetMessage.content || '');
    });
  },

  clearTypingTimer: function() {
    if (this.data.typingTimer) {
      clearTimeout(this.data.typingTimer);
      this.setData({ typingTimer: null });
    }
  },

  finishAiReplyState: function() {
    this.stopReplyRecoveryPolling();
    this.clearTypingTimer();
    this.setData({
      isSending: false,
      isAiTyping: false,
      isSendDisabled: !this.data.inputValue.trim() || this.data.isMessageLimitReached
    });
  },

  stopReplyRecoveryPolling: function() {
    if (this.replyRecoveryTimer) {
      clearTimeout(this.replyRecoveryTimer);
      this.replyRecoveryTimer = null;
    }
  },

  scheduleReplyRecoveryPoll: function() {
    this.stopReplyRecoveryPolling();
    if (this.data.isLeavingPage || !this.data.aiId) return;

    this.replyRecoveryTimer = setTimeout(() => {
      this.replyRecoveryTimer = null;
      this.refreshReplyProgress();
    }, REPLY_STATUS_POLL_INTERVAL_MS);
  },

  beginReplyRecovery: function() {
    if (this.data.isLeavingPage) return;

    this.setData({
      isSending: false,
      isAiTyping: true,
      isSendDisabled: true
    });
    this.scheduleReplyRecoveryPoll();
  },

  refreshReplyProgress: function() {
    if (!this.data.aiId || this.data.isLeavingPage) return;

    this._request({
      url: `/chats/${this.data.aiId}/reply-status`,
      method: 'GET'
    }).then((data) => {
      const replyInProgress = Boolean(data && data.reply_in_progress);
      if (replyInProgress) {
        if (this.data.isSending) {
          this.scheduleReplyRecoveryPoll();
        } else {
          this.beginReplyRecovery();
        }
        return;
      }

      this.stopReplyRecoveryPolling();
      if (!this.data.isSending && this.data.isAiTyping) {
        this.reloadConversationAfterReply();
      }
    }).catch((err) => {
      console.warn('获取回复进度失败:', err);
      if (this.data.isAiTyping && !this.data.isSending) {
        this.scheduleReplyRecoveryPoll();
      }
    });
  },

  reloadConversationAfterReply: function() {
    if (!this.data.aiId || this.data.isLeavingPage) return;

    this._request({
      url: `/chats/${this.data.aiId}/details`,
      method: 'GET'
    }).then((data) => {
      this.applyChatDetailsData(data, {
        animateScroll: true,
        showProfileCard: false
      });
    }).catch((err) => {
      console.warn('回复结束后刷新聊天记录失败:', err);
      this.finishAiReplyState();
      wx.showToast({ title: '回复已结束，请重新进入聊天查看', icon: 'none' });
    });
  },

  applyChatDetailsData: function(data = {}, options = {}) {
    const formattedMessages = this.formatMessages(data.history);
    const character = data.character || {};
    const profile = character.profile || null;
    const profileCardData = this.buildProfileCardData(profile || {});
    const affinityDisplay = this.buildAffinityDisplay(data.favorability_context || {});
    const backendBaseUrl = API_BASE_URL.replace('/api/v1/community', '');
    const avatarUrl = character.avatar_url
      ? (character.avatar_url.startsWith('http') ? character.avatar_url : backendBaseUrl + character.avatar_url)
      : this.data.aiAvatar;
    const replyInProgress = Boolean(data.reply_in_progress);
    const preservedDraft = this.pendingConflictDraft !== undefined
      ? String(this.pendingConflictDraft || '')
      : this.data.inputValue;
    const isSending = this.data.isSending;
    const isAiTyping = isSending || replyInProgress;

    this.setData({
      messageList: formattedMessages,
      inputValue: preservedDraft,
      aiCurrentStatus: data.character_status || '在线',
      aiName: character.name || this.data.aiName,
      aiAvatar: avatarUrl,
      aiProfile: profile,
      isHistoryLoading: false,
      isHistoryLoadFailed: false,
      isAiTyping,
      isSendDisabled: !preservedDraft.trim()
        || this.data.isMessageLimitReached
        || isSending
        || replyInProgress,
      ...affinityDisplay,
      ...profileCardData
    }, () => {
      if (replyInProgress && !isSending) {
        this.beginReplyRecovery();
      } else if (!replyInProgress) {
        this.stopReplyRecoveryPolling();
        this.pendingConflictDraft = undefined;
      }

      if (options.showProfileCard !== false) {
        this.showProfileCardOnFirstVisit();
      }
      this.scrollToBottom({ animate: options.animateScroll === true });
    });
  },

  getRequestErrorMessage: function(err, fallback) {
    const detail = err && err.data ? err.data.detail : null;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (detail && typeof detail.message === 'string' && detail.message.trim()) {
      return detail.message;
    }
    return fallback;
  },

  getNextReplyDelay: function(message, index) {
    const textLength = message && message.content ? String(message.content).length : 0;
    const baseDelay = index === 0 ? 700 : 820;
    const readingDelay = Math.min(textLength * 22, 520);
    return baseDelay + readingDelay;
  },

  appendAiMessagesSequentially: function(messages, onComplete) {
    const aiMessages = Array.isArray(messages)
      ? messages.filter((message) => message && String(message.content || '').trim())
      : [];
    if (!aiMessages.length) {
      if (onComplete) onComplete();
      return;
    }

    const appendNext = (index) => {
      if (this.data.isLeavingPage) return;

      if (index >= aiMessages.length) {
        if (onComplete) onComplete();
        return;
      }

      const baseIndex = this.data.messageList.length;
      const msg = aiMessages[index];
      const nextMessage = this.normalizeMessage(
        {
          role: 'ai',
          content: msg.content,
          timestamp: msg.timestamp || Date.now() / 1000,
          appearClass: 'message-item-fade-in'
        },
        baseIndex
      );

      if (!nextMessage.content || this.hasMessage(nextMessage)) {
        const timer = setTimeout(() => appendNext(index + 1), 120);
        this.setData({ typingTimer: timer });
        return;
      }

      const updates = {
        messageList: [...this.data.messageList, nextMessage],
        isAiTyping: index < aiMessages.length - 1
      };

      this.setData(updates, () => {
        this.scrollToBottom({ animate: true });
        const delay = index >= aiMessages.length - 1
          ? 360
          : this.getNextReplyDelay(aiMessages[index + 1], index + 1);
        const timer = setTimeout(() => appendNext(index + 1), delay);
        this.setData({ typingTimer: timer });
      });
    };

    const timer = setTimeout(() => appendNext(0), this.getNextReplyDelay(aiMessages[0], 0));
    this.setData({ typingTimer: timer });
  },

  normalizeMessageQuota: function(dailyCount, limit) {
    const currentLimit = Number(this.data.messageLimit);
    const parsedLimit = Number(limit);
    const safeLimit = Number.isFinite(parsedLimit) && parsedLimit >= 0
      ? parsedLimit
      : (Number.isFinite(currentLimit) && currentLimit >= 0 ? currentLimit : 50);

    const currentCount = Number(this.data.dailyMessageCount);
    const parsedDailyCount = Number(dailyCount);
    const safeDailyCount = Number.isFinite(parsedDailyCount) && parsedDailyCount >= 0
      ? parsedDailyCount
      : (Number.isFinite(currentCount) && currentCount >= 0 ? currentCount : 0);

    return {
      dailyMessageCount: safeDailyCount,
      messageLimit: safeLimit,
      remainingMessageCount: Math.max(0, safeLimit - safeDailyCount),
      isMessageLimitReached: safeDailyCount >= safeLimit
    };
  },
  
  checkMessageLimit: function() {
    this._request({
      url: `/chats/status`,
      method: 'GET',
    }).then(res => {
      console.log("获取消息限制状态:", res);
      const quotaState = this.normalizeMessageQuota(res && res.daily_count, res && res.limit);
      this.setData({
        ...quotaState,
        isSendDisabled: !this.data.inputValue.trim() || quotaState.isMessageLimitReached || this.data.isSending || this.data.isAiTyping
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
    const value = e.detail.value || '';
    const isSendDisabled = !value.trim() || this.data.isMessageLimitReached || this.data.isSending || this.data.isAiTyping;
    if (value === this.data.inputValue && isSendDisabled === this.data.isSendDisabled) {
      return;
    }
    this.setData({ 
      inputValue: value,
      isSendDisabled
    });
  },

  onInputFocus: function() {
    if (this.data.isEmojiPanelVisible) {
      this.setData({ isEmojiPanelVisible: false });
    }
  },

  onUserAvatarError: function() {
    if (this.data.userAvatar !== DEFAULT_USER_AVATAR) {
      this.setData({ userAvatar: DEFAULT_USER_AVATAR });
    }
  },

  toggleEmojiPanel: function() {
    if (this.data.isMessageLimitReached) return;
    this.setData({ isEmojiPanelVisible: !this.data.isEmojiPanelVisible });
  },

  selectEmoji: function(e) {
    const emoji = e.currentTarget.dataset.emoji;
    if (!emoji || this.data.isMessageLimitReached) return;
    const inputValue = `${this.data.inputValue}${emoji}`;
    this.setData({
      inputValue,
      isEmojiPanelVisible: false,
      isSendDisabled: !inputValue.trim() || this.data.isMessageLimitReached || this.data.isSending || this.data.isAiTyping
    });
  },

  sendMessage: function() {
    if (this.data.isSending || this.data.isAiTyping) {
      wx.showToast({ title: '对方正在回复您哦~稍后再发吧', icon: 'none' });
      return;
    }

    if (this.data.isMessageLimitReached) {
      showVipQuotaModal({ feature: 'community' });
      return;
    }
    
    if (this.data.isSendDisabled) return;

    const content = this.data.inputValue.trim();
    if (!content) {
        return;
    }
    
    const nowTimestamp = Date.now() / 1000;
    const tempId = `${Math.floor(nowTimestamp * 1000)}_user`;
    const userMessage = {
      id: tempId,
      role: 'user',
      content: content,
      timestamp: nowTimestamp,
      time: this.formatTimestamp(nowTimestamp),
      status: 'sending'
    };
    const nextMessageList = [...this.data.messageList, userMessage];

    this.setData({
      messageList: nextMessageList,
      inputValue: '',
      isSendDisabled: true,
      isSending: true,
      isAiTyping: true,
      isEmojiPanelVisible: false,
    }, () => {
      this.scrollToBottom({ animate: true });
    });

    this.submitMessageRequest(content, tempId);
  },

  submitMessageRequest: function(content, messageId) {
    this._request({
      url: `/chats/${this.data.aiId}/messages`,
      method: 'POST',
      timeout: 120000,
      data: { content },
      success: (data) => {
        const aiMessages = data.ai_messages || [];
        if (!aiMessages.length) {
          this.updateMessageStatus(messageId, 'failed');
          this.finishAiReplyState();
          return;
        }

        this.updateMessageStatus(messageId, 'sent');
        const returnedCount = data.daily_count !== undefined && data.daily_count !== null
          ? data.daily_count
          : this.data.dailyMessageCount + 1;
        const quotaState = this.normalizeMessageQuota(
          returnedCount,
          data.limit !== undefined ? data.limit : this.data.messageLimit
        );
        this.setData({
            ...quotaState,
            isSendDisabled: true,
            aiCurrentStatus: data.character_status || this.data.aiCurrentStatus,
        });
        setTimeout(() => {
          this.appendAiMessagesSequentially(aiMessages, () => {
            this.finishAiReplyState();
          });
        }, 180);
      },
      fail: (err) => {
        console.error("发送失败:", err);

        if (isVipQuotaExhaustedError(err)) {
          this.setData({
            messageList: this.data.messageList.filter(message => message.id !== messageId),
            inputValue: content,
            isSending: false,
            isAiTyping: false,
            isMessageLimitReached: true,
            remainingMessageCount: 0,
            isSendDisabled: true
          }, () => {
            this.scrollToBottom({ animate: true });
          });
          showVipQuotaModal({ error: err, feature: 'community' });
          return;
        } else if (err && err.statusCode === 429) {
          this.showLimitModal(this.getRequestErrorMessage(err, '今日消息已达上限'));
          this.setData({
              isMessageLimitReached: true,
              remainingMessageCount: 0,
              isSendDisabled: true
          });
          this.setData({
            messageList: this.data.messageList.filter(message => message.id !== messageId),
            inputValue: ''
          });
        } else if (err && err.statusCode === 409) {
          this.pendingConflictDraft = content;
          this.setData({
            messageList: this.data.messageList.filter(message => message.id !== messageId),
            inputValue: content,
            isSending: false,
            isAiTyping: true,
            isSendDisabled: true
          }, () => {
            this.scrollToBottom({ animate: true });
          });
          wx.showToast({
            title: this.getRequestErrorMessage(err, '对方仍在回复，完成后会自动刷新'),
            icon: 'none'
          });
          this.beginReplyRecovery();
          return;
        } else {
          this.updateMessageStatus(messageId, 'failed');
          wx.showToast({
            title: '发送失败，点击红色感叹号重试',
            icon: 'none',
            duration: 2200
          });
        }
        this.finishAiReplyState();
      }
    })
    .catch(err => {
      console.log("Promise rejection has been handled gracefully.");
    });
  },

  showRetryPrompt: function(e) {
    const messageId = e.currentTarget.dataset.messageId;
    const message = this.data.messageList.find(item => item.id === messageId);
    if (!message || message.status !== 'failed') return;

    wx.showModal({
      title: '消息发送失败',
      content: '是否重新发送这条消息？',
      confirmText: '重新发送',
      cancelText: '取消',
      success: (result) => {
        if (result.confirm) {
          this.retryFailedMessage(messageId);
        }
      }
    });
  },

  retryFailedMessage: function(messageId) {
    if (this.data.isSending || this.data.isAiTyping) {
      wx.showToast({ title: '请等待当前回复完成', icon: 'none' });
      return;
    }

    if (this.data.isMessageLimitReached) {
      showVipQuotaModal({ feature: 'community' });
      return;
    }

    const messageIndex = this.data.messageList.findIndex(item => item.id === messageId);
    if (messageIndex === -1) return;

    const content = String(this.data.messageList[messageIndex].content || '').trim();
    if (!content) return;

    this.setData({
      [`messageList[${messageIndex}].status`]: 'sending',
      isSending: true,
      isAiTyping: true,
      isSendDisabled: true
    }, () => {
      this.scrollToBottom({ animate: true });
    });

    this.submitMessageRequest(content, messageId);
  },
  
  // ---------------------------------------------------
  // 其他所有原有函数 (保持不变)
  // ---------------------------------------------------

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

  loadInitialDataWithFallback: function() {
    this.setData({
      isHistoryLoading: true,
      isHistoryLoadFailed: false
    });
    this._request({
      url: `/chats/${this.data.aiId}/details`,
      success: (data) => {
        this.applyChatDetailsData(data, {
          animateScroll: false,
          showProfileCard: true
        });
      },
      fail: () => {
        console.warn("'/details' endpoint failed. Falling back to history only.");
        this._request({
          url: `/chats/${this.data.aiId}`,
          success: (historyData) => {
            const formattedMessages = this.formatMessages(historyData);
            this.setData({ 
              messageList: formattedMessages,
              aiCurrentStatus: '在线',
              isHistoryLoading: false,
              isHistoryLoadFailed: false
            }, () => {
              this.scrollToBottom({ animate: false });
            });
          },
          fail: () => {
            this.setData({
              isHistoryLoading: false,
              isHistoryLoadFailed: true
            });
            wx.showToast({ title: '加载历史消息失败', icon: 'none' });
          }
        });
      }
    });
  },

  retryInitialLoad: function() {
    if (this.data.isHistoryLoading) return;
    this.loadInitialDataWithFallback();
  },
  
  _request: function(options) {
    return new Promise((resolve, reject) => {
        const token = wx.getStorageSync('token');
        if (!token) { 
            wx.showToast({ title: '请先登录', icon: 'none' });
            if(options.fail) options.fail({errMsg: 'No Token'});
            if(options.complete) options.complete();
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
            },
            complete: () => {
                if(options.complete) options.complete();
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

  copyMessage: function(e) {
    const content = e && e.currentTarget && e.currentTarget.dataset
      ? String(e.currentTarget.dataset.content || '').trim()
      : '';
    if (!content) return;

    wx.setClipboardData({
      data: content,
      success: () => {
        wx.showToast({ title: '已复制', icon: 'success', duration: 900 });
      },
      fail: () => {
        wx.showToast({ title: '复制失败', icon: 'none' });
      }
    });
  },
  
  scrollToBottom: function(options = {}) {
    if (!this.data.messageList.length) return;

    const animate = options.animate !== false;
    wx.nextTick(() => {
      if (this.data.isLeavingPage) return;
      this.setData({
        scrollWithAnimation: animate,
        scrollTop: this.data.scrollTop + 100000
      });
    });
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
    return messages.map((msg, index) => this.normalizeMessage(msg, index));
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
