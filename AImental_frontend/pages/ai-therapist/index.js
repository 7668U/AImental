// pages/ai-therapist/index.js
const { getShareInfo, getTimelineInfo } = require('../../utils/share.js');
const {
  confirmPrivacyAwareLogin,
  loginWithBackend,
  rejectPrivacyAwareLogin,
  requestPrivacyAwareLogin
} = require('../../utils/auth.js');
const {
  isVipQuotaExhaustedError,
  showVipQuotaModal,
} = require('../../utils/vip-quota.js');

// --- 全局配置与网络请求封装 ---
const API_BASE_URL = 'https://api.feelyourself.cn/api/v1';
const WELCOME_MESSAGE = '你好呀，我是 Polaris 😊\n今天想聊些什么呢？';
const DEFAULT_HISTORY_PREVIEW = '继续这段对话，和 Polaris 慢慢聊。';
const THERAPIST_DISCLAIMER_STORAGE_KEY = 'hasShownMoodTreeholeDisclaimerV2';

function request(options) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token');
    wx.request({
      ...options,
      url: `${API_BASE_URL}${options.url}`,
      header: {
        ...options.header,
        'Authorization': `Bearer ${token}`
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          if (res.statusCode === 401) {
            console.error("请求未授权 (401)，token可能已失效。");
          } else if (isVipQuotaExhaustedError(res)) {
            // Let the caller restore optimistic UI and show the VIP guidance modal.
          } else {
            wx.showToast({ title: `请求错误: ${res.data.detail || res.statusCode}`, icon: 'none' });
          }
          reject(res);
        }
      },
      fail(err) {
        wx.showToast({ title: '网络连接失败', icon: 'none' });
        reject(err);
      }
    });
  });
}

