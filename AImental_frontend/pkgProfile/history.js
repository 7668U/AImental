// pages/profile/history.js

const SERVER_BASE_URL = 'https://api.feelyourself.cn';
const ASSESSMENTS_API_URL = `${SERVER_BASE_URL}/api/v1/assessments`;
const MOOD_ANALYSIS_HISTORY_API_URL = `${SERVER_BASE_URL}/api/v1/report/history`;
const ASSESSMENT_ANALYSIS_HISTORY_API_URL = `${SERVER_BASE_URL}/api/v1/history-analysis/`;
const { getScaleDisplayName } = require('../utils/assessment-display.js');

const REQUEST_TIMEOUT = 8000;
const MOOD_ANALYSIS_HISTORY_REPORT_KEY = 'mood_analysis_history_report';
const MOOD_ANALYSIS_FRONTEND_TYPE_MAP = {
  mood: 'mood_distribution',
  'tag-mood': 'tag_correlation',
  'word-cloud': 'word_cloud',
  color: 'color_palette'
};

const { getShareInfo, getTimelineInfo } = require('../utils/share.js');
Page({
  data: {
    navTop: 0,
    navHeight: 0,
    activeHistoryTab: 'assessment',
    isLoading: true,
    isMoodAnalysisLoading: false,
    isAssessmentAnalysisLoading: false,
    groupedHistory: [],
    moodAnalysisHistory: [],
    assessmentAnalysisHistory: [],
  },

  onLoad(options) {
    this.setNavSize();
    this.fetchHistory();
    this.fetchMoodAnalysisHistory();
    this.fetchAssessmentAnalysisHistory();
  },

  setNavSize() {
    const fallback = { statusBarHeight: 24 };
    let sysInfo = fallback;
    let menuButtonInfo = null;
    try {
      sysInfo = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
      menuButtonInfo = wx.getMenuButtonBoundingClientRect();
    } catch (e) {
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

  navigateBack() {
    wx.navigateBack({ delta: 1 });
  },

  fetchHistory() {
    this.setData({ isLoading: true });
    wx.request({
      url: `${ASSESSMENTS_API_URL}/history/`,
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
      timeout: REQUEST_TIMEOUT,
      success: (res) => {
        if (res.statusCode === 200 && Array.isArray(res.data)) {
          const groupedData = this.processHistoryData(res.data);
          this.setData({ groupedHistory: groupedData });
        } else {
          this.handleFetchError('加载失败，请稍后重试');
        }
      },
      fail: () => {
        this.handleFetchError('网络错误，请检查网络连接');
      },
      complete: () => {
        this.setData({ isLoading: false });
      }
    });
  },

  handleFetchError(title = '加载失败，请重试') {
    wx.showToast({ title: title, icon: 'none' });
  },

  switchHistoryTab(e) {
    const tab = e.currentTarget.dataset.tab;
    if (!tab || tab === this.data.activeHistoryTab) return;
    this.setData({ activeHistoryTab: tab });
  },

  fetchMoodAnalysisHistory() {
    this.setData({ isMoodAnalysisLoading: true });
    wx.request({
      url: MOOD_ANALYSIS_HISTORY_API_URL,
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
      timeout: REQUEST_TIMEOUT,
      success: (res) => {
        if (res.statusCode === 200 && Array.isArray(res.data)) {
          this.setData({ moodAnalysisHistory: this.processMoodAnalysisHistory(res.data) });
        } else {
          this.handleFetchError('心情分析历史加载失败');
        }
      },
      fail: () => {
        this.handleFetchError('网络错误，请检查网络连接');
      },
      complete: () => {
        this.setData({ isMoodAnalysisLoading: false });
      }
    });
  },

  fetchAssessmentAnalysisHistory() {
    this.setData({ isAssessmentAnalysisLoading: true });
    wx.request({
      url: ASSESSMENT_ANALYSIS_HISTORY_API_URL,
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
      timeout: REQUEST_TIMEOUT,
      success: (res) => {
        if (res.statusCode === 200 && Array.isArray(res.data)) {
          this.setData({
            assessmentAnalysisHistory: this.processAssessmentAnalysisHistory(res.data)
          });
        } else {
          this.handleFetchError('综合测评历史加载失败');
        }
      },
      fail: () => {
        this.handleFetchError('网络错误，请检查网络连接');
      },
      complete: () => {
        this.setData({ isAssessmentAnalysisLoading: false });
      }
    });
  },

  toggleExpand(e) {
    const { index } = e.currentTarget.dataset;
    const key = `groupedHistory[${index}].is_expanded`;
    const currentValue = this.data.groupedHistory[index].is_expanded;
    this.setData({
      [key]: !currentValue
    });
  },

  goToResultDetail(e) {
    try {
      const { record } = e.currentTarget.dataset;
      if (!record || !record.id) { 
        console.error("无法跳转：记录或记录ID无效", record);
        return;
      }
      // ✅ 【核心修改】不再传递整个对象，只传递 record_id
      const url = `/pkgAssessment/result?record_id=${record.id}&from=history`;
      wx.navigateTo({ url: url });

    } catch (err) {
      console.error("跳转到结果页时发生错误", err);
      wx.showToast({ title: '发生未知错误', icon: 'none' });
    }
  },

  goToMoodAnalysisReport(e) {
    const index = Number(e.currentTarget.dataset.index);
    const record = this.data.moodAnalysisHistory[index];
    if (!record || !record.start_date || !record.end_date) {
      wx.showToast({ title: '报告信息不完整，暂时无法打开', icon: 'none' });
      return;
    }
    wx.setStorageSync(MOOD_ANALYSIS_HISTORY_REPORT_KEY, {
      start_date: record.start_date,
      end_date: record.end_date,
      reports: record.reports || {},
    });
    const params = [
      `start_date=${encodeURIComponent(record.start_date)}`,
      `end_date=${encodeURIComponent(record.end_date)}`,
      'from=history'
    ].join('&');
    wx.navigateTo({
      url: `/pkgDailyCheckin/analysis?${params}`
    });
  },

  goToAssessmentAnalysisReport(e) {
    const index = Number(e.currentTarget.dataset.index);
    const record = this.data.assessmentAnalysisHistory[index];
    if (!record || !record.id) {
      wx.showToast({ title: '报告信息不完整，暂时无法打开', icon: 'none' });
      return;
    }
    wx.navigateTo({
      url: `/pkgProfile/history_analysis?id=${encodeURIComponent(record.id)}`
    });
  },

    formatDateToYYYYMMDD(timestamp) {
    const date = new Date(timestamp);
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    return `${year}-${month}-${day}`;
  },

  processHistoryData(records) {
    if (!records || records.length === 0) return [];
    const historyMap = new Map();

    records.forEach(record => {
      const scaleInfo = record.scale_info || record.scale_details || {
        id: record.scale_id || `legacy-${record.id}`,
        short_name: 'LEGACY',
        name: '历史测评',
        assessment_type: record.final_score !== null && record.final_score !== undefined
          ? 'scoring'
          : 'categorical'
      };
      record.scale_info = scaleInfo;
        
      record.completed_at_formatted = this.formatDateToYYYYMMDD(record.completed_at);
      record.display_result_level = this.getDisplayResultLevel(record.result_level);
      record.display_final_score = this.formatScore(record.final_score);
      
      const scaleId = scaleInfo.id;
      if (historyMap.has(scaleId)) {
        historyMap.get(scaleId).records.push(record);
        historyMap.get(scaleId).count += 1;
      } else {
        const shortName = scaleInfo.short_name;
        historyMap.set(scaleId, {
          scale_id: scaleId,
          scale_name: getScaleDisplayName(shortName, scaleInfo.name),
          count: 1,
          is_expanded: true,
          records: [record],
          assessment_type: scaleInfo.assessment_type
        });
      }
    });
    return Array.from(historyMap.values());
  },

  processMoodAnalysisHistory(records) {
    if (!records || records.length === 0) return [];
    const grouped = new Map();

    records.forEach((record) => {
      if (!record.start_date || !record.end_date) return;
      const key = `${record.start_date}_${record.end_date}`;
      const sortTime = this.resolveSortTime(record.updated_at || record.created_at);
      const existing = grouped.get(key);
      if (!existing) {
        grouped.set(key, {
          id: key,
          start_date: record.start_date,
          end_date: record.end_date,
          sort_time: sortTime,
          reports: {},
        });
      }

      const target = grouped.get(key);
      target.sort_time = Math.max(target.sort_time, sortTime);
      const frontendType = MOOD_ANALYSIS_FRONTEND_TYPE_MAP[record.analysis_type];
      if (!frontendType) return;
      const currentReport = target.reports[frontendType];
      if (!currentReport || sortTime >= currentReport.sort_time) {
        target.reports[frontendType] = {
          analysis_type: record.analysis_type,
          summary_text: record.summary_text || '',
          report_text: record.report_text || '',
          sort_time: sortTime,
        };
      }
    });

    return Array.from(grouped.values())
      .sort((a, b) => b.sort_time - a.sort_time);
  },

  processAssessmentAnalysisHistory(records) {
    if (!records || records.length === 0) return [];
    return records
      .filter(record => record && record.id)
      .map(record => ({
        ...record,
        created_at_formatted: this.formatRecordDateTime(record.created_at),
        overall_assessment: record.overall_assessment || '这份综合报告暂时没有摘要。'
      }));
  },

  resolveSortTime(value) {
    if (!value) return 0;
    if (typeof value === 'number') {
      return value > 1000000000000 ? value : value * 1000;
    }
    const parsed = Date.parse(value);
    return Number.isNaN(parsed) ? 0 : parsed;
  },

  formatRecordDateTime(value) {
    const time = this.resolveSortTime(value);
    if (!time) return '';
    const date = new Date(time);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hour = String(date.getHours()).padStart(2, '0');
    const minute = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day} ${hour}:${minute}`;
  },

  getDisplayResultLevel(level) {
    if (level === null || level === undefined) return '结果待确认';
    const text = String(level).trim();
    if (!text || text.toLowerCase() === 'null') return '结果待确认';
    return text;
  },

  formatScore(score) {
    if (score === null || score === undefined || score === '') return '--';
    const numericScore = Number(score);
    if (!Number.isFinite(numericScore)) return String(score);
    return String(Math.round(numericScore * 100) / 100);
  },

  handleLongPressDelete(e) {
    const { groupIndex, recordIndex, recordId } = e.currentTarget.dataset;
    wx.showModal({
      title: '删除确认',
      content: '您确定要删除这条测试记录吗？此操作无法撤销。',
      confirmColor: '#fa5151',
      success: (res) => {
        if (res.confirm) {
          this.deleteRecord(groupIndex, recordIndex, recordId);
        }
      }
    });
  },

  deleteRecord(groupIndex, recordIndex, recordId) {
    wx.showLoading({ title: '正在删除...' });
    wx.request({
      url: `${ASSESSMENTS_API_URL}/history/${recordId}`,
      method: 'DELETE',
      header: { 'Authorization': 'Bearer ' + wx.getStorageSync('token') },
      success: (apiRes) => {
        if (apiRes.statusCode === 204) {
          wx.showToast({ title: '删除成功', icon: 'success' });
          this.removeRecordFromLocalData(groupIndex, recordIndex);
        } else {
          wx.showToast({ title: (apiRes.data && apiRes.data.detail) || '删除失败', icon: 'none' });
        }
      },
      fail: () => { wx.showToast({ title: '请求失败', icon: 'none' }); },
      complete: () => { wx.hideLoading(); }
    });
  },

  removeRecordFromLocalData(groupIndex, recordIndex) {
    let groupedHistory = this.data.groupedHistory.slice();
    const targetGroup = groupedHistory[groupIndex];
    targetGroup.records.splice(recordIndex, 1);
    targetGroup.count -= 1;
    if (targetGroup.count === 0) {
      groupedHistory.splice(groupIndex, 1);
    }
    this.setData({
      groupedHistory: groupedHistory
    });
  },

  onShareAppMessage: function () {
    return getShareInfo();
  },

  onShareTimeline: function () {
    return getTimelineInfo();
  }
});
