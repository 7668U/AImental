// pages/daily-checkin/index.js
Page({
  data: {
    hasCheckedInToday: false,
    showCalendar: false,
  },

  onLoad(options) {},

  onShow() {
    // 每次页面显示时，都重新检查当天的打卡状态
    this.checkTodayStatus();
  },

  /**
   * 检查当天打卡状态的函数
   */
  checkTodayStatus() {
    const token = wx.getStorageSync('token');
    if (!token) return;

    // 先从后端获取权威的“今天”是几号
    wx.request({
      url: 'http://49.233.220.130:8000/api/v1/system/time',
      method: 'GET',
      header: { 'Authorization': `Bearer ${token}` },
      success: (timeRes) => {
        if (timeRes.statusCode !== 200) {
          this.setData({ hasCheckedInToday: false });
          return;
        }
        const serverDateStr = timeRes.data.server_date;
        
        // 再用服务器的日期去查询打卡记录
        wx.request({
          url: `http://49.233.220.130:8000/api/v1/checkin/date/${serverDateStr}`,
          method: 'GET',
          header: { 'Authorization': `Bearer ${token}` },
          success: (statusRes) => {
            this.setData({ hasCheckedInToday: statusRes.statusCode === 200 });
          },
          fail: () => {
            this.setData({ hasCheckedInToday: false });
          }
        });
      },
      fail: () => {
        this.setData({ hasCheckedInToday: false });
      }
    });
  },

  /**
   * 跳转到“今日打卡”页面
   */
  goToRecord() {
    let url = './record'; // 默认是新建模式

    // 如果今天已经打过卡，就在URL后面加上参数 mode=edit
    if (this.data.hasCheckedInToday) {
      url = './record?mode=edit';
    }

    wx.navigateTo({
      url: url
    });
  },
  
  // --- 以下是与日历交互的函数 ---

  /**
   * 打开日历弹窗
   */
  openCalendar() {
    this.setData({ showCalendar: true });
  },

  /**
   * 关闭日历弹窗
   */
  hideCalendar() {
    this.setData({ showCalendar: false });
  },

  /**
   * 处理日历组件的日期点击事件
   */
  onDayTap(e) {
    const { date, hasCheckin } = e.detail;
    
    if (hasCheckin) {
      wx.navigateTo({
        url: `./record?mode=view&date=${date}`
      });
    } else {
      const today = new Date();
      const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
      
      if (date === todayStr) {
        wx.navigateTo({ url: './record' });
      } else {
        wx.showToast({
          title: '那天没有记录哦~',
          icon: 'none'
        });
      }
    }
  },

  /**
   * “心情日历”卡片的点击事件
   */
  goToCalendar() {
    this.openCalendar();
  },

  /**
   * 【最终修改】“我的心情报告”卡片的点击事件
   * 现在它会跳转到我们新建的 analysis 页面
   */
  goToStatistics() {
    wx.navigateTo({
      url: './analysis' // 跳转到同目录下的 analysis 页面
    });
  },
})