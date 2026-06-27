// pages/profile/history.js

const SERVER_BASE_URL = 'http://127.0.0.1:8000';
const ASSESSMENTS_API_URL = `${SERVER_BASE_URL}/api/v1/assessments`;
const ANALYSIS_API_URL = `${SERVER_BASE_URL}/api/v1/history-analysis`;

const DEFAULT_ICON_PATH = '/images/assessment/default.png';
const DELETE_BTN_WIDTH = 80;
const SCALE_ICON_ALIASES = {
  'BDI-II': 'bdi-ii',
  SDS: 'sds'
};

const SCALE_DISPLAY_NAMES = {
  IAS: '互动焦虑量表'
};

const { getShareInfo, getTimelineInfo } = require('../utils/share.js');
Page({
  data: {
    isLoading: true,
    groupedHistory: [],
    touchStartX: 0,
  },

  onLoad(options) {
    this.fetchHistory();
  },

  goToAnalysis(e) {
    const { scale, records } = e.currentTarget.dataset.scale;
    // 此处的判断在WXML中已经处理，但为保险起见，JS中也可以保留
    if (records.length < 5) {
      wx.showToast({ title: '测试次数不足5次，暂时无法分析', icon: 'none' });
      return;
    }

    const history_ids = records.map(r => r.id);

    wx.showLoading({
      title: '正在生成报告...',
      mask: true
    });

    wx.request({
      url: `${ANALYSIS_API_URL}/synthesize`,
      method: 'POST',
      header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('token'),
        'Content-Type': 'application/json'
      },
      data: {
        history_ids: history_ids
      },
      success: (res) => {
        if (res.statusCode === 200) {
          const analysisReport = res.data;
          
          wx.navigateTo({
            url: `/pkgProfile/history_analysis`,
            success: (navRes) => {
              navRes.eventChannel.emit('acceptDataFromHistoryPage', { 
                groupData: e.currentTarget.dataset.scale,
                reportData: analysisReport
              });
            }
          });

        } else {
          wx.showToast({
            title: (res.data && res.data.detail) || '报告生成失败，请稍后重试',
            icon: 'none'
          });
        }
      },
      fail: () => {
        wx.showToast({ title: '网络请求失败', icon: 'none' });
      },
      complete: () => {
        wx.hideLoading();
      }
    });
  },

  fetchHistory() {
    this.setData({ isLoading: true });
    wx.request({
      url: `${ASSESSMENTS_API_URL}/history/`,
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
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

  handleIconError(e) {
    const { index } = e.currentTarget.dataset;
    const errorPath = `groupedHistory[${index}].iconPath`;
    if (this.data.groupedHistory[index].iconPath !== DEFAULT_ICON_PATH) {
      this.setData({ [errorPath]: DEFAULT_ICON_PATH });
    }
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
        const iconName = SCALE_ICON_ALIASES[shortName] || (shortName ? shortName.toLowerCase() : 'default');
        const iconPath = `/images/assessment/scale-icons/${iconName}.png`;
        
        historyMap.set(scaleId, {
          scale_id: scaleId,
          scale_name: SCALE_DISPLAY_NAMES[shortName] || record.scale_info.name,
          iconPath: iconPath,
          count: 1,
          is_expanded: false,
          records: [record],
          // ✅ 【核心修改已集成】
          // 从当前记录的 scale_info 中获取 assessment_type，并存入分组信息
          assessment_type: record.scale_info.assessment_type 
        });
      }
    });
    return Array.from(historyMap.values());
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
