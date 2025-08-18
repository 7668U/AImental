// pages/ai-community/chat-list/chat-list.js

const SERVER_URL = 'https://api.feelyourself.cn';
const app = getApp();

// --- 统一网络请求函数 ---
function request(options) {
  // 定义不同模块的基础URL
  const BASE_URLS = {
    user: `${SERVER_URL}/api/v1`,
    community: `${SERVER_URL}/api/v1/community`
  };
  // 默认使用 community 接口
  const finalBaseUrl = BASE_URLS[options.apiType] || BASE_URLS.community;

  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token');
    wx.request({
      ...options,
      url: `${finalBaseUrl}${options.url}`, // 根据 apiType 拼接 URL
      header: {
        ...options.header,
        'Authorization': `Bearer ${token}`
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else if (res.statusCode === 401) {
          // Token失效，获取当前页面实例并调用清理函数
          const currentPage = getCurrentPages().pop();
          if (currentPage && typeof currentPage.clearLoginState === 'function') {
            currentPage.clearLoginState();
          }
          reject(res);
        } else {
          reject(res);
        }
      },
      fail(err) {
        reject(err);
      }
    });
  });
}

const { getShareInfo, getTimelineInfo } = require('../../../utils/share.js');
Page({
  data: {
    // 保留原有数据结构
    serverUrl: SERVER_URL,
    chatList: [],
    isLoading: false,
    statusBarHeight: 0,
    navBarHeight: 0,
    totalHeaderHeight: 0,
    
    // 统一使用 isLoggedIn 控制登录状态
    isLoggedIn: false, 
    isError: false, // 新增错误状态
  },

  onLoad: function (options) {
    this.setData({
      // statusBarHeight 不变
      statusBarHeight: app.globalData.statusBarHeight || 20,
      
      // 【修改】让本页面使用“紧凑版”的高度
      navBarHeight: app.globalData.compactNavBarHeight || 44, 
      totalHeaderHeight: app.globalData.compactTotalNavBarHeight || 64
    });
    // onLoad 时只注册 WebSocket 监听器
    app.webSocketManager.registerListener(this);
  },

  onShow: function () {
    // 每次进入页面都检查登录状态
    this.checkLoginStatus();
  },

  onUnload: function() {
    // 页面卸载时注销监听器
    app.webSocketManager.unregisterListener();
  },

  // --- 核心登录检查逻辑 ---
  checkLoginStatus() {
    const token = wx.getStorageSync('token');
    if (token) {
      // 如果有 token，设置为已登录状态并获取数据
      if (!this.data.isLoggedIn) { // 避免重复setData
          this.setData({ isLoggedIn: true });
      }
      this.getChatList();
      app.webSocketManager.connect(); // 确认登录后再连接WebSocket
    } else {
      // 没有 token，设置为未登录状态
      this.setData({ 
        isLoggedIn: false,
        chatList: [] // 清空列表，避免显示旧数据
      });
    }
  },

  // --- 清理登录状态的函数，用于被 request 或其他页面逻辑调用 ---
  clearLoginState() {
    wx.removeStorageSync('token');
    wx.removeStorageSync('userInfo');
    this.setData({ isLoggedIn: false, chatList: [] });
    wx.showToast({ title: '登录已失效', icon: 'none' });
  },

  // --- 使用 async/await 和新的 request 函数重构登录逻辑 ---
  async handleLogin() {
    wx.showLoading({ title: '正在登录...' });
    try {
      const loginRes = await wx.login();
      if (!loginRes.code) throw new Error('微信登录失败');

      const tokenRes = await request({
        url: '/users/login',
        method: 'POST',
        apiType: 'user', // 指定使用用户接口的URL前缀
        data: { code: loginRes.code }
      });
      
      if (tokenRes.access_token) {
        wx.setStorageSync('token', tokenRes.access_token);
        wx.hideLoading();
        wx.showToast({ title: '登录成功', icon: 'success' });
        // 登录成功后，重新检查状态，会自动刷新UI并加载数据
        this.checkLoginStatus();
      } else {
        throw new Error('后端未返回有效token');
      }
    } catch (error) {
      wx.hideLoading();
      wx.showToast({ title: '登录失败，请稍后重试', icon: 'none' });
      console.error("登录流程失败: ", error);
    }
  },

  // --- 使用新的 request 函数获取聊天列表 ---
  async getChatList() {
    if (this.data.isLoading) return;
    this.setData({ isLoading: true, isError: false });
    wx.showNavigationBarLoading(); // 保留加载动画

    try {
      const data = await request({ 
        url: '/chats',
        apiType: 'community' // 指定使用社区接口的URL前缀
      });

      const formattedList = (data || []).map(item => ({
        id: item.character_id,
        name: item.character_name,
        avatar: item.character_avatar_url.startsWith('http') ? item.character_avatar_url : SERVER_URL + item.character_avatar_url,
        lastMessage: item.last_message_snippet,
        unread: item.unread, 
        time: this.formatTimestamp(item.last_message_timestamp),
      }));

      this.setData({ 
        chatList: formattedList,
        isError: false
      });

    } catch (error) {
      console.error("加载列表失败:", error);
      // 如果不是401（已在request中处理），则显示通用错误
      if (error.statusCode !== 401) {
        this.setData({ isError: true });
      }
    } finally {
      this.setData({ isLoading: false });
      wx.hideNavigationBarLoading();
      wx.stopPullDownRefresh();
    }
  },

  onPullDownRefresh: function() {
    if (this.data.isLoggedIn) {
      this.getChatList();
    } else {
      wx.stopPullDownRefresh();
    }
  },
  
  onSocketMessage: function(data) {
    if (!this.data.isLoggedIn) return; // 未登录不处理
    if (data.type === 'new_message' && data.chat_summary) {
      const summary = data.chat_summary;
      let list = [...this.data.chatList];
      let existingChatIndex = list.findIndex(chat => chat.id === summary.character_id);
      const updatedChatItem = {
        id: summary.character_id, name: summary.character_name,
        avatar: summary.character_avatar_url.startsWith('http') ? summary.character_avatar_url : this.data.serverUrl + summary.character_avatar_url,
        lastMessage: summary.last_message_snippet, unread: summary.unread,
        time: this.formatTimestamp(summary.last_message_timestamp),
      };
      if (existingChatIndex > -1) list.splice(existingChatIndex, 1);
      list.unshift(updatedChatItem);
      this.setData({ chatList: list });
    }
  },

  navigateToChat: function(e) {
    const ai = e.currentTarget.dataset.ai;
    wx.navigateTo({ url: `/pkgCommunity/chat-interface/chat-interface?aiId=${ai.id}&name=${encodeURIComponent(ai.name)}&avatar=${encodeURIComponent(ai.avatar)}` });
  },

  addMoreFriends: function() { 
    wx.navigateTo({ url: '/pkgCommunity/add-friends/add-friends' });
  },

  formatTimestamp: function(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp * 1e3);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
    if (date >= today) return `${date.getHours().toString().padStart(2, "0")}:${date.getMinutes().toString().padStart(2, "0")}`;
    if (date >= yesterday) return "昨天";
    return `${date.getFullYear()}/${(date.getMonth() + 1).toString().padStart(2, "0")}/${date.getDate().toString().padStart(2, "0")}`;
  },

  onShareAppMessage: function () {
    return getShareInfo();
  },

  onShareTimeline: function () {
    return getTimelineInfo();
  }
});

