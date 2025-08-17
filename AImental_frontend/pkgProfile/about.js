// about.js
const { getShareInfo, getTimelineInfo } = require('../utils/share.js');

Page({
  data: {
    statusBarHeight: 0, // 用于WXML设置导航栏样式的状态栏高度
    version: '2.0.0',
    contactInfo: 'feelyourself12138@163.com'
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad: function (options) {
    // 获取手机系统信息，得到状态栏高度
    wx.getSystemInfo({
      success: (res) => {
        this.setData({
          statusBarHeight: res.statusBarHeight
        });
      },
    })
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