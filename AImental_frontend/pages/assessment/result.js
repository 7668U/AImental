// pages/assessment/result.js
Page({
  data: {
    result: {
      final_score: 0,
      result_level: '',
      result_interpretation: '',
      result_recommendation: '',
    },
    // ✅ 1. 增加一个数据字段，用于记录页面来源
    source: '' 
  },

  onLoad(options) {
    // ✅ 2. 在页面加载时，检查并记录来源参数
    if (options.from) {
      this.setData({
        source: options.from
      });
    }

    if (options.data) {
      try {
        const resultData = JSON.parse(decodeURIComponent(options.data));
        this.setData({
          result: resultData
        });
      } catch (e) {
        console.error("解析结果数据失败", e);
        this.showErrorAndGoBack('结果加载失败');
      }
    } else {
      console.error("未接收到测评结果数据");
      this.showErrorAndGoBack('无效的访问');
    }
  },

  /**
   * “我知道了”按钮的点击事件处理函数
   * ✅ 3. 根据记录的 source 决定跳转行为
   */
  handleConfirm() {
    if (this.data.source === 'history') {
      // 如果来源是历史页，则返回上一页
      wx.navigateBack();
    } else {
      // 否则，执行默认行为（例如从答题页过来），跳转到测评列表
      wx.reLaunch({
        url: '/pages/assessment/index'
      });
    }
  },

  /**
   * 封装一个统一的错误处理函数，代码更简洁
   * @param {string} title 
   */
  showErrorAndGoBack(title) {
    wx.showToast({
      title: title,
      icon: 'error',
      duration: 2000
    });
    
    setTimeout(() => {
      // 无论哪种错误，都统一返回上一页
      wx.navigateBack();
    }, 2000);
  }
})