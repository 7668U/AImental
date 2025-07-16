// pages/profile/history.js

const SERVER_BASE_URL = 'http://49.233.220.130:8000';
// ✅ 【修改】将 API URL 分得更细，方便调用不同模块的接口
const ASSESSMENTS_API_URL = `${SERVER_BASE_URL}/api/v1/assessments`;
const ANALYSIS_API_URL = `${SERVER_BASE_URL}/api/v1/history-analysis`;

const DEFAULT_ICON_PATH = '/images/assessment/default.png';
const DELETE_BTN_WIDTH = 80;

Page({
  data: {
    isLoading: true,
    groupedHistory: [],
    touchStartX: 0,
  },

  onLoad(options) {
    this.fetchHistory();
  },

  // ✅ 【核心修改】重写 goToAnalysis 函数
  goToAnalysis(e) {
    const { scale, records } = e.currentTarget.dataset.scale;
    if (records.length < 5) {
      wx.showToast({ title: '测试次数不足5次，暂时无法分析', icon: 'none' });
      return;
    }

    // 1. 提取当前分组下所有记录的ID
    const history_ids = records.map(r => r.id);

    // 2. 显示加载提示，因为AI分析需要时间
    wx.showLoading({
      title: '正在生成报告...',
      mask: true
    });

    // 3. 调用我们新建的后端AI分析接口
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
          // 4. 成功获取报告后，跳转页面并通过 eventChannel 传递数据
          const analysisReport = res.data;
          
          wx.navigateTo({
            url: `/pages/profile/history_analysis`,
            success: (navRes) => {
              // 使用 eventChannel “投喂”数据给下一个页面
              navRes.eventChannel.emit('acceptDataFromHistoryPage', { 
                groupData: e.currentTarget.dataset.scale, // 传递包含记录和量表信息的整个分组
                reportData: analysisReport // 传递AI分析报告
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

  // --- 以下是原有的其他函数，保持不变 ---

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
      if (!record) { return; }
      const recordString = JSON.stringify(record);
      const encodedRecord = encodeURIComponent(recordString);
      const url = `/pages/assessment/result?data=${encodedRecord}&from=history`;
      wx.navigateTo({
        url: url,
        fail: (err) => {
          if (err.errMsg && err.errMsg.includes('too large')) {
            wx.showToast({ title: '结果数据过大，无法跳转', icon: 'none' });
          }
        }
      });
    } catch (err) {
      wx.showToast({ title: '发生未知错误', icon: 'none' });
    }
  },

  processHistoryData(records) {
    if (!records || records.length === 0) return [];
    const historyMap = new Map();
    records.forEach(record => {
      record.x_offset = 0;
      record.completed_at_formatted = new Date(record.completed_at).toLocaleString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' });
      const scaleId = record.scale_info.id;
      if (historyMap.has(scaleId)) {
        historyMap.get(scaleId).records.push(record);
        historyMap.get(scaleId).count += 1;
      } else {
        const shortName = record.scale_info.short_name;
        const iconName = shortName ? shortName.toLowerCase() : 'default';
        const iconPath = `/images/assessment/${iconName}.png`;
        historyMap.set(scaleId, {
          scale_id: scaleId,
          scale_name: record.scale_info.name,
          iconPath: iconPath,
          count: 1,
          is_expanded: false,
          records: [record]
        });
      }
    });
    return Array.from(historyMap.values());
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
  }
});