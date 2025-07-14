// pages/assessment/result.js
Page({
  /**
   * 页面的初始数据
   */
  data: {
    // 初始化一个空的result对象，防止WXML在数据加载完成前渲染时报错
    result: {
      final_score: 0,
      result_level: '',
      result_interpretation: '',
      result_recommendation: '',
    }
  },

  /**
   * 生命周期函数--监听页面加载
   * options 是从上一个页面跳转时传来的参数
   */
  onLoad(options) {
    if (options.data) {
      try {
        // 从URL参数中解码并解析JSON数据
        const resultData = JSON.parse(decodeURIComponent(options.data));

        // 将解析出的数据更新到页面的data中，WXML会自动重新渲染
        this.setData({
          result: resultData
        });

      } catch (e) {
        console.error("解析结果数据失败", e);
        wx.showToast({
          title: '结果加载失败',
          icon: 'error',
          duration: 2000
        });
        setTimeout(() => {
          this.handleConfirm(); // 加载失败也返回主页
        }, 2000);
      }
    } else {
      console.error("未接收到测评结果数据");
      wx.showToast({
        title: '无效的访问',
        icon: 'error',
        duration: 2000
      });
      setTimeout(() => {
        this.handleConfirm(); // 无效访问也返回主页
      }, 2000);
    }
  },

  /**
   * “我知道了”按钮的点击事件处理函数
   */
  handleConfirm() {
    // 使用 reLaunch 跳转到测评主页，清空导航栈，给用户一个全新的开始
    wx.reLaunch({
      // 因为 index, test, result 都在同一个 assessment 文件夹下，
      // 所以我们直接跳转到 'index' 即可。
      // 使用 / 开头的绝对路径更保险。
      url: '/pages/assessment/index'
    });
  }
})