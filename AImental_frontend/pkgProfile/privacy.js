const SERVER_BASE_URL = 'https://api.feelyourself.cn';
const {
  PRIVACY_POLICY,
  clearPrivacyConsent,
  hasCurrentPrivacyConsent
} = require('../utils/privacy.js');

Page({
  data: {
    policy: PRIVACY_POLICY,
    topSafeHeight: 72,
    isLoggedIn: false,
    consentCurrent: false,
    consentedAtText: ''
  },

  onLoad() {
    this.initLayoutMetrics();
  },

  onShow() {
    const token = wx.getStorageSync('token');
    this.setData({
      isLoggedIn: Boolean(token),
      consentCurrent: hasCurrentPrivacyConsent()
    });
    if (token) {
      this.loadConsentStatus(token);
    }
  },

  initLayoutMetrics() {
    let statusBarHeight = 24;
    try {
      const info = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
      statusBarHeight = info.statusBarHeight || statusBarHeight;
    } catch (error) {}
    this.setData({ topSafeHeight: statusBarHeight + 18 });
  },

  goBack() {
    wx.navigateBack();
  },

  loadConsentStatus(token) {
    wx.request({
      url: `${SERVER_BASE_URL}/api/v1/users/me/privacy-consent`,
      method: 'GET',
      header: { Authorization: `Bearer ${token}` },
      success: (res) => {
        if (res.statusCode !== 200) {
          return;
        }
        const consentedAt = res.data.consented_at
          ? new Date(res.data.consented_at).toLocaleString()
          : '';
        this.setData({
          consentCurrent: Boolean(res.data.is_current),
          consentedAtText: consentedAt
        });
      }
    });
  },

  withdrawConsent() {
    if (!this.data.isLoggedIn) {
      wx.showToast({ title: '当前尚未登录', icon: 'none' });
      return;
    }

    wx.showModal({
      title: '撤回隐私同意',
      content: '撤回后将退出登录，依赖账号和个人数据的功能会暂停使用。确定继续吗？',
      confirmText: '确认撤回',
      confirmColor: '#d96a3c',
      success: (modalRes) => {
        if (!modalRes.confirm) {
          return;
        }
        const token = wx.getStorageSync('token');
        wx.showLoading({ title: '正在处理...' });
        wx.request({
          url: `${SERVER_BASE_URL}/api/v1/users/me/privacy-consent`,
          method: 'DELETE',
          header: { Authorization: `Bearer ${token}` },
          complete: (res) => {
            wx.hideLoading();
            if (res.statusCode === 200) {
              clearPrivacyConsent();
              wx.removeStorageSync('token');
              wx.removeStorageSync('userInfo');
              this.setData({
                isLoggedIn: false,
                consentCurrent: false,
                consentedAtText: ''
              });
              wx.showToast({ title: '已撤回并退出登录', icon: 'none' });
              return;
            }
            wx.showToast({ title: '撤回失败，请稍后重试', icon: 'none' });
          }
        });
      }
    });
  }
});
