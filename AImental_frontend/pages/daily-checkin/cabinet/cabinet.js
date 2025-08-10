// pages/daily-checkin/cabinet/cabinet.js

// 网络请求函数 (可封装成公共模块)
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
          console.error('Request failed with status:', res.statusCode, res.data);
          reject(res);
        }
      },
      fail(err) {
        console.error('Request failed:', err);
        reject(err);
      }
    });
  });
}

function formatNameForCover(name) {
  if (!name) return [];
  const nameArray = [];
  for (let i = 0; i < name.length; i += 2) {
    nameArray.push(name.substring(i, i + 2));
  }
  return nameArray;
}

Page({
  data: {
    navBarHeight: getApp().globalData.navBarHeight,
    notebooks: [],
    showActionSheet: false,
    currentNotebookId: null,
    currentNotebookName: null,
    
    // --- New Modal State ---
    showModal: false,
    modalMode: 'create', // 'create' or 'rename'
    notebookNameInput: '',
    selectedCoverForCreate: '',
    editingNotebookId: null,

    // --- Cover Selector for Update ---
    showCoverSelectorForUpdate: false,
  },

  onShow() {
    this.fetchNotebooks();
  },

  async fetchNotebooks() {
    wx.showLoading({ title: '加载中...' });
    try {
      const notebooks = await request({ url: '/notebooks/' });
      const formattedNotebooks = notebooks.map(n => ({
        ...n,
        formattedName: formatNameForCover(n.name)
      }));
      this.setData({ notebooks: formattedNotebooks });
    } catch (error) {
      wx.showToast({ title: '加载失败', icon: 'none' });
    } finally {
      wx.hideLoading();
    }
  },

  goBack() {
    wx.navigateBack();
  },

  navigateToNote(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/daily-checkin/note/note?id=${id}`,
    });
  },

  // --- Modal Logic ---
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
      notebookNameInput: this.data.currentNotebookName,
      editingNotebookId: this.data.currentNotebookId,
      showActionSheet: false
    });
  },

  hideModal() {
    this.setData({ showModal: false });
  },

  handleNameInput(e) {
    this.setData({ notebookNameInput: e.detail.value });
  },

  onCoverSelectForCreate(e) {
    this.setData({ selectedCoverForCreate: e.detail.cover });
  },

  async handleConfirm() {
    const { modalMode, notebookNameInput, selectedCoverForCreate, editingNotebookId } = this.data;

    if (!notebookNameInput.trim()) {
      wx.showToast({ title: '名称不能为空', icon: 'none' });
      return;
    }

    wx.showLoading({ title: '保存中...' });

    try {
      if (modalMode === 'create') {
        if (!selectedCoverForCreate) {
          wx.showToast({ title: '请选择封面', icon: 'none' });
          return;
        }
        await request({
          url: '/notebooks/',
          method: 'POST',
          data: { name: notebookNameInput, cover_image: selectedCoverForCreate }
        });
      } else { // rename mode
        await request({
          url: `/notebooks/${editingNotebookId}`,
          method: 'PUT',
          data: { name: notebookNameInput }
        });
      }
      wx.hideLoading();
      this.hideModal();
      this.fetchNotebooks(); // Refresh list
    } catch (error) {
      wx.hideLoading();
      wx.showToast({ title: '操作失败', icon: 'none' });
    }
  },

  // --- Cover Selector for Update Logic ---
  openCoverSelector() {
    this.setData({ showCoverSelectorForUpdate: true, showActionSheet: false });
  },

  hideCoverSelector() {
    this.setData({ showCoverSelectorForUpdate: false });
  },

  async handleUpdateCover(e) {
    const selectedCover = e.detail.cover;
    this.hideCoverSelector();
    wx.showLoading({ title: '正在更换封面...' });
    try {
      await request({
        url: `/notebooks/${this.data.currentNotebookId}`,
        method: 'PUT',
        data: { cover_image: selectedCover }
      });
      wx.hideLoading();
      this.fetchNotebooks(); // Refresh list
    } catch (error) {
      wx.hideLoading();
      wx.showToast({ title: '操作失败', icon: 'none' });
    }
  },

  // --- Action Sheet Logic ---
  showActionMenu(e) {
    const { id, name } = e.currentTarget.dataset;
    this.setData({
      showActionSheet: true,
      currentNotebookId: id,
      currentNotebookName: name
    });
  },

  hideActionSheet() {
    this.setData({ showActionSheet: false });
  },

  preventMaskTap() {},

  confirmDeleteNotebook() {
    // Hide the sheet, but keep the ID for the next step
    this.setData({ showActionSheet: false });

    wx.showModal({
      title: '确认删除',
      content: '删除后，笔记本内的所有内容将无法恢复，确定要删除吗？',
      confirmColor: '#ee0a24',
      success: (res) => {
        if (res.confirm) {
          this.deleteNotebook();
        } else {
          // If user cancels, clear the now-unused ID
          this.setData({ currentNotebookId: null, currentNotebookName: null });
        }
      }
    });
  },

  async deleteNotebook() {
    if (!this.data.currentNotebookId) {
      wx.showToast({ title: '错误：未选中笔记本', icon: 'none' });
      return;
    }
    wx.showLoading({ title: '删除中...' });
    try {
      await request({
        url: `/notebooks/${this.data.currentNotebookId}`,
        method: 'DELETE'
      });
      wx.hideLoading();
      wx.showToast({ title: '删除成功', icon: 'success' });
      
      const newNotebooks = this.data.notebooks.filter(n => n.id !== this.data.currentNotebookId);
      
      this.setData({ 
          notebooks: newNotebooks, 
          currentNotebookId: null,
          currentNotebookName: null
      });

    } catch (error) {
      wx.hideLoading();
      wx.showToast({ title: '删除失败', icon: 'none' });
      this.setData({ currentNotebookId: null, currentNotebookName: null });
    }
  }
});