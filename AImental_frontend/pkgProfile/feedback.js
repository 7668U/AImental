// pages/feedback/feedback.js
const { getShareInfo, getTimelineInfo } = require('../utils/share.js');

//【配置】请确保这里的地址是正确的
const API_BASE_URL = 'https://api.feelyourself.cn/api/v1'; // 你的服务器根地址

Page({
  /**
   * 页面的初始数据
   */
  data: {
    statusBarHeight: 0,
    navBarHeight: 0,
    feedbackType: 'optimization', // 'optimization' 或 'bug'
    content: '',
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    const systemInfo = wx.getSystemInfoSync();
    const menuButtonInfo = wx.getMenuButtonBoundingClientRect();
    this.setData({
      statusBarHeight: systemInfo.statusBarHeight,
      navBarHeight: menuButtonInfo.height + (menuButtonInfo.top - systemInfo.statusBarHeight) * 2
    });
  },

  /**
   * 返回上一页
   */
  goBack() {
    wx.navigateBack({ delta: 1 });
  },

  /**
   * 切换反馈类型
   */
  switchType(e) {
    this.setData({ feedbackType: e.currentTarget.dataset.type });
  },

  /**
   * 处理文本域输入
   */
  handleTextareaInput(e) {
    this.setData({ content: e.detail.value });
  },

  /**
   * 提交反馈
   */
  handleSubmit() {
    if (!this.data.content) {
      wx.showToast({ title: '内容不能为空', icon: 'none' });
      return;
    }
    // 此处应有实际的提交逻辑，例如 wx.request
    wx.showLoading({ title: '正在提交...' });
    setTimeout(() => {
      wx.hideLoading();
      wx.showToast({ title: '感谢您的反馈！', icon: 'success' });
      this.setData({ content: '' });
      setTimeout(() => wx.navigateBack(), 1500);
    }, 1000);
  },

  onShareAppMessage: function () {
    return getShareInfo();
  },

  onShareTimeline: function () {
    return getTimelineInfo();
  }
});