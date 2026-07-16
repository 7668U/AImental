// pages/daily-checkin/index.js (修改后)
const { getShareInfo, getTimelineInfo } = require('../../utils/share.js');
const {
  confirmPrivacyAwareLogin,
  loginWithBackend,
  rejectPrivacyAwareLogin,
  requestPrivacyAwareLogin
} = require('../../utils/auth.js');

const DAILY_CHECKIN_GUIDE_VERSION = 'v1';
const DAILY_CHECKIN_GUIDE_ICON = '/pages/daily-checkin/assets/calendar-card.png';

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
    todayDate: '',
    todayMomentCount: 0,
    todayTrajectoryPreview: [],
    latestMomentTime: '',
    trajectorySubtitle: '今天还没有留下心情记录',
    showCalendar: false,
    statusBarHeight: 0,
    navBarHeight: 0,
    totalNavBarHeight: 0,
    privacyVisible: false,
    showDailyCheckinGuide: false,
    dailyCheckinGuideIcon: DAILY_CHECKIN_GUIDE_ICON
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
        this.showDailyCheckinGuideIfNeeded();
    
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
      this.setData({
        isLoggedIn: false,
        hasCheckedInToday: false,
        todayDate: '',
        todayMomentCount: 0,
        todayTrajectoryPreview: [],
        latestMomentTime: '',
        trajectorySubtitle: '今天还没有留下心情记录',
        showCalendar: false
      });
    }
  },

  getDailyCheckinGuideStorageKey() {
    const userInfo = wx.getStorageSync('userInfo') || {};
    const userKey = userInfo.id || userInfo.user_id || userInfo.openid || 'default';
    return `daily_checkin_guide_seen_${DAILY_CHECKIN_GUIDE_VERSION}_${userKey}`;
  },

  showDailyCheckinGuideIfNeeded() {
    const storageKey = this.getDailyCheckinGuideStorageKey();
    if (wx.getStorageSync(storageKey) || this._dailyCheckinGuideVisible) return;

    this._dailyCheckinGuideVisible = true;
    setTimeout(() => {
      this.setData({ showDailyCheckinGuide: true });
    }, 260);
  },

  handleConfirmDailyCheckinGuide() {
    const storageKey = this.getDailyCheckinGuideStorageKey();
    wx.setStorageSync(storageKey, true);
    this._dailyCheckinGuideVisible = false;
    this.setData({ showDailyCheckinGuide: false });
  },

  preventDailyCheckinGuideClose() {},

  promptLogin(content = '登录后可以继续使用这个功能。') {
    wx.showModal({
      title: '登录后继续',
      content,
      confirmText: '去登录',
      cancelText: '先逛逛',
      confirmColor: '#ff6b16',
      success: (res) => {
        if (res.confirm) {
          this.handleLogin();
        }
      }
    });
  },

  /**
   * 新增：处理登录逻辑的函数，由需要账号的操作触发
   */
  handleLogin() {
    return requestPrivacyAwareLogin(this, this.performLogin);
  },

  performLogin() {
    wx.showLoading({ title: '登录中...' });
    return loginWithBackend('http://127.0.0.1:8000/api/v1')
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

  onPrivacyConfirm() {
    return confirmPrivacyAwareLogin(this);
  },

  onPrivacyReject() {
    rejectPrivacyAwareLogin(this);
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
      const timeline = await request({ url: `/checkin/date/${serverDateStr}/timeline` });
      const moments = Array.isArray(timeline.moments) ? timeline.moments : [];
      const preview = moments.slice(-5).map(item => ({
        id: item.id,
        mood: item.mood,
        moodIcon: item.mood_icon || item.mood_id || item.mood,
        localTime: item.local_time || this.formatTimeFromTimestamp(item.recorded_at || item.timestamp),
      }));
      this.setData({
        todayDate: serverDateStr,
        hasCheckedInToday: moments.length > 0,
        todayMomentCount: moments.length,
        todayTrajectoryPreview: preview,
        latestMomentTime: preview.length ? preview[preview.length - 1].localTime : '',
        trajectorySubtitle: moments.length > 0 ? `今天已记录 ${moments.length} 次` : '今天还没有留下心情记录',
      });

    } catch (error) {
      // 任何请求失败都回到空状态，保持首页可继续记录。
      this.setData({
        hasCheckedInToday: false,
        todayMomentCount: 0,
        todayTrajectoryPreview: [],
        latestMomentTime: '',
        trajectorySubtitle: '今天还没有留下心情记录',
      });
    }
  },


  /**
   * 以下是原有的页面业务逻辑函数，保持不变
   */
  goToRecord() {
    if (!this.data.isLoggedIn) {
      this.promptLogin('登录后可以记录和保存你的此刻心情。');
      return;
    }

    wx.navigateTo({ url: '/pkgDailyCheckin/record' });
  },

  goToTrajectory() {
    if (!this.data.isLoggedIn) {
      this.promptLogin('登录后可以查看你的心情轨迹。');
      return;
    }
    const date = this.data.todayDate || this.getTodayString();
    wx.navigateTo({ url: `/pkgDailyCheckin/trajectory?date=${date}` });
  },
  
  openCalendar() {
    if (!this.data.isLoggedIn) {
      this.promptLogin('登录后可以查看你的心情日历。');
      return;
    }

    this.setData({ showCalendar: true });
  },

  hideCalendar() {
    this.setData({ showCalendar: false });
  },

  onDayTap(e) {
    if (!this.data.isLoggedIn) {
      this.promptLogin('登录后可以查看和补记心情。');
      return;
    }

    const { date, hasCheckin, hasTimeline } = e.detail;
    
    if (hasTimeline || hasCheckin) {
      wx.navigateTo({
        url: `/pkgDailyCheckin/trajectory?date=${date}`
      });
    } else {
      const todayStr = this.getTodayString();
      
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

  getTodayString() {
    const today = new Date();
    return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
  },

  formatTimeFromTimestamp(timestamp) {
    if (!timestamp) return '';
    const date = new Date(Number(timestamp) * 1000);
    if (Number.isNaN(date.getTime())) return '';
    return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
  },

  goToStatistics() {
    if (!this.data.isLoggedIn) {
      this.promptLogin('登录后可以查看你的心情分析。');
      return;
    }

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
