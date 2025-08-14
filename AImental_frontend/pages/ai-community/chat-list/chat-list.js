// pages/ai-community/chat-list/chat-list.js (最终完整版)
const API_BASE_URL = 'http://127.0.0.1:8000/api/v1/community';
const SERVER_URL = 'http://127.0.0.1:8000';
const app = getApp();

Page({
  data: {
    // --- 您的原有数据，完全保留 ---
    serverUrl: SERVER_URL,
    chatList: [],
    isLoading: false,

    // --- 【核心改动】用于动态导航栏的高度值 ---
    statusBarHeight: 0,
    navBarHeight: 0,
    totalHeaderHeight: 0, 
  },

  // --- 页面生命周期 ---

  onLoad: function (options) {
    // 【核心改动】从全局 app.js 获取并设置适配当前机型的导航栏高度
    this.setData({
      statusBarHeight: app.globalData.statusBarHeight || 20,
      navBarHeight: app.globalData.navBarHeight || 44,
      totalHeaderHeight: app.globalData.totalNavBarHeight || 64
    });

    // 【保留】页面加载时，注册自己为监听器
    app.webSocketManager.registerListener(this);
  },

  onShow: function () {
    // 【保留】您的原有功能
    app.webSocketManager.registerListener(this);
    const token = wx.getStorageSync('token');
    if (token) {
      this.getChatList();
      app.webSocketManager.connect();
    } else {
      this.setData({ chatList: [] });
      wx.showToast({ title: '请先登录', icon: 'none' });
    }
  },

  onUnload: function() {
    // 【保留】您的原有功能
    app.webSocketManager.unregisterListener();
  },

  // --- WebSocket 消息处理 (您的原有设计，完全保留) ---
  onSocketMessage: function(data) {
    console.log('ChatList Page: 收到全局推送消息:', data);
    if (data.type === 'new_message' && data.chat_summary) {
      const summary = data.chat_summary;
      let list = [...this.data.chatList];
      let existingChatIndex = list.findIndex(chat => chat.id === summary.character_id);
      
      const updatedChatItem = {
        id: summary.character_id,
        name: summary.character_name,
        avatar: summary.character_avatar_url.startsWith('http') ? summary.character_avatar_url : this.data.serverUrl + summary.character_avatar_url,
        lastMessage: summary.last_message_snippet,
        unread: summary.unread,
        time: this.formatTimestamp(summary.last_message_timestamp),
      };

      if (existingChatIndex > -1) {
        list.splice(existingChatIndex, 1);
      }
      
      list.unshift(updatedChatItem);
      this.setData({ chatList: list });
      console.log('ChatList Page: 列表已通过推送消息直接更新！');
    }
  },

  // --- API & 数据请求 (您的原有设计，完全保留) ---
  getChatList: function() {
    if (this.data.isLoading) return Promise.resolve();
    this.setData({ isLoading: true });
    wx.showNavigationBarLoading();

    return this._request({ url: '/chats' })
      .then(data => {
        if (!Array.isArray(data)) return;
        const formattedList = data.map(item => ({
          id: item.character_id,
          name: item.character_name,
          avatar: item.character_avatar_url.startsWith('http') ? item.character_avatar_url : SERVER_URL + item.character_avatar_url,
          lastMessage: item.last_message_snippet,
          unread: item.unread, 
          time: this.formatTimestamp(item.last_message_timestamp),
        }));
        this.setData({ chatList: formattedList });
      })
      .catch(err => { 
        console.error("加载列表失败:", err);
        wx.showToast({ title: '加载列表失败', icon: 'none' });
      })
      .finally(() => {
        this.setData({ isLoading: false });
        wx.hideNavigationBarLoading();
        wx.stopPullDownRefresh();
      });
  },

  onPullDownRefresh: function() {
    this.getChatList();
  },

  // --- 页面事件处理 (您的原有设计，完全保留) ---
  navigateToChat: function(e) {
    const ai = e.currentTarget.dataset.ai;
    wx.navigateTo({
      url: `/pages/ai-community/chat-interface/chat-interface?aiId=${ai.id}&name=${encodeURIComponent(ai.name)}&avatar=${encodeURIComponent(ai.avatar)}`
    });
  },

  addMoreFriends: function() {
    wx.navigateTo({ url: '/pages/ai-community/add-friends/add-friends' });
  },

  // --- 工具函数 (您的原有设计，完全保留) ---
  _request: function(options) {
    return new Promise((resolve, reject) => {
      const token = wx.getStorageSync('token');
      if (!token) {
        reject({ message: 'No token' });
        return;
      }
      wx.request({
        url: API_BASE_URL + options.url,
        method: options.method || 'GET',
        header: { 'Authorization': `Bearer ${token}`, ...options.header },
        data: options.data || {},
        success: (res) => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(res.data);
          } else {
            reject(res);
          }
        },
        fail: (err) => { reject(err); }
      });
    });
  },

  formatTimestamp: function(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp * 1000);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
    
    if (date >= today) {
      return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
    } else if (date >= yesterday) {
      return '昨天';
    } else {
      return `${date.getFullYear()}/${(date.getMonth() + 1).toString().padStart(2, '0')}/${date.getDate().toString().padStart(2, '0')}`;
    }
  }
});