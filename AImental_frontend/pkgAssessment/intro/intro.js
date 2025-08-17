const { getShareInfo, getTimelineInfo } = require('../../utils/share.js');
// pages/assessment/intro/intro.js

// --- 抽离出可复用的网络请求函数 ---
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

const DEFAULT_ICON_PATH = '/images/assessment/default.png';

Page({
  data: {
    scale: null, // Stores the fetched scale details
    scaleId: null, // Stores the ID passed from the previous page
    isLoading: true,
    isError: false
  },

  onLoad(options) {
    const scaleId = options.id; // Get the scaleId from the URL parameters
    if (scaleId) {
      this.setData({ scaleId: scaleId });
      this.fetchScaleDetails(scaleId);
    } else {
      this.setData({ isError: true, isLoading: false });
      wx.showToast({
        title: '问卷ID缺失',
        icon: 'none'
      });
    }
  },

  async fetchScaleDetails(scaleId) {
    this.setData({ isLoading: true, isError: false });
    try {
      // Assuming there's an API endpoint to get a single assessment by ID
      // If not, we might need to fetch all and filter, or suggest a new API.
      const scaleData = await request({ url: `/assessments/${scaleId}`, method: 'GET' });

      // Process icon path similar to index.js
      const iconName = scaleData.short_name ? scaleData.short_name.toLowerCase() : 'default';
      scaleData.iconPath = `/images/assessment/${iconName}.png`;

      this.setData({
        scale: scaleData,
        isLoading: false
      });
    } catch (error) {
      console.error("fetchScaleDetails failed:", error);
      this.setData({ isError: true, isLoading: false });
      wx.showToast({
        title: '加载问卷详情失败',
        icon: 'none'
      });
    }
  },

  startTest() {
    const scaleId = this.data.scaleId;
    if (scaleId) {
      wx.redirectTo({ // Use redirectTo to prevent going back to intro page from test page
        url: `/pkgAssessment/test?id=${scaleId}`, // Adjust path if test page is not directly under assessment
      });
    } else {
      wx.showToast({
        title: '无法开始测试，问卷ID缺失',
        icon: 'none'
      });
    }
  },

  // Optional: Handle icon loading error for the intro page icon
  handleIconError(e) {
    this.setData({
      'scale.iconPath': DEFAULT_ICON_PATH
    });
  },

  onShareAppMessage: function () {
    return getShareInfo();
  },

  onShareTimeline: function () {
    return getTimelineInfo();
  }
});