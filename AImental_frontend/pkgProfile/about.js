// about.js
const { getShareInfo, getTimelineInfo } = require('../utils/share.js');

Page({
  data: {
    navTop: 0,
    navHeight: 0,
    version: '3.0.0',
    contactInfo: '1751211464@qq.com'
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad: function (options) {
    this.setNavSize();
  },

  setNavSize() {
    const fallback = { statusBarHeight: 24 };
    let systemInfo = fallback;
    let menuButtonInfo = null;

    try {
      systemInfo = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
      menuButtonInfo = wx.getMenuButtonBoundingClientRect();
    } catch (e) {
      menuButtonInfo = null;
    }

    const statusBarHeight = systemInfo.statusBarHeight || fallback.statusBarHeight;
    const navHeight = menuButtonInfo
      ? menuButtonInfo.height + (menuButtonInfo.top - statusBarHeight) * 2
      : 44;

    this.setData({
      navTop: statusBarHeight,
      navHeight
    });
  },

  /**
   * 点击自定义返回按钮时的事件
   */
  navigateBack: function() {
    wx.navigateBack({
      delta: 1 // 返回上一页
    });
  },

  /**
   * 复制联系方式 (保持不变)
   */
  copyContact: function() {
    wx.setClipboardData({
      data: this.data.contactInfo,
      success: function (res) {
        wx.showToast({
          title: '联系方式已复制',
          icon: 'success'
        });
      }
    });
  },

  /**
   * 用户点击右上角分享给好友
   */
  onShareAppMessage: function () {
    return getShareInfo();
  },

  /**
   * 用户点击右上角分享到朋友圈
   */
  onShareTimeline: function () {
    return getTimelineInfo();
  }
})
