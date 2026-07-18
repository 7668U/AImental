const SERVER_BASE_URL = 'http://127.0.0.1:8000';
const HISTORY_ANALYSIS_API_URL = `${SERVER_BASE_URL}/api/v1/history-analysis`;
const { getShareInfo, getTimelineInfo } = require('../utils/share.js');

Page({
  data: {
    navTop: 0,
    navHeight: 0,
    analysisId: '',
    isLoading: true,
    errorText: '',
    report: null
  },

  onLoad(options) {
    this.setNavSize();
    const analysisId = options && options.id ? decodeURIComponent(options.id) : '';
    if (!analysisId) {
      this.setData({
        isLoading: false,
        errorText: '报告信息不完整，暂时无法打开。'
      });
      return;
    }
    this.setData({ analysisId });
    this.fetchAnalysisReport();
  },

  setNavSize() {
    const fallback = { statusBarHeight: 24 };
    let sysInfo = fallback;
    let menuButtonInfo = null;
    try {
      sysInfo = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
      menuButtonInfo = wx.getMenuButtonBoundingClientRect();
    } catch (error) {
      menuButtonInfo = null;
    }
    const statusBarHeight = sysInfo.statusBarHeight || fallback.statusBarHeight;
    const navHeight = menuButtonInfo
      ? menuButtonInfo.height + (menuButtonInfo.top - statusBarHeight) * 2
      : 44;
    this.setData({
      navTop: statusBarHeight,
      navHeight
    });
  },

  fetchAnalysisReport() {
    this.setData({ isLoading: true, errorText: '' });
    wx.request({
      url: `${HISTORY_ANALYSIS_API_URL}/${encodeURIComponent(this.data.analysisId)}`,
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
      timeout: 8000,
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          const payload = res.data;
          this.setData({
            report: {
              ...payload,
              createdAtLabel: this.formatDateTime(payload.created_at),
              historyCount: Array.isArray(payload.analyzed_history_ids)
                ? payload.analyzed_history_ids.length
                : 0
            }
          });
          return;
        }
        this.setData({
          errorText: (res.data && res.data.detail) || '报告加载失败，请稍后重试。'
        });
      },
      fail: () => {
        this.setData({ errorText: '网络连接失败，请稍后重试。' });
      },
      complete: () => {
        this.setData({ isLoading: false });
      }
    });
  },

  formatDateTime(value) {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hour = String(date.getHours()).padStart(2, '0');
    const minute = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day} ${hour}:${minute}`;
  },

  navigateBack() {
    wx.navigateBack({ delta: 1 });
  },

  retryLoad() {
    if (!this.data.analysisId) return;
    this.fetchAnalysisReport();
  },

  onShareAppMessage() {
    return getShareInfo();
  },

  onShareTimeline() {
    return getTimelineInfo();
  }
});
