// pages/ai-therapist/index.js

// --- 全局配置与网络请求封装 ---
const API_BASE_URL = 'https://api.feelyourself.cn/api/v1';

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
  },
  
  // =================================================================
  // 核心生命周期函数 (Lifecycle Hooks)
  // =================================================================

  onLoad(options) {
    console.log("页面首次加载 (onLoad)");
    this.checkLoginStatus();
  },

  onShow() {
    console.log("页面显示 (onShow)，重新检查登录状态...");
    this.checkLoginStatus();
  },

  // =================================================================
  // 登录与初始化 (Login & Initialization)
  // =================================================================
  
  checkLoginStatus() {
    const token = wx.getStorageSync('token');
    if (token) {
      if (!this.data.isLoggedIn) {
        console.log("检测到Token，更新为已登录状态并加载数据...");
        this.setData({ isLoggedIn: true });
        this.initializeChat();
      }
    } else {
      if (this.data.isLoggedIn) {
        console.log("未检测到Token，但页面状态为已登录，执行登出清理...");
        this.setData({
          isLoggedIn: false,
          messages: [],
          chatHistory: [],
          activeChatId: null,
          isSidebarVisible: false,
          inputValue: ''
        });
      }
    }
  },

  handleLogin() {
    wx.showLoading({ title: '正在登录' });
    wx.login({
      success: (loginRes) => {
        if (loginRes.code) {
          request({
            url: '/users/login',
            method: 'POST',
            data: { code: loginRes.code }
          }).then(tokenRes => {
            wx.hideLoading();
            wx.setStorageSync('token', tokenRes.access_token);
            this.checkLoginStatus(); 
            wx.showToast({ title: '登录成功', icon: 'success' });
          }).catch(err => {
            wx.hideLoading();
            console.error("后端登录接口失败", err);
            wx.showToast({ title: '登录失败，请稍后重试', icon: 'none' });
          });
        } else {
          wx.hideLoading();
          wx.showToast({ title: '凭证获取失败', icon: 'none' });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        // 在控制台打印完整的错误对象
        console.error("登录接口调用失败，详细错误:", err); 
        
        // 仍然给用户一个通用的提示
        wx.showToast({ title: '登录失败，请检查网络', icon: 'none' }); 
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
  // 聊天与侧边栏 (Chat & Sidebar)
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
      const newChat = await request({ url: '/chats/', method: 'POST' });
      const currentHistory = this.data.chatHistory;
      const newHistoryItem = {
        id: newChat.chat_id,
        title: newChat.title 
      };
      currentHistory.unshift(newHistoryItem);
      this.setData({
        messages: [],
        messageCounter: 0,
        activeChatId: newChat.chat_id,
        isSidebarVisible: false,
        chatHistory: currentHistory
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
      const chatToMove = history.splice(chatIndex, 1)[0];
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
          messages.push({
              id: 1,
              sender: 'ai',
              text: '你好，我是你的AI心理伙伴，随时在这里倾听你的心声。'
          });
      }
      this.setData({
        messages: messages,
        messageCounter: messages.length,
        activeChatId: chatId,
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

  // --- [新增] 聊天选项逻辑 (重命名与删除) ---
  showChatOptions(e) {
      const { id, title } = e.currentTarget.dataset;
      const that = this; // 保存 this 上下文

      wx.showActionSheet({
          itemList: ['重命名', '删除'],
          itemColor: '#333333', // 普通选项颜色
          success(res) {
              if (res.tapIndex === 0) {
                  // 用户点击了 "重命名"
                  that.handleRenameChat(id, title);
              } else if (res.tapIndex === 1) {
                  // 用户点击了 "删除"，二次确认
                  wx.showActionSheet({
                    itemList: ['确认删除'],
                    itemColor: '#e64340', // 红色警告
                    success(delRes) {
                        if (delRes.tapIndex === 0) {
                          that.handleDeleteChat(id);
                        }
                    }
                  })
              }
          }
      });
  },

  handleRenameChat(chatId, currentTitle) {
      const that = this;
      wx.showModal({
          title: '重命名你的聊天',
          content: '',
          editable: true,
          placeholderText: currentTitle,
          success(res) {
              if (res.confirm && res.content) {
                  const newTitle = res.content.trim();
                  if (newTitle && newTitle !== currentTitle) {
                      wx.showLoading({ title: '保存中...' });
                      // 调用后端API
                      request({
                          url: `/chats/${chatId}`,
                          method: 'PATCH',
                          data: { title: newTitle }
                      }).then(() => {
                          wx.hideLoading();
                          // 更新前端 chatHistory 数组中的数据
                          const history = that.data.chatHistory;
                          const chatIndex = history.findIndex(chat => chat.id === chatId);
                          if (chatIndex !== -1) {
                              history[chatIndex].title = newTitle;
                              that.setData({ chatHistory: history });
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
      const that = this;
      wx.showLoading({ title: '删除中...' });
      // 调用已有的删除API
      request({
          url: `/chats/${chatId}`,
          method: 'DELETE'
      }).then(() => {
          wx.hideLoading();
          // 从前端 chatHistory 数组中移除该项
          const newHistory = that.data.chatHistory.filter(chat => chat.id !== chatId);
          that.setData({ chatHistory: newHistory });

          // [重要] 检查删除的是否是当前正在查看的聊天
          if (that.data.activeChatId === chatId) {
              // 如果是，则清空聊天界面或加载下一个聊天, 最简单的方式是重新初始化
              that.initializeChat(); 
          }
          wx.showToast({ title: '删除成功', icon: 'success' });
      }).catch(err => {
          wx.hideLoading();
          console.error("删除失败", err);
          wx.showToast({ title: '操作失败', icon: 'none' });
      });
  },

  // =================================================================
  // 消息处理 (Message Handling)
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
      const response = await request({
        url: `/chats/${this.data.activeChatId}/respond`,
        method: 'POST',
        data: { message: text } 
      });

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
    this.setData({
      messages,
      messageCounter: newMessageId,
      latestMessageId: `msg-${newMessageId}`
    });
    return newMessageId;
  },

  updateMessage(messageId, newText) {
    const messages = this.data.messages;
    const messageIndex = messages.findIndex(msg => msg.id === messageId);
    if (messageIndex !== -1) {
      const messageToUpdate = messages[messageIndex];
      if (messageToUpdate.isLoading) {
        messageToUpdate.isLoading = false;
      }
      messageToUpdate.text = newText;
      this.setData({ messages });
    }
  },
  
  streamMessage(messageId, text) {
    let currentIndex = 0;
    const interval = 50; // 打字速度(毫秒)

    if (this.data.streamTimer) {
      clearInterval(this.data.streamTimer);
    }

    const timer = setInterval(() => {
      if (currentIndex < text.length) {
        currentIndex++;
        const messageToUpdate = this.data.messages.find(msg => msg.id === messageId);
        if (messageToUpdate && messageToUpdate.isLoading) {
          messageToUpdate.isLoading = false;
        }
        this.updateMessage(messageId, text.substring(0, currentIndex) + "▋");
      } else {
        this.updateMessage(messageId, text); // 显示最终完整文本
        clearInterval(timer);
        this.setData({ streamTimer: null });
      }
    }, interval);

    this.setData({ streamTimer: timer });
  },
});