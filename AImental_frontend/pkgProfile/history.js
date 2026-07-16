// pages/profile/history.js

const SERVER_BASE_URL = 'http://127.0.0.1:8000';
const ASSESSMENTS_API_URL = `${SERVER_BASE_URL}/api/v1/assessments`;
const MOOD_ANALYSIS_HISTORY_API_URL = `${SERVER_BASE_URL}/api/v1/report/history`;
const { getScaleDisplayName } = require('../utils/assessment-display.js');

const DELETE_BTN_WIDTH = 80;
const REQUEST_TIMEOUT = 8000;
const MOOD_ANALYSIS_TYPE_ORDER = {
  mood: 1,
  'tag-mood': 2,
  'word-cloud': 3,
  color: 4
};
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
    groupedHistory: [],
    moodAnalysisHistory: [],
    touchStartX: 0,
  },

  onLoad(options) {
    this.setNavSize();
    this.fetchHistory();
    this.fetchMoodAnalysisHistory();
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
    this.closeOtherSwipedItems(-1, -1);
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

  toggleExpand(e) {
    const { index } = e.currentTarget.dataset;
    const key = `groupedHistory[${index}].is_expanded`;
    const currentValue = this.data.groupedHistory[index].is_expanded;
    this.setData({
      [key]: !currentValue
    });
  },

  goToResultDetail(e) {
    this.closeOtherSwipedItems(-1, -1);
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
    const { record } = e.currentTarget.dataset;
    if (!record || !record.start_date || !record.end_date || !record.frontend_analysis_type) {
      wx.showToast({ title: '报告信息不完整，暂时无法打开', icon: 'none' });
      return;
    }
    const params = [
      `type=${encodeURIComponent(record.frontend_analysis_type)}`,
      `start_date=${encodeURIComponent(record.start_date)}`,
      `end_date=${encodeURIComponent(record.end_date)}`,
      'from=history'
    ].join('&');
    wx.navigateTo({
      url: `/pkgDailyCheckin/analysis?${params}`
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
      // 增加一个安全检查，如果记录没有 scale_info，则跳过
      if (!record.scale_info) {
        console.warn("记录缺少 scale_info，已跳过:", record);
        return;
      }
        
      record.x_offset = 0;
      record.completed_at_formatted = this.formatDateToYYYYMMDD(record.completed_at);
      record.display_result_level = this.getDisplayResultLevel(record.result_level);
      record.display_final_score = this.formatScore(record.final_score);
      
      const scaleId = record.scale_info.id;
      if (historyMap.has(scaleId)) {
        historyMap.get(scaleId).records.push(record);
        historyMap.get(scaleId).count += 1;
      } else {
        const shortName = record.scale_info.short_name;
        historyMap.set(scaleId, {
          scale_id: scaleId,
          scale_name: getScaleDisplayName(shortName, record.scale_info.name),
          count: 1,
          is_expanded: true,
          records: [record],
          // ✅ 【核心修改已集成】
          // 从当前记录的 scale_info 中获取 assessment_type，并存入分组信息
          assessment_type: record.scale_info.assessment_type 
        });
      }
    });
    return Array.from(historyMap.values());
  },

  processMoodAnalysisHistory(records) {
    if (!records || records.length === 0) return [];
    return records
      .map(record => ({
        ...record,
        date_range: `${record.start_date || '--'} 至 ${record.end_date || '--'}`,
        display_report: record.report_text || record.summary_text || '暂无报告内容',
        display_summary: record.summary_text || '',
        updated_at_formatted: this.formatRecordDateTime(record.updated_at),
        sort_time: this.resolveSortTime(record.updated_at || record.created_at),
        type_order: MOOD_ANALYSIS_TYPE_ORDER[record.analysis_type] || 99,
        frontend_analysis_type: MOOD_ANALYSIS_FRONTEND_TYPE_MAP[record.analysis_type] || ''
      }))
      .sort((a, b) => {
        if (b.sort_time !== a.sort_time) return b.sort_time - a.sort_time;
        return a.type_order - b.type_order;
      });
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

  handleTouchStart(e) {
    this.setData({ touchStartX: e.touches[0].clientX });
  },

  handleTouchMove(e) {
    const { groupIndex, recordIndex } = e.currentTarget.dataset;
    const moveX = e.touches[0].clientX;
    const deltaX = moveX - this.data.touchStartX;
    if (deltaX < 0) {
      const newOffset = Math.max(deltaX, -DELETE_BTN_WIDTH);
      const key = `groupedHistory[${groupIndex}].records[${recordIndex}].x_offset`;
      this.setData({ [key]: newOffset });
    }
  },

  handleTouchEnd(e) {
    const { groupIndex, recordIndex } = e.currentTarget.dataset;
    const endX = e.changedTouches[0].clientX;
    const deltaX = endX - this.data.touchStartX;
    const threshold = DELETE_BTN_WIDTH / 2;
    const finalOffset = deltaX < -threshold ? -DELETE_BTN_WIDTH : 0;
    const key = `groupedHistory[${groupIndex}].records[${recordIndex}].x_offset`;
    this.closeOtherSwipedItems(groupIndex, recordIndex);
    this.setData({ [key]: finalOffset });
  },

  closeOtherSwipedItems(currentGroupIndex, currentRecordIndex) {
    const updates = {};
    this.data.groupedHistory.forEach((group, gIndex) => {
      group.records.forEach((record, rIndex) => {
        if ((gIndex !== currentGroupIndex || rIndex !== currentRecordIndex) && record.x_offset < 0) {
          updates[`groupedHistory[${gIndex}].records[${rIndex}].x_offset`] = 0;
        }
      });
    });
    if (Object.keys(updates).length > 0) {
      this.setData(updates);
    }
  },

  handleConfirmDelete(e) {
    const { groupIndex, recordIndex, recordId } = e.currentTarget.dataset;
    wx.showModal({
      title: '删除确认',
      content: '您确定要删除这条测试记录吗？此操作无法撤销。',
      confirmColor: '#fa5151',
      success: (res) => {
        if (res.confirm) {
          this.deleteRecord(groupIndex, recordIndex, recordId);
        } else {
          const key = `groupedHistory[${groupIndex}].records[${recordIndex}].x_offset`;
          this.setData({ [key]: 0 });
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
