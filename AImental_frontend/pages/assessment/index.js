// pages/assessment/index/index.js (修改后)

// --- 1. 抽离出可复用的网络请求函数 ---
// (这个函数会自动添加 Base URL 和 Token)
function request(options) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token');
    wx.request({
      ...options,
      url: `https://api.feelyourself.cn/api/v1${options.url}`,
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

const DEFAULT_ICON_PATH = '/images/assessment/default.png';

Page({
  data: {
    isLoggedIn: false,  // 新增：登录状态
    scaleList: [],
    isLoading: true,
    isError: false,
  },

  // --- 2. 修改生命周期函数 ---
  
  onLoad(options) {
    // onLoad 中不再直接获取数据
  },

  onShow() {
    // 每次进入页面都检查登录状态
    this.checkLoginStatus();
  },

  onPullDownRefresh() {
    // 确保登录后才允许下拉刷新
    if (this.data.isLoggedIn) {
      this.fetchScaleList();
    } else {
      wx.stopPullDownRefresh();
    }
  },

  // --- 3. 新增登录相关函数 ---

  /**
   * 检查本地 Token 判断是否登录
   */
  checkLoginStatus() {
    const token = wx.getStorageSync('token');
    if (token) {
      this.setData({ isLoggedIn: true });
      // 如果已登录，才去获取测评列表
      this.fetchScaleList();
    } else {
      this.setData({ 
        isLoggedIn: false,
        isLoading: false, // 未登录时，停止加载状态
        isError: false
      });
    }
  },

  /**
   * 处理登录逻辑，由 login-prompt 组件触发
   */
  handleLogin() {
    wx.showLoading({ title: '正在登录' });
    wx.login({
      success: (loginRes) => {
        if (loginRes.code) {
          wx.request({
            url: 'https://api.feelyourself.cn/api/v1/users/login',
            method: 'POST',
            data: { code: loginRes.code },
            success: (tokenRes) => {
              wx.hideLoading();
              if (tokenRes.statusCode === 200 && tokenRes.data.access_token) {
                wx.setStorageSync('token', tokenRes.data.access_token);
                wx.showToast({ title: '登录成功', icon: 'success' });
                this.setData({ isLoggedIn: true });
                this.fetchScaleList();
              } else {
                 wx.showToast({ title: '登录失败', icon: 'none' });
              }
            },
            fail: () => {
              wx.hideLoading();
              wx.showToast({ title: '登录失败，请检查网络', icon: 'none' });
            }
          });
        }
      }
    });
  },

  // --- 4. 改造核心业务函数 ---
  
  /**
   * 使用新的 request 函数获取测评列表
   */
  async fetchScaleList() {
    this.setData({ isLoading: true, isError: false });
    try {
      // 使用封装好的 request 函数
      const listData = await request({ url: '/assessments/', method: 'GET' });
      
      const processedList = listData.map(scale => {
        const iconName = scale.short_name ? scale.short_name.toLowerCase() : 'default';
        return {
          ...scale,
          iconPath: `/images/assessment/${iconName}.png`
        };
      });
      this.setData({ scaleList: processedList, isLoading: false });

    } catch (error) {
      console.error("fetchScaleList failed:", error);
      this.setData({ isError: true, isLoading: false });
    } finally {
      wx.stopPullDownRefresh();
    }
  },

  /**
   * 点击卡片，跳转到答题页面 (此函数无需修改)
   */
  goToTest(e) {
    const scaleId = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `./test?id=${scaleId}`,
    });
  },
  
  /**
   * 图标加载失败时的容错处理 (此函数无需修改)
   */
  handleIconError(e) {
    const errorIndex = e.currentTarget.dataset.index;
    const updatedPath = `scaleList[${errorIndex}].iconPath`;
    this.setData({
      [updatedPath]: DEFAULT_ICON_PATH
    });
  }
});