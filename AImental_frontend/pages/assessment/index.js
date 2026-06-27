const { getShareInfo, getTimelineInfo } = require('../../utils/share.js');
const { loginWithBackend } = require('../../utils/auth.js');
// pages/assessment/index.js

const SERVER_BASE_URL = 'http://127.0.0.1:8000';
const ASSESSMENT_GROUPS = [
  {
    label: '心理健康',
    theme: 'health',
    description: '关注情绪状态，关爱内心健康',
    icon: '/images/assessment/home/group-health.png',
    key: 'health'
  },
  {
    label: '自我人格',
    theme: 'personality',
    description: '探索性格特质，认识独特的自己',
    icon: '/images/assessment/home/group-personality.png',
    key: 'personality'
  },
  {
    label: '亲密关系',
    theme: 'relationship',
    description: '理解人际关系，建立深度联结',
    icon: '/images/assessment/home/group-relationship.png',
    key: 'relationship'
  },
  {
    label: '趣味探索',
    theme: 'interest',
    description: '发现兴趣偏好，探索更多可能',
    icon: '/images/assessment/home/group-interest.png',
    key: 'interest'
  },
];

Page({
  data: {
    isLoggedIn: false,
    statusBarHeight: 0,
    displayGroups: ASSESSMENT_GROUPS,
  },

  onShow() {
    this.checkLoginStatus();
    const systemInfo = wx.getSystemInfoSync();
    this.setData({
      statusBarHeight: systemInfo.statusBarHeight
    });
  },
  
  checkLoginStatus() {
    const token = wx.getStorageSync('token');
    if (token) {
      this.setData({ isLoggedIn: true });
    } else {
      this.setData({ isLoggedIn: false });
    }
  },

  // --- [修改] 采用 async/await 重构登录函数，逻辑更清晰 ---
  async handleLogin() {
    wx.showLoading({ title: '???...' });
    try {
      const tokenRes = await loginWithBackend(SERVER_BASE_URL + '/api/v1');
      if (tokenRes.access_token) {
        wx.setStorageSync('token', tokenRes.access_token);
        wx.hideLoading();
        wx.showToast({ title: '????', icon: 'success' });
        this.checkLoginStatus();
      } else {
        throw new Error('???????token');
      }
    } catch (error) {
      wx.hideLoading();
      wx.showToast({ title: '??????????', icon: 'none' });
      console.error('??????: ' , error);
    }
  },

  // [新增] 清理登录状态并提示的函数，用于被 request 调用
  clearLoginStateAndShowToast() {
    wx.removeStorageSync('token');
    wx.removeStorageSync('userInfo');
    this.setData({ isLoggedIn: false });
    wx.showToast({ title: '登录已失效，请重新登录', icon: 'none' });
  },

  onPullDownRefresh() {
    wx.stopPullDownRefresh();
  },
  goToCategory(e) {
    const group = e.currentTarget.dataset.group;
    const encodedGroup = encodeURIComponent(group);
    wx.navigateTo({ url: `/pkgAssessment/category/category?group=${encodedGroup}` });
  },

  onShareAppMessage: function () {
    return getShareInfo();
  },

  onShareTimeline: function () {
    return getTimelineInfo();
  }
});
