// pages/daily-checkin/index.js (修改后)

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
    wx.showLoading({ title: '正在登录' });
    wx.login({
      success: (loginRes) => {
        if (loginRes.code) {
          // 调用你原来的后端登录接口
          wx.request({
            url: 'http://127.0.0.1:8000/api/v1/users/login',
            method: 'POST',
            data: { code: loginRes.code },
            success: (tokenRes) => {
              if (tokenRes.statusCode === 200 && tokenRes.data.access_token) {
                wx.hideLoading();
                wx.setStorageSync('token', tokenRes.data.access_token);
                wx.showToast({ title: '登录成功', icon: 'success' });
                // 登录成功后，手动更新状态并加载页面数据
                this.setData({ isLoggedIn: true });
                this.fetchCheckinData();
              } else {
                 wx.hideLoading();
                 wx.showToast({ title: '登录失败，请稍后重试', icon: 'none' });
              }
            },
            fail: () => {
              wx.hideLoading();
              wx.showToast({ title: '登录失败，请检查网络', icon: 'none' });
            }
          });
        }
      },
      fail: () => {
         wx.hideLoading();
         wx.showToast({ title: '登录服务异常', icon: 'none' });
      }
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
    let url = './record';
    if (this.data.hasCheckedInToday) {
      url = './record?mode=edit';
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

  goToStatistics() {
    wx.navigateTo({
      url: './analysis'
    });
  },
})