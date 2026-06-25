const { getShareInfo, getTimelineInfo } = require('../../utils/share.js');
const { loginWithBackend } = require('../../utils/auth.js');
// pages/assessment/index.js

const SERVER_BASE_URL = 'http://127.0.0.1:8000';
const DEFAULT_ICON_PATH = '/images/assessment/default.png';
const DEFAULT_CATEGORY = '专业测试';

// --- [新增] 借鉴自 daily-checkin 的封装网络请求函数 ---
function request(options) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token');
    wx.request({
      ...options,
      url: `${SERVER_BASE_URL}/api/v1${options.url}`, // 拼接基础URL
      header: {
        ...options.header,
        'Authorization': `Bearer ${token}`
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data); // 请求成功，resolve 数据
        } else if (res.statusCode === 401) {
          // 特殊处理401错误，代表Token失效
          getCurrentPages().pop().clearLoginStateAndShowToast();
          reject(res);
        }
        else {
          reject(res); // 其他错误状态码
        }
      },
      fail(err) {
        reject(err); // 网络层面的失败
      }
    });
  });
}

Page({
  data: {
    isLoggedIn: false,
    statusBarHeight: 0,
    rawScaleList: [],
    displayScaleList: [],
    activeCategory: DEFAULT_CATEGORY,
    isLoading: false,
    isError: false,
  },

  onShow() {
    this.checkLoginStatus();
    const systemInfo = wx.getSystemInfoSync();
    this.setData({
      statusBarHeight: systemInfo.statusBarHeight
    });
  },
  
  checkLoginStatus() {
    const token = wx.getStorageSync('token');
    if (token) {
      this.setData({ isLoggedIn: true });
      this.fetchScaleList();
    } else {
      this.setData({ isLoggedIn: false });
    }
  },

  // --- [修改] 采用 async/await 重构登录函数，逻辑更清晰 ---
  async handleLogin() {
    wx.showLoading({ title: '???...' });
    try {
      const tokenRes = await loginWithBackend(SERVER_BASE_URL + '/api/v1');
      if (tokenRes.access_token) {
        wx.setStorageSync('token', tokenRes.access_token);
        wx.hideLoading();
        wx.showToast({ title: '????', icon: 'success' });
        this.checkLoginStatus();
      } else {
        throw new Error('???????token');
      }
    } catch (error) {
      wx.hideLoading();
      wx.showToast({ title: '??????????', icon: 'none' });
      console.error('??????: ' , error);
    }
  },

  // --- [修改] 使用封装的 request 函数获取数据 ---
  async fetchScaleList() {
    this.setData({ isLoading: true, isError: false });
    try {
      // 直接调用封装的 request 函数
      const data = await request({ url: '/assessments/' });

      const rawList = data || [];
      const processedList = rawList.map(scale => ({
        ...scale,
        iconPath: `/images/assessment/${scale.short_name ? scale.short_name.toLowerCase() : 'default'}.png`
      }));
      
      const filteredDisplayList = processedList.filter(scale => scale.category === this.data.activeCategory);

      this.setData({
        rawScaleList: processedList,
        displayScaleList: filteredDisplayList,
        isError: false
      });

    } catch (error) {
      // 无论是401还是其他网络错误，都会在这里被捕获
      this.setData({ isError: true });
      console.error("获取测评列表失败: ", error);
    } finally {
      // 无论成功或失败，都结束加载状态
      this.setData({ isLoading: false });
      wx.stopPullDownRefresh();
    }
  },

  // [新增] 清理登录状态并提示的函数，用于被 request 调用
  clearLoginStateAndShowToast() {
    wx.removeStorageSync('token');
    wx.removeStorageSync('userInfo');
    this.setData({ isLoggedIn: false });
    wx.showToast({ title: '登录已失效，请重新登录', icon: 'none' });
  },

  onPullDownRefresh() {
    if (this.data.isLoggedIn) {
      this.fetchScaleList();
    } else {
      wx.stopPullDownRefresh();
    }
  },

  // --- 以下是与UI交互的函数，保持不变 ---
  switchCategory(e) {
    const newCategory = e.currentTarget.dataset.category;
    if (newCategory === this.data.activeCategory) return;
    this.setData({ activeCategory: newCategory });
    this.filterAndSetDisplayList(newCategory);
  },
  filterAndSetDisplayList(categoryName) {
    const filteredList = this.data.rawScaleList.filter(scale => scale.category === categoryName);
    this.setData({ displayScaleList: filteredList });
  },
  goToTest(e) {
    const scaleId = e.currentTarget.dataset.id;
    wx.navigateTo({ url: `/pkgAssessment/intro/intro?id=${scaleId}` });
  },
  handleIconError(e) {
    const errorIndex = e.currentTarget.dataset.index;
    const updatedPath = `displayScaleList[${errorIndex}].iconPath`;
    this.setData({ [updatedPath]: DEFAULT_ICON_PATH });
  },

  onShareAppMessage: function () {
    return getShareInfo();
  },

  onShareTimeline: function () {
    return getTimelineInfo();
  }
});
