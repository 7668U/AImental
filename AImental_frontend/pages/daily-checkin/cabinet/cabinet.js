// pages/daily-checkin/cabinet/cabinet.js (The final, correct version)

// ---- Request Helper ----
const BASE_URL = getApp().globalData?.apiBase || 'http://127.0.0.1:8000/api/v1';
function request(options) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token');
    wx.request({
      ...options,
      url: `${BASE_URL}${options.url}`,
      header: {
        'Authorization': token ? `Bearer ${token}` : '',
        'Content-Type': 'application/json',
        ...options.header
      },
      success(res) {
        if (res.statusCode === 401) {
          wx.showToast({ title: '登录已过期，请重新登录', icon: 'none' });
          reject(res);
          return;
        }
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          console.error('Request failed:', res.statusCode, res.data);
          reject(res);
        }
      },
      fail(err) {
        console.error('Request error:', err);
        reject(err);
      }
    });
  });
}

function formatNameForCover(name) {
  if (!name) return [];
  const arr = [];
  for (let i = 0; i < name.length; i += 2) arr.push(name.substring(i, i + 2));
  return arr;
}

const { getShareInfo, getTimelineInfo } = require('../../../utils/share.js');
Page({
  data: {
    // === 布局旋钮 ===
    contentTopLift: 56,
    titleBottomGap: 50,
    shelfPullUp: 0,

    // 业务数据
    notebooks: [],

    // action sheet
    showActionSheet: false,
    currentNotebookId: null,
    currentNotebookName: null,
    currentNotebookCover: null,

    // modal (create/rename)
    showModal: false,
    modalMode: 'create',
    notebookNameInput: '',
    selectedCoverForCreate: '',
    editingNotebookId: null,

    // cover selector
    showCoverSelectorForUpdate: false,

    // 状态
    loading: false
  },

  // =======================================================
  // 【最终修改】确保 onLoad 和 onShow 都能触发数据加载
  // =======================================================
  onLoad() {
    // 页面首次加载时获取数据
    this.fetchNotebooks();
  },

  onShow() {
    // 每次页面显示时（包括从后一页返回时）都获取数据
    // 这能保证从 note 页面返回后，列表总是最新的
    this.fetchNotebooks();
  },

  onPullDownRefresh() {
    this.fetchNotebooks().finally(() => wx.stopPullDownRefresh());
  },

  async fetchNotebooks() {
    this.setData({ loading: true });
    wx.showLoading({ title: '加载中...' });
    try {
      const notebooks = await request({ url: '/notebooks/' });
      const formatted = (notebooks || []).map(n => ({
        ...n, formattedName: formatNameForCover(n.name)
      }));
      this.setData({ notebooks: formatted });
    } catch (e) {
      wx.showToast({ title: '加载失败', icon: 'none' });
    } finally {
      this.setData({ loading: false });
      wx.hideLoading();
    }
  },

  navigateToNote(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: `/pages/daily-checkin/note/note?id=${id}` });
  },

  // ---- Action Sheet ----
  showActionMenu(e) {
    const { id, name, cover } = e.currentTarget.dataset;
    this.setData({
      showActionSheet: true,
      currentNotebookId: id,
      currentNotebookName: name,
      currentNotebookCover: cover
    });
  },
  hideActionSheet() { this.setData({ showActionSheet: false }); },
  preventMaskTap() { },

  confirmDeleteNotebook() {
    this.setData({ showActionSheet: false });
    wx.showModal({
      title: '确认删除',
      content: '删除后，笔记本内的所有内容将无法恢复，确定要删除吗？',
      confirmColor: '#ee0a24',
      success: (res) => {
        if (res.confirm) this.deleteNotebook();
        else this.setData({
          currentNotebookId: null,
          currentNotebookName: null,
          currentNotebookCover: null
        });
      }
    });
  },

  async deleteNotebook() {
    const id = this.data.currentNotebookId;
    if (!id) return wx.showToast({ title: '错误：未选中笔记本', icon: 'none' });
    
    wx.showLoading({ title: '删除中...' });
    try {
      await request({ url: `/notebooks/${id}`, method: 'DELETE' });
      wx.hideLoading();
      wx.showToast({ title: '删除成功', icon: 'success' });
      this.setData({ currentNotebookId: null, currentNotebookName: null, currentNotebookCover: null });
      this.fetchNotebooks();
    } catch (e) {
      wx.hideLoading();
      wx.showToast({ title: '删除失败', icon: 'none' });
    }
  },

  // ---- Modal ----
  showCreateModal() {
    this.setData({
      showModal: true,
      modalMode: 'create',
      notebookNameInput: '',
      selectedCoverForCreate: '',
      editingNotebookId: null
    });
  },
  showRenameModal() {
    this.setData({
      showModal: true,
      modalMode: 'rename',
      notebookNameInput: this.data.currentNotebookName || '',
      editingNotebookId: this.data.currentNotebookId,
      showActionSheet: false
    });
  },
  hideModal() { this.setData({ showModal: false }); },
  handleNameInput(e) { this.setData({ notebookNameInput: e.detail.value }); },
  onCoverSelectForCreate(e) { this.setData({ selectedCoverForCreate: e.detail.cover }); },

  async handleConfirm() {
    const { modalMode, notebookNameInput, selectedCoverForCreate, editingNotebookId } = this.data;
    const name = (notebookNameInput || '').trim();

    if (!name) return wx.showToast({ title: '名称不能为空', icon: 'none' });
    if (modalMode === 'create' && !selectedCoverForCreate) {
      return wx.showToast({ title: '请选择封面', icon: 'none' });
    }

    wx.showLoading({ title: '保存中...' });
    try {
      if (modalMode === 'create') {
        await request({
          url: '/notebooks/',
          method: 'POST',
          data: { name, cover_image: selectedCoverForCreate }
        });
      } else {
        await request({ url: `/notebooks/${editingNotebookId}`, method: 'PUT', data: { name } });
      }
      this.hideModal();
      await this.fetchNotebooks();
      wx.showToast({ title: '保存成功' });
    } catch (e) {
      wx.hideLoading();
      wx.showToast({ title: '操作失败', icon: 'none' });
    }
  },

  // ---- Cover Selector for Update ----
  openCoverSelector() {
    this.setData({ showCoverSelectorForUpdate: true, showActionSheet: false });
  },
  hideCoverSelector() {
    this.setData({ showCoverSelectorForUpdate: false });
  },

  async handleUpdateCover(e) {
    const selectedCover = e.detail.cover;
    const id = this.data.currentNotebookId;
    if (!id) return;

    this.hideCoverSelector();
    wx.showLoading({ title: '正在更换封面...' });
    try {
      await request({ url: `/notebooks/${id}`, method: 'PUT', data: { cover_image: selectedCover } });
      await this.fetchNotebooks();
      wx.showToast({ title: '更换成功', icon: 'success' });
      this.setData({ currentNotebookCover: selectedCover });
    } catch (e) {
      wx.hideLoading();
      wx.showToast({ title: '操作失败', icon: 'none' });
    }
  },

  onShareAppMessage: function () {
    return getShareInfo();
  },

  onShareTimeline: function () {
    return getTimelineInfo();
  }
});