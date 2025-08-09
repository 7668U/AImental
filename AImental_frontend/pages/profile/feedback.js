// pages/feedback/feedback.js

//【配置】请确保这里的地址是正确的
const API_BASE_URL = 'http://127.0.0.1:8000/api/v1'; // 你的服务器根地址

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
  submitFeedback() {
    if (this.data.content.trim() === '') {
      wx.showToast({ title: '反馈内容不能为空', icon: 'none' });
      return;
    }

    const token = wx.getStorageSync('token');
    if (!token) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }

    wx.showLoading({ title: '正在提交...', mask: true });
    
    // 【核心修改】准备提交到后端的数据
    // 现在后端需要两个独立的字段：feedback_type 和 content
    const requestData = {
      feedback_type: this.data.feedbackType,
      content: this.data.content
    };
    
    // 发起网络请求，调用后端的 POST /feedback/ 接口
    wx.request({
      url: `${API_BASE_URL}/feedback/`,
      method: 'POST',
      header: {
        'Authorization': `Bearer ${token}`
      },
      // 【核心修改】将准备好的数据对象作为请求体
      data: requestData,
      success: (res) => {
        if (res.statusCode === 201) {
          wx.showToast({ title: '提交成功！', icon: 'success' });
          setTimeout(() => {
            this.setData({ content: '', feedbackType: 'optimization' });
            wx.navigateBack();
          }, 1500);
        } else {
          wx.showToast({ title: `提交失败: ${res.data.detail || '请稍后重试'}`, icon: 'none' });
        }
      },
      fail: (err) => {
        console.error("请求失败", err);
        wx.showToast({ title: '网络错误，请检查网络连接', icon: 'none' });
      },
      complete: () => {
        wx.hideLoading();
      }
    });
  }
});