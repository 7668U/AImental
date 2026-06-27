// pages/daily-checkin/index.js (修改后)
const { getShareInfo, getTimelineInfo } = require('../../utils/share.js');
const { loginWithBackend } = require('../../utils/auth.js');

// 从 ai-therapist 页面“借鉴”过来的网络请求函数，你也可以把它封装成公共模块
function request(options) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token');
    wx.request({
      ...options,
      url: `http://127.0.0.1:8000/api/v1${options.url}`,
      header: {
        ...options.header,
        'Authorization': `Bearer ${token}`
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          reject(res);
        }
      },
      fail(err) {
        reject(err);
      }
    });
  });
}


Page({
  data: {
    isLoggedIn: false, // 新增：登录状态标志
    hasCheckedInToday: false,
    showCalendar: false,
    statusBarHeight: 0,
    navBarHeight: 0,
    totalNavBarHeight: 0,
  },

  onLoad(options) {},

  onShow() {
    // 每次页面显示时，都重新检查登录状态
    this.checkLoginStatus();
        // 【新增】完全一样的动态计算逻辑
        const windowInfo = wx.getWindowInfo();
        const menuButtonInfo = wx.getMenuButtonBoundingClientRect();
        const extraPadding = 8; // 自定义间距，可自行调整
    
        const statusBarHeight = windowInfo.statusBarHeight;
        const navBarHeight = (menuButtonInfo.top - statusBarHeight) * 2 + menuButtonInfo.height + extraPadding;
        const totalNavBarHeight = statusBarHeight + navBarHeight;
    
        this.setData({
          statusBarHeight: statusBarHeight,
          navBarHeight: navBarHeight,
          totalNavBarHeight: totalNavBarHeight
        });
    
        // 模拟登录状态和打卡状态
        // this.setData({ isLoggedIn: true, hasCheckedInToday: false });
  
    
  },

  /**
   * 新增：检查本地 Token 判断是否登录
   */
  checkLoginStatus() {
    const token = wx.getStorageSync('token');
    if (token) {
      this.setData({ isLoggedIn: true });
      // 如果已登录，才去获取打卡状态
      this.fetchCheckinData();
    } else {
      this.setData({ isLoggedIn: false });
    }
  },

  /**
   * 新增：处理登录逻辑的函数，由 login-prompt 组件触发
   */
  handleLogin() {
    wx.showLoading({ title: '???' });
    loginWithBackend('http://127.0.0.1:8000/api/v1')
      .then((tokenRes) => {
        if (tokenRes.access_token) {
          wx.hideLoading();
          wx.setStorageSync('token', tokenRes.access_token);
          wx.showToast({ title: '????', icon: 'success' });
          this.setData({ isLoggedIn: true });
          this.fetchCheckinData();
        } else {
          throw new Error('???????token');
        }
      })
      .catch(() => {
        wx.hideLoading();
        wx.showToast({ title: '??????????', icon: 'none' });
      });
  },

  /**
   * 修改：原 checkTodayStatus 函数，现在只负责获取业务数据
   * 我们把它重命名为 fetchCheckinData，更清晰
   */
  async fetchCheckinData() {
    try {
      // 使用封装的 request 函数，代码更简洁
      const timeRes = await request({ url: '/system/time' });
      const serverDateStr = timeRes.server_date;
      
      await request({ url: `/checkin/date/${serverDateStr}` });
      // 如果上面这个请求成功 (没抛出异常)，说明已打卡
      this.setData({ hasCheckedInToday: true });

    } catch (error) {
      // 任何请求失败 (比如404代表未打卡)，都视为未打卡
      this.setData({ hasCheckedInToday: false });
    }
  },


  /**
   * 以下是原有的页面业务逻辑函数，保持不变
   */
  goToRecord() {
    let url = '/pkgDailyCheckin/record';
    if (this.data.hasCheckedInToday) {
      url = '/pkgDailyCheckin/record?mode=edit';
    }
    wx.navigateTo({ url: url });
  },
  
  openCalendar() {
    this.setData({ showCalendar: true });
  },

  hideCalendar() {
    this.setData({ showCalendar: false });
  },

  onDayTap(e) {
    const { date, hasCheckin } = e.detail;
    
    if (hasCheckin) {
      const mode = this.isWithinRecentDays(date, 3) ? 'edit' : 'view';
      wx.navigateTo({
        url: `/pkgDailyCheckin/record?mode=${mode}&date=${date}`
      });
    } else {
      const today = new Date();
      const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
      
      if (date === todayStr) {
        wx.navigateTo({ url: '/pkgDailyCheckin/record' });
      } else {
        wx.showToast({
          title: '那天没有记录哦~',
          icon: 'none'
        });
      }
    }
  },

  isWithinRecentDays(dateStr, days) {
    const target = new Date(`${dateStr}T00:00:00`);
    if (Number.isNaN(target.getTime())) return false;

    const today = new Date();
    const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    const diffDays = Math.floor((todayStart.getTime() - target.getTime()) / (24 * 60 * 60 * 1000));
    return diffDays >= 0 && diffDays < days;
  },

  goToStatistics() {
    wx.navigateTo({
      url: '/pkgDailyCheckin/analysis'
    });
  },

    onShareAppMessage: function () {
    return getShareInfo();
  },

  onShareTimeline: function () {
    return getTimelineInfo();
  }
});
