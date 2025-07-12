// pages/daily-checkin/index.js
Page({
  /**
   * 页面的初始数据
   */
  data: {
    // 这个页面目前是静态的，所以暂时不需要太多数据
  },

  /**
   * 跳转到“今日打卡”页面
   */
  goToRecord() {
    wx.navigateTo({
      // url 指向我们刚刚创建的 record 页面
      url: './record' 
    });
  },

  /**
   * 跳转到“心情日历”页面
   * 【注意】这是一个占位函数，对应的页面还需您后续创建
   */
  goToCalendar() {
    // 在页面创建好之前，我们可以先用一个提示来代替
    wx.showToast({
      title: '日历功能正在努力开发中...',
      icon: 'none'
    });
    
    /*
    // 页面创建好后，您可以使用下面的代码进行跳转
    wx.navigateTo({
      url: './calendar' // 假设日历页面的文件名是 calendar
    });
    */
  },

  /**
   * 跳转到“心情报告”页面
   * 【注意】这是一个占位函数，对应的页面还需您后续创建
   */
  goToStatistics() {
    // 同样，先用一个提示来代替
    wx.showToast({
      title: '心情报告功能敬请期待！',
      icon: 'none'
    });

    /*
    // 页面创建好后，您可以使用下面的代码进行跳转
    wx.navigateTo({
      url: './statistics' // 假设报告页面的文件名是 statistics
    });
    */
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {

  },

  /**
   * 生命周期函数--监听页面显示
   */
  onShow() {
    // 可以在这里写一些每次页面显示时都需要执行的逻辑
    // 例如，检查登录状态等
  },

  // ... 其他生命周期函数 ...
})