// --- 页面逻辑 ---
Page({
  data: {
    isLoggedIn: false,
    isSidebarVisible: false,
    activeChatId: null,
    chatHistory: [],
    messages: [],
    inputValue: '',
    latestMessageId: '',
    messageCounter: 0,
    streamTimer: null,
    statusBarHeight: 0,
    navBarHeight: 0,
    totalNavBarHeight: 0,
    isSettingsVisible: false,
    allowAiReadData: true,
    isEmojiPanelVisible: false,
    emojiOptions: ['😊', '🙂', '😌', '🥰', '🤗', '😢', '😭', '😔', '😴', '😮', '😤', '✨', '🌙', '☀️', '🍀', '💛', '🧡', '👍'],
    // 【新增】控制温馨提示弹窗的显示/隐藏
    isDisclaimerVisible: false,
    privacyVisible: false,
  },

  _isInitializingChat: false,
  _hasInitializedChat: false,
  
  // =================================================================
  // 核心生命周期函数
  // =================================================================

  onLoad(options) {
    this.checkLoginStatus();
    this.checkDisclaimer();
    const windowInfo = wx.getWindowInfo();
    const menuButtonInfo = wx.getMenuButtonBoundingClientRect();
    const statusBarHeight = windowInfo.statusBarHeight;
    const navBarHeight = (menuButtonInfo.top - statusBarHeight) * 2 + menuButtonInfo.height;
    const totalNavBarHeight = statusBarHeight + navBarHeight;
    this.setData({ statusBarHeight, navBarHeight, totalNavBarHeight });
  },

  onShow() {
    this.checkLoginStatus();
  },

  // =================================================================
  // 登录与初始化
  // =================================================================
  
  checkLoginStatus() {
    const token = wx.getStorageSync('token');
    if (token) {
      if (!this.data.isLoggedIn) {
        this._hasInitializedChat = false;
        this.setData({ isLoggedIn: true });
        this.initializeChat();
        // 登录后，获取用户设置
        this.loadUserSettings(); 
      }
    } else {
      const wasLoggedIn = this.data.isLoggedIn;
      this._isInitializingChat = false;
      this._hasInitializedChat = false;
      this.setData({
        isLoggedIn: false,
        chatHistory: [],
        activeChatId: null,
        isSidebarVisible: false,
        isSettingsVisible: false,
        isEmojiPanelVisible: false,
        ...(wasLoggedIn ? { inputValue: '' } : {}),
      }, () => this.ensureGuestConversation(wasLoggedIn));
    }
  },

  ensureGuestConversation(forceReset = false) {
    if (!forceReset && this.data.messages.length > 0 && !this.data.activeChatId) {
      return;
    }

    this.setData({
      messages: [{
        id: 1,
        sender: 'ai',
        text: WELCOME_MESSAGE,
        displayTime: this.formatMessageTime()
      }],
      messageCounter: 1,
      latestMessageId: 'msg-1',
    });
  },

  promptLogin(content = '登录后可以继续使用这个功能。') {
    wx.showModal({
      title: '登录后继续',
      content,
      confirmText: '去登录',
      cancelText: '先逛逛',
      confirmColor: '#ff6b16',
      success: (res) => {
        if (res.confirm) {
          this.handleLogin();
        }
      }
    });
  },

  handleLogin() {
    return requestPrivacyAwareLogin(this, this.performLogin);
  },

  performLogin() {
    wx.showLoading({ title: '登录中...' });
    return loginWithBackend(API_BASE_URL)
      .then(tokenRes => {
        wx.hideLoading();
        if (!tokenRes.access_token) {
          throw new Error('登录接口未返回 token');
        }
        wx.setStorageSync('token', tokenRes.access_token);
        this.checkLoginStatus();
        wx.showToast({ title: '登录成功', icon: 'success' });
        this.checkDisclaimer();
      })
      .catch(err => {
        wx.hideLoading();
        console.error('登录失败', err);
        wx.showToast({ title: '登录失败，请重试', icon: 'none' });
      });
  },

  onPrivacyConfirm() {
    return confirmPrivacyAwareLogin(this);
  },

  onPrivacyReject() {
    rejectPrivacyAwareLogin(this);
  },

  async initializeChat() {
    if (this._isInitializingChat || this._hasInitializedChat) {
      return;
    }

    this._isInitializingChat = true;
    await this.loadChatHistory();
    try {
      if (this.data.chatHistory && this.data.chatHistory.length > 0) {
        const latestChatId = this.data.chatHistory[0].id;
        await this.loadChat(latestChatId);
      } else {
        await this.startNewChat();
      }
      this._hasInitializedChat = true;
    } finally {
      this._isInitializingChat = false;
    }
  },

  // =================================================================
  // 聊天与侧边栏
  // =================================================================
  
  async loadChatHistory() {
    try {
      const chatSummaries = await request({ url: '/chats/' }); 
      if (chatSummaries) {
        const formattedHistory = this.formatChatSummaries(chatSummaries);
        this.setData({ chatHistory: formattedHistory });
        this.enrichChatSummaries(formattedHistory);
      }
    } catch (error) {
      console.error("加载聊天历史失败", error);
      this.setData({ chatHistory: [] });
    }
  },

  formatChatSummaries(chatSummaries = []) {
    return chatSummaries.map((chat, index) => this.formatHistoryItem(chat, index));
  },

  formatHistoryItem(chat = {}, index = 0) {
    const timestamp = Number(chat.timestamp || chat.updated_at || chat.created_at) || 0;
    const title = (chat.title || '新的对话').trim();
    const preview = this.getChatPreview(chat.message) || chat.preview || chat.summary || DEFAULT_HISTORY_PREVIEW;

    return {
      ...chat,
      title,
      preview: this.truncateText(preview, 28),
      displayDate: this.formatHistoryDate(timestamp, index)
    };
  },

  enrichChatSummaries(chatSummaries = []) {
    if (!chatSummaries.length) return;

    const enrichCount = Math.min(chatSummaries.length, 12);
    Promise.all(
      chatSummaries.slice(0, enrichCount).map(async (chat, index) => {
        try {
          const detail = await request({ url: `/chats/${chat.id}` });
          return this.formatHistoryItem({ ...chat, ...detail }, index);
        } catch (error) {
          return chat;
        }
      })
    ).then((enrichedItems) => {
      const currentHistory = this.data.chatHistory || [];
      const restItems = currentHistory.slice(enrichCount);
      this.setData({ chatHistory: [...enrichedItems, ...restItems] });
    });
  },

  getChatPreview(rawMessage) {
    if (!rawMessage) return '';

    try {
      const parsedMessages = typeof rawMessage === 'string' ? JSON.parse(rawMessage) : rawMessage;
      if (!Array.isArray(parsedMessages) || parsedMessages.length === 0) return '';

      const userMessage = [...parsedMessages].reverse().find((msg) => msg.role === 'user' && msg.content);
      const lastMessage = userMessage || [...parsedMessages].reverse().find((msg) => msg.content);
      return lastMessage ? lastMessage.content : '';
    } catch (error) {
      return '';
    }
  },

  truncateText(text, maxLength) {
    if (!text) return '';
    const normalized = String(text).replace(/\s+/g, ' ').trim();
    if (normalized.length <= maxLength) return normalized;
    return `${normalized.slice(0, maxLength)}...`;
  },

  formatHistoryDate(timestamp, index = 0) {
    if (!timestamp) return index === 0 ? '最近' : '';
    const date = new Date(timestamp * 1000);
    const month = `${date.getMonth() + 1}`.padStart(2, '0');
    const day = `${date.getDate()}`.padStart(2, '0');
    return `${month}/${day}`;
  },

  formatMessageTime(timestamp) {
    const date = timestamp ? new Date(timestamp * 1000) : new Date();
    const hours = `${date.getHours()}`.padStart(2, '0');
    const minutes = `${date.getMinutes()}`.padStart(2, '0');
    return `${hours}:${minutes}`;
  },

  syncActiveChatPreview(text) {
    const now = Math.floor(Date.now() / 1000);
    const activeChatId = this.data.activeChatId;
    if (!activeChatId) return;

    const chatHistory = (this.data.chatHistory || []).map((chat, index) => {
      if (chat.id !== activeChatId) return chat;
      return {
        ...chat,
        timestamp: now,
        preview: this.truncateText(text, 28),
        displayDate: this.formatHistoryDate(now, index)
      };
    });
    this.setData({ chatHistory });
  },

  async startNewChat() {
    if (!this.data.isLoggedIn) {
      this.promptLogin('登录后可以创建并保存新的聊天记录。');
      return null;
    }

    wx.showLoading({ title: '创建中...' });
    try {
      // 【核心修改】: 在创建新聊天时，将当前的设置状态作为请求体发送给后端
      const requestBody = {
        with_context: this.data.allowAiReadData
      };
      
      const newChat = await request({ 
        url: '/chats/', 
        method: 'POST',
        data: requestBody // 将请求体传给后端
      });
      
      const currentHistory = this.data.chatHistory;
      const newHistoryItem = this.formatHistoryItem({
        id: newChat.chat_id,
        title: newChat.title,
        timestamp: Math.floor(Date.now() / 1000),
        preview: '刚刚开启一段新的陪伴。'
      });
      currentHistory.unshift(newHistoryItem);
      this.setData({
        messages: [], messageCounter: 0, activeChatId: newChat.chat_id,
        isSidebarVisible: false, isEmojiPanelVisible: false, chatHistory: currentHistory
      });
      this.addMessage('ai', WELCOME_MESSAGE);
      return newChat;
    } catch (error) {
      console.error("创建新聊天失败", error);
      wx.showToast({ title: '创建失败', icon: 'none' });
      throw error;
    } finally {
      wx.hideLoading();
    }
  },
  
  moveChatToTop(chatId) {
    const history = this.data.chatHistory;
    const chatIndex = history.findIndex(chat => chat.id === chatId);
    if (chatIndex > 0) {
      const [chatToMove] = history.splice(chatIndex, 1);
      history.unshift(chatToMove);
      this.setData({ chatHistory: history });
    }
  },

  updateChatTitle(chatId, newTitle) {
    const history = this.data.chatHistory;
    const chatIndex = history.findIndex(chat => chat.id === chatId);
    if (chatIndex !== -1 && history[chatIndex].title !== newTitle) {
      history[chatIndex].title = newTitle;
      this.setData({ chatHistory: history });
    }
  },

  switchChat(e) {
    if (!this.data.isLoggedIn) {
      this.promptLogin('登录后可以查看历史聊天记录。');
      return;
    }

    const chatId = e.currentTarget.dataset.id;
    if (chatId === this.data.activeChatId && this.data.isSidebarVisible) {
      this.setData({ isSidebarVisible: false });
      return;
    }
    this.loadChat(chatId);
    this.setData({ isSidebarVisible: false, isEmojiPanelVisible: false });
  },

  async loadChat(chatId) {
    wx.showLoading({ title: '加载中...' });
    try {
      const chatSession = await request({ url: `/chats/${chatId}` });
      const historyMessages = JSON.parse(chatSession.message);
      const baseTimestamp = Number(chatSession.timestamp) || Math.floor(Date.now() / 1000);
      const totalMessages = historyMessages.length || 1;
      const messages = historyMessages.map((msg, index) => ({
        id: index + 1,
        sender: msg.role === 'assistant' ? 'ai' : 'user',
        text: msg.content,
        displayTime: this.formatMessageTime(baseTimestamp - Math.max(totalMessages - index - 1, 0) * 60)
      }));
      if (messages.length === 0) {
          messages.push({
            id: 1,
            sender: 'ai',
            text: WELCOME_MESSAGE,
            displayTime: this.formatMessageTime(baseTimestamp)
          });
      }
      this.setData({
        messages, messageCounter: messages.length, activeChatId: chatId,
        latestMessageId: `msg-${messages.length}`
      });
    } catch (error) {
      console.error("加载聊天记录失败", error);
    } finally {
      wx.hideLoading();
    }
  },
  
  toggleSidebar() {
    if (!this.data.isLoggedIn) {
      this.promptLogin('登录后可以查看和管理历史聊天。');
      return;
    }

    this.setData({ isSidebarVisible: !this.data.isSidebarVisible });
  },
  
  closeSidebar() {
    const updates = {};
    if (this.data.isSidebarVisible) {
      updates.isSidebarVisible = false;
    }
    if (this.data.isEmojiPanelVisible) {
      updates.isEmojiPanelVisible = false;
    }
    if (Object.keys(updates).length > 0) {
      this.setData(updates);
    }
  },

  showChatOptions(e) {
      if (!this.data.isLoggedIn) {
          this.promptLogin('登录后可以管理你的聊天记录。');
          return;
      }

      const { id, title } = e.currentTarget.dataset;
      wx.showActionSheet({
          itemList: ['重命名', '删除'],
          itemColor: '#333333',
          success: (res) => {
              if (res.tapIndex === 0) {
                  this.handleRenameChat(id, title);
              } else if (res.tapIndex === 1) {
                  wx.showActionSheet({
                    itemList: ['确认删除'], itemColor: '#e64340',
                    success: (delRes) => {
                        if (delRes.tapIndex === 0) this.handleDeleteChat(id);
                    }
                  })
              }
          }
      });
  },

  handleRenameChat(chatId, currentTitle) {
      wx.showModal({
          title: '重命名你的聊天', content: '', editable: true,
          placeholderText: currentTitle,
          success: (res) => {
              if (res.confirm && res.content) {
                  const newTitle = res.content.trim();
                  if (newTitle && newTitle !== currentTitle) {
                      wx.showLoading({ title: '保存中...' });
                      request({ url: `/chats/${chatId}`, method: 'PATCH', data: { title: newTitle } })
                        .then(() => {
                          wx.hideLoading();
                          const history = this.data.chatHistory;
                          const chatIndex = history.findIndex(chat => chat.id === chatId);
                          if (chatIndex !== -1) {
                              history[chatIndex].title = newTitle;
                              this.setData({ chatHistory: history });
                              wx.showToast({ title: '重命名成功', icon: 'success' });
                          }
                        }).catch(err => {
                          wx.hideLoading();
                          console.error("重命名失败", err);
                          wx.showToast({ title: '操作失败', icon: 'none' });
                        });
                  }
              }
          }
      });
  },
  
  handleDeleteChat(chatId) {
      wx.showLoading({ title: '删除中...' });
      request({ url: `/chats/${chatId}`, method: 'DELETE' })
        .then(() => {
          wx.hideLoading();
          const newHistory = this.data.chatHistory.filter(chat => chat.id !== chatId);
          this.setData({ chatHistory: newHistory });
          if (this.data.activeChatId === chatId) this.initializeChat(); 
          wx.showToast({ title: '删除成功', icon: 'success' });
        }).catch(err => {
          wx.hideLoading();
          console.error("删除失败", err);
          wx.showToast({ title: '操作失败', icon: 'none' });
        });
  },

  // =================================================================
  // 消息处理
  // =================================================================

  onInput(e) {
    this.setData({ inputValue: e.detail.value });
  },

  toggleEmojiPanel() {
    this.setData({ isEmojiPanelVisible: !this.data.isEmojiPanelVisible });
  },

  selectEmoji(e) {
    const emoji = e.currentTarget.dataset.emoji;
    if (!emoji) return;
    this.setData({
      inputValue: `${this.data.inputValue}${emoji}`,
      isEmojiPanelVisible: false
    });
  },

  scrollToTop() {
    this.setData({ latestMessageId: '' }, () => {
      this.setData({ latestMessageId: 'chatTopAnchor' });
    });
  },

  async onSend() {
    const text = this.data.inputValue.trim();
    if (!text) return;

    if (!this.data.isLoggedIn) {
      this.promptLogin('登录后就可以把这段话发送给 Polaris，并保存这次对话。');
      return;
    }

    if (!this.data.activeChatId) {
      await this.startNewChat();
      if (!this.data.activeChatId) return;
    }

    const isFirstUserMessage = this.data.messages.length <= 1;
    const userMessageId = this.addMessage('user', text);
    this.syncActiveChatPreview(text);
    this.setData({ inputValue: '', isEmojiPanelVisible: false });
    const loadingMessageId = this.addMessage('ai', '', true);
    try {
      const response = await request({ url: `/chats/${this.data.activeChatId}/respond`, method: 'POST', data: { message: text } });
      this.streamMessage(loadingMessageId, response.reply); 
      this.moveChatToTop(this.data.activeChatId);
      if (isFirstUserMessage && response.title) {
        this.updateChatTitle(this.data.activeChatId, response.title);
      }
    } catch (error) {
      console.error("发送消息失败", error);
      if (isVipQuotaExhaustedError(error)) {
        this.removeMessages([userMessageId, loadingMessageId]);
        this.setData({ inputValue: text, isEmojiPanelVisible: false });
        showVipQuotaModal({ error, feature: 'tree_hole' });
        return;
      }
      this.updateMessage(loadingMessageId, "抱歉，出了一点问题，请稍后再试。");
    }
  },

  addMessage(sender, text, isLoading = false) {
    const messages = this.data.messages;
    const newMessageId = this.data.messageCounter + 1;
    messages.push({
      id: newMessageId,
      sender,
      text,
      isLoading,
      displayTime: this.formatMessageTime()
    });
    this.setData({ messages, messageCounter: newMessageId, latestMessageId: `msg-${newMessageId}` });
    return newMessageId;
  },

  removeMessages(messageIds = []) {
    const idSet = new Set(messageIds);
    const messages = this.data.messages.filter((message) => !idSet.has(message.id));
    const lastMessage = messages[messages.length - 1];
    this.setData({
      messages,
      latestMessageId: lastMessage ? `msg-${lastMessage.id}` : '',
    });
  },

  updateMessage(messageId, newText) {
    const messages = this.data.messages;
    const messageIndex = messages.findIndex(msg => msg.id === messageId);
    if (messageIndex !== -1) {
      messages[messageIndex].isLoading = false;
      messages[messageIndex].text = newText;
      this.setData({ messages });
    }
  },
  
  streamMessage(messageId, text) {
    let currentIndex = 0;
    const interval = 50;
    if (this.data.streamTimer) clearInterval(this.data.streamTimer);

    const timer = setInterval(() => {
      if (currentIndex < text.length) {
        currentIndex++;
        const messageToUpdate = this.data.messages.find(msg => msg.id === messageId);
        if (messageToUpdate && messageToUpdate.isLoading) messageToUpdate.isLoading = false;
        this.updateMessage(messageId, text.substring(0, currentIndex) + "▋");
        this.setData({ latestMessageId: `msg-${messageId}` });
      } else {
        this.updateMessage(messageId, text);
        clearInterval(timer);
        this.setData({ streamTimer: null, latestMessageId: `msg-${messageId}` });
      }
    }, interval);
    this.setData({ streamTimer: timer });
  },

  // =================================================================
  // 设置弹窗相关方法
  // =================================================================
  
  async loadUserSettings() {
    try {
      const userInfo = await request({ url: '/users/me' });
      if (userInfo && typeof userInfo.allow_ai_read_data === 'boolean') {
        this.setData({ allowAiReadData: userInfo.allow_ai_read_data });
      }
    } catch (error) {
      console.error("加载用户设置失败", error);
      this.setData({ allowAiReadData: false });
    }
  },

  toggleSettings() {
    if (!this.data.isLoggedIn) {
      this.promptLogin('登录后可以调整个性化对话设置。');
      return;
    }

    if (!this.data.isSettingsVisible) {
      this.loadUserSettings();
    }
    this.setData({ isSettingsVisible: !this.data.isSettingsVisible });
  },

  closeSettings() {
    this.setData({ isSettingsVisible: false });
  },

  preventClose() {},

  onAllowStatusChange(e) {
    const newStatus = e.detail.value;
    const oldStatus = this.data.allowAiReadData;

    this.setData({ allowAiReadData: newStatus });

    request({
      url: '/users/me/settings',
      method: 'PUT',
      data: { allow_ai_read_data: newStatus }
    }).then(() => {
      wx.showToast({
        title: newStatus ? '已开启个性化' : '已关闭个性化',
        icon: 'success',
        duration: 1500
      });
    }).catch(err => {
      console.error("设置更新失败", err);
      wx.showToast({
        title: '设置失败，请重试',
        icon: 'none'
      });
      this.setData({ allowAiReadData: oldStatus });
    });
  },

  // =================================================================
  // 【新增】温馨提示弹窗相关方法
  // =================================================================
  checkDisclaimer() {
    const hasShown = wx.getStorageSync(THERAPIST_DISCLAIMER_STORAGE_KEY);
    if (!hasShown) {
      this.setData({ isDisclaimerVisible: true });
    }
  },

  handleConfirmDisclaimer() {
    this.setData({ isDisclaimerVisible: false });
    wx.setStorageSync(THERAPIST_DISCLAIMER_STORAGE_KEY, true);
  },

  onShareAppMessage: function () {
    return getShareInfo();
  },

  onShareTimeline: function () {
    return getTimelineInfo();
  }
});
