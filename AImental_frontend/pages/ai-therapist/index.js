// pages/ai-therapist/index.js
const { getShareInfo, getTimelineInfo } = require('../../utils/share.js');

// --- 全局配置与网络请求封装 ---
const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

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
    allowAiReadData: false,
    // 【新增】控制温馨提示弹窗的显示/隐藏
    isDisclaimerVisible: false,
  },
  
  // =================================================================
  // 核心生命周期函数
  // =================================================================

  onLoad(options) {
    this.checkLoginStatus();
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
        this.setData({ isLoggedIn: true });
        this.initializeChat();
        // 登录后，获取用户设置
        this.loadUserSettings(); 
      }
    } else {
      if (this.data.isLoggedIn) {
        this.setData({
          isLoggedIn: false, messages: [], chatHistory: [],
          activeChatId: null, isSidebarVisible: false, inputValue: '',
          isSettingsVisible: false,
        });
      }
    }
  },

  handleLogin() {
    wx.showLoading({ title: '正在登录' });
    wx.login({
      success: (loginRes) => {
        if (loginRes.code) {
          request({ url: '/users/login', method: 'POST', data: { code: loginRes.code } })
            .then(tokenRes => {
              wx.hideLoading();
              wx.setStorageSync('token', tokenRes.access_token);
              this.checkLoginStatus(); 
              wx.showToast({ title: '登录成功', icon: 'success' });

              // 【核心修改】登录成功后，检查是否需要显示温馨提示
              this.checkDisclaimer();

            }).catch(err => {
              wx.hideLoading();
              console.error("后端登录接口失败", err);
              wx.showToast({ title: '登录失败', icon: 'none' });
            });
        } else {
          wx.hideLoading();
          wx.showToast({ title: '凭证获取失败', icon: 'none' });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        console.error("登录接口调用失败:", err); 
        wx.showToast({ title: '登录失败', icon: 'none' }); 
      }
    });
  },

  async initializeChat() {
    await this.loadChatHistory();
    if (this.data.chatHistory && this.data.chatHistory.length > 0) {
      const latestChatId = this.data.chatHistory[0].id;
      this.switchChat({ currentTarget: { dataset: { id: latestChatId } } });
    } else {
      this.startNewChat();
    }
  },

  // =================================================================
  // 聊天与侧边栏
  // =================================================================
  
  async loadChatHistory() {
    try {
      const chatSummaries = await request({ url: '/chats/' }); 
      if (chatSummaries) {
        this.setData({ chatHistory: chatSummaries });
      }
    } catch (error) {
      console.error("加载聊天历史失败", error);
      this.setData({ chatHistory: [] });
    }
  },

  async startNewChat() {
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
      const newHistoryItem = { id: newChat.chat_id, title: newChat.title };
      currentHistory.unshift(newHistoryItem);
      this.setData({
        messages: [], messageCounter: 0, activeChatId: newChat.chat_id,
        isSidebarVisible: false, chatHistory: currentHistory
      });
      this.addMessage('ai', '你好，我是你的AI心理伙伴，随时在这里倾听你的心声。');
    } catch (error) {
      console.error("创建新聊天失败", error);
      wx.showToast({ title: '创建失败', icon: 'none' });
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
    const chatId = e.currentTarget.dataset.id;
    if (chatId === this.data.activeChatId && this.data.isSidebarVisible) {
      this.setData({ isSidebarVisible: false });
      return;
    }
    this.loadChat(chatId);
    this.setData({ isSidebarVisible: false });
  },

  async loadChat(chatId) {
    wx.showLoading({ title: '加载中...' });
    try {
      const chatSession = await request({ url: `/chats/${chatId}` });
      const historyMessages = JSON.parse(chatSession.message);
      const messages = historyMessages.map((msg, index) => ({
        id: index + 1,
        sender: msg.role === 'assistant' ? 'ai' : 'user',
        text: msg.content
      }));
      if (messages.length === 0) {
          messages.push({ id: 1, sender: 'ai', text: '你好，我是你的AI心理伙伴，随时在这里倾听你的心声。' });
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
    this.setData({ isSidebarVisible: !this.data.isSidebarVisible });
  },
  
  closeSidebar() {
    if (this.data.isSidebarVisible) {
      this.setData({ isSidebarVisible: false });
    }
  },

  showChatOptions(e) {
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

  async onSend() {
    if (!this.data.isLoggedIn) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    const text = this.data.inputValue.trim();
    if (!text) return;
    const isFirstUserMessage = this.data.messages.length <= 1;
    this.addMessage('user', text);
    this.setData({ inputValue: '' });
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
      this.updateMessage(loadingMessageId, "抱歉，出了一点问题，请稍后再试。");
    }
  },

  addMessage(sender, text, isLoading = false) {
    const messages = this.data.messages;
    const newMessageId = this.data.messageCounter + 1;
    messages.push({ id: newMessageId, sender, text, isLoading });
    this.setData({ messages, messageCounter: newMessageId, latestMessageId: `msg-${newMessageId}` });
    return newMessageId;
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
    const hasShown = wx.getStorageSync('hasShownDisclaimer');
    if (!hasShown) {
      this.setData({ isDisclaimerVisible: true });
    }
  },

  handleConfirmDisclaimer() {
    this.setData({ isDisclaimerVisible: false });
    wx.setStorageSync('hasShownDisclaimer', true);
  },

  onShareAppMessage: function () {
    return getShareInfo();
  },

  onShareTimeline: function () {
    return getTimelineInfo();
  }
});