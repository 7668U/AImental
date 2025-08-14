// pages/request-history/request-history.js

// 引入公用的API请求配置
const API_BASE_URL = 'http://127.0.0.1:8000/api/v1/community';
const SERVER_URL = 'http://127.0.0.1:8000';

Page({
  data: {
    serverUrl: SERVER_URL,
    requestList: [],
    isLoading: true,
    isEmpty: false,
  },

  onLoad: function (options) {
    this.loadHistory();
  },
  
  // 从添加好友页面复制过来的请求函数，保证风格统一
  _request: function(options) {
    return new Promise((resolve, reject) => {
      const token = wx.getStorageSync('token');
      if (!token) {
        wx.showToast({ title: '请先登录', icon: 'none' });
        reject({ message: 'No token', noAuth: true });
        return;
      }
      wx.request({
        url: API_BASE_URL + options.url,
        method: options.method || 'GET',
        header: { 'Authorization': `Bearer ${token}`, ...options.header },
        success: (res) => {
          if (res.statusCode >= 200 && res.statusCode < 300) resolve(res.data);
          else reject(res);
        },
        fail: reject
      });
    });
  },

  loadHistory: function() {
    this.setData({ isLoading: true });
    
    this._request({ url: '/friendship/history' })
      .then(data => {
        // 数据处理：将后端状态映射为前端展示所需的内容
        const statusMap = {
          accepted: { text: '已通过', className: 'accepted' },
          pending: { text: '等待回应', className: 'pending' },
          rejected: { text: '已拒绝', className: 'rejected' },
        };

        const processedList = data.map(item => ({
          character_id: item.character_id,
          name: item.character_name,
          avatar: this.data.serverUrl + item.character_avatar_url,
          verification_message: item.verification_message,
          status_info: statusMap[item.status] || { text: '未知', className: 'unknown' },
          // 格式化时间戳为"YYYY-MM-DD"
          request_date: new Date(item.request_timestamp).toLocaleDateString().replace(/\//g, '-')
        }));

        this.setData({
          requestList: processedList,
          isEmpty: processedList.length === 0,
          isLoading: false
        });
      })
      .catch(err => {
        console.error("加载历史记录失败", err);
        wx.showToast({ title: '加载失败', icon: 'none' });
        this.setData({ isLoading: false, isEmpty: true });
      });
  },

  // 点击列表项的交互
  handleTap: function(e) {
    const item = e.currentTarget.dataset.item;
    
    if (item.status_info.className === 'accepted') {
      wx.showToast({ title: '正在进入聊天...', icon: 'loading', duration: 1000 });
      // 跳转到聊天界面
      wx.navigateTo({
        url: `/pages/ai-community/chat-interface/chat-interface?characterId=${item.character_id}`
      });
    } else if (item.status_info.className === 'pending') {
      wx.showToast({ title: '对方还在考虑中，请耐心等待', icon: 'none' });
    } else {
      wx.showToast({ title: '你的申请已被对方拒绝', icon: 'none' });
    }
  }
});