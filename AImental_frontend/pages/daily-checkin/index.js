// pages/daily-checkin/index.js (修改后)
const { getShareInfo, getTimelineInfo } = require('../../utils/share.js');
const { loginWithBackend } = require('../../utils/auth.js');

// 从 ai-therapist 页面“借鉴”过来的网络请求函数，你也可以把它封装成公共模块
function request(options) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token');
    wx.request({
      ...options,
      url: `https://feelyourself.cn/api/v1${options.url}`,
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
    wx.showLoading({ title: '登录中...' });
    loginWithBackend('https://feelyourself.cn/api/v1')
      .then((tokenRes) => {
        if (tokenRes.access_token) {
          wx.hideLoading();
          wx.setStorageSync('token', tokenRes.access_token);
          wx.showToast({ title: '登录成功', icon: 'success' });
          this.setData({ isLoggedIn: true });
          this.fetchCheckinData();
        } else {
          throw new Error('登录接口未返回 token');
        }
      })
      .catch(() => {
        wx.hideLoading();
        wx.showToast({ title: '登录失败，请重试', icon: 'none' });
      });
  },

  /**
   * 修改：原 checkTodayStatus 函数，现在只负责获取业务数据
   * 我们把它重命名为 fetchCheckinData，更清晰
   */
  async fetchCheckinData() {
    try {
      const timeRes = await request({ url: '/system/time' });
      const serverDateStr = timeRes.server_date;
      const [year, month, day] = serverDateStr.split('-');
      const monthlyCheckins = await request({ url: `/checkin/month/${year}/${Number(month)}` });
      this.setData({ hasCheckedInToday: !!monthlyCheckins[Number(day)] });

    } catch (error) {
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
      if (this.isWithinRecentDays(date, 3)) {
        wx.navigateTo({
          url: `/pkgDailyCheckin/record?mode=create&date=${date}`
        });
      } else {
        wx.showToast({
          title: '只能补记最近3天哦~',
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
