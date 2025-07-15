// feedback.js (修改后)
Page({
  /**
   * 页面的初始数据
   */
  data: {
    // 自定义导航栏相关数据
    statusBarHeight: 0,
    navBarHeight: 0,

    // 业务数据
    feedbackType: 'optimization', 
    content: '',
    // 删除：移除了 uploadedImages 数组
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
   * 增加：返回上一页的函数
   */
  goBack() {
    wx.navigateBack({
      delta: 1
    });
  },

  /**
   * 切换反馈类型
   */
  switchType(e) {
    const newType = e.currentTarget.dataset.type;
    this.setData({
      feedbackType: newType
    });
  },

  /**
   * 处理文本域输入
   */
  handleTextareaInput(e) {
    this.setData({
      content: e.detail.value
    });
  },

  // 删除：chooseImage, previewImage, deleteImage 函数已被移除

  /**
   * 提交反馈
   */
  submitFeedback() {
    if (this.data.content.trim() === '') {
      wx.showToast({
        title: '反馈内容不能为空',
        icon: 'none'
      });
      return;
    }

    wx.showLoading({
      title: '正在提交...',
      mask: true
    });

    // 修改：简化了提交逻辑，不再处理图片
    console.log('提交的数据:');
    console.log('反馈类型:', this.data.feedbackType);
    console.log('反馈内容:', this.data.content);

    // 示例：模拟网络请求
    setTimeout(() => {
      wx.hideLoading();
      
      wx.showToast({
        title: '提交成功！',
        icon: 'success'
      });

      // 提交成功后，可以清空表单并返回上一页
      setTimeout(() => {
        this.setData({
          content: '',
          feedbackType: 'optimization'
        });
        wx.navigateBack();
      }, 1500);

    }, 2000);

    /* 真实的提交逻辑
     * wx.request({
     * url: '你的提交反馈接口',
     * method: 'POST',
     * data: {
     * type: this.data.feedbackType,
     * content: this.data.content
     * },
     * success(res) { // 成功处理 },
     * fail(err) { // 失败处理 },
     * complete() { wx.hideLoading(); }
     * });
    */
  }
});