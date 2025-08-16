// pages/daily-checkin/note/note.js (The final, corrected version for the simplified backend)

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
          wx.showToast({ title: '登录已过期', icon: 'none' });
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

const { getShareInfo, getTimelineInfo } = require('../../../utils/share.js');
Page({
  data: {
    navBarHeight: getApp().globalData.navBarHeight,
    statusBarHeight: getApp().globalData.statusBarHeight,
    
    // 【修正】笔记本名称固定，不再需要从后端获取
    notebookName: '我的记事簿',
    
    todos: [],
    notes: [],
    uncompletedTodoCount: 0,
    
    isEditing: false,
    showTodoModal: false,
    currentTodo: { id: null, content: '' },
    showNoteModal: false,
    currentNote: { id: null, title: '', content: '' },
  },

  onLoad() {
    this.fetchNotebookDetails();
  },

  onPullDownRefresh() {
    this.fetchNotebookDetails().finally(() => wx.stopPullDownRefresh());
  },

  onUnload() {
    wx.hideLoading();
  },

  // ===================================================
  // 【最终核心修正】修正数据获取函数以匹配最终的后端接口
  // ===================================================
  async fetchNotebookDetails() {
    wx.showLoading({ title: '加载中...' });
    try {
      // 【修正】请求正确的、最终的后端接口 GET /notes/
      // 这个接口直接返回一个包含所有笔记和待办的数组
      const allItems = await request({ url: '/notes/' });
      
      const todos = allItems.filter(item => item.item_type === 'todo');
      const notes = allItems.filter(item => item.item_type === 'note');
      
      // 【修正】数据源已改变，不再有 notebook_name，直接设置 notes
      this.setData({
        notes: notes
      });

      this.updateAndSortTodos(todos);

    } catch (error) {
      console.error("加载详情失败: ", error);
      wx.showToast({ title: '加载失败，请重试', icon: 'none' });
    } finally {
      wx.hideLoading();
    }
  },

  updateAndSortTodos(todos) {
    const sortedTodos = todos.sort((a, b) => a.is_completed - b.is_completed);
    const count = todos.filter(t => !t.is_completed).length;
    this.setData({
      todos: sortedTodos,
      uncompletedTodoCount: count
    });
  },

  hideModals() {
    this.setData({ showTodoModal: false, showNoteModal: false });
  },

  onModalInput(e) {
    const field = e.currentTarget.dataset.field;
    const value = e.detail.value;
    if (this.data.showTodoModal) {
      this.setData({ 'currentTodo.content': value });
    } else if (this.data.showNoteModal) {
      this.setData({ [`currentNote.${field}`]: value });
    }
  },

  // --- 待办 (Todo) 逻辑 ---
  showAddTodoModal() { this.setData({ isEditing: false, currentTodo: { id: null, content: '' }, showTodoModal: true, }); },
  showEditTodoModal(e) {
    const todo = this.data.todos.find(t => t.id === e.currentTarget.dataset.id);
    if (todo) { this.setData({ isEditing: true, currentTodo: { ...todo }, showTodoModal: true, }); }
  },
  
  async handleTodoModalConfirm() {
    const todo = this.data.currentTodo;
    if (!todo.content.trim()) { return wx.showToast({ title: '内容不能为空', icon: 'none' }); }
    
    this.hideModals();
    wx.showLoading({ title: '保存中...' });

    try {
      if (this.data.isEditing) {
        await request({ url: `/notes/${todo.id}`, method: 'PUT', data: { content: todo.content } });
      } else {
        // 这个创建逻辑已经是正确的，请求 /notes/
        await request({
          url: `/notes/`,
          method: 'POST',
          data: { item_type: 'todo', content: todo.content }
        });
      }
      await this.fetchNotebookDetails();
      wx.showToast({ title: '已保存', icon: 'success' });
    } catch (error) {
      wx.hideLoading();
      wx.showToast({ title: '保存失败', icon: 'none' });
    }
  },

  async onTodoToggle(e) {
    const todoId = e.currentTarget.dataset.id;
    const originalTodos = JSON.parse(JSON.stringify(this.data.todos));
    const index = originalTodos.findIndex(t => t.id === todoId);
    if (index === -1) return;
    const newStatus = !originalTodos[index].is_completed;
    originalTodos[index].is_completed = newStatus;
    this.updateAndSortTodos(originalTodos);
    try {
      await request({ url: `/notes/${todoId}`, method: 'PUT', data: { is_completed: newStatus } });
    } catch (error) {
      this.updateAndSortTodos(this.data.todos);
      wx.showToast({ title: '更新失败', icon: 'none' });
    }
  },

  async onDeleteTodo(e) {
    const todoId = e.currentTarget.dataset.id;
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这个待办事项吗？',
      confirmColor: '#FF4D4F',
      success: async (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '删除中...' });
          try {
            await request({ url: `/notes/${todoId}`, method: 'DELETE' });
            await this.fetchNotebookDetails();
            wx.showToast({ title: '已删除' });
          } catch (error) {
            wx.hideLoading();
            wx.showToast({ title: '删除失败', icon: 'none' });
          }
        }
      }
    });
  },

  // --- 笔记 (Note) 逻辑 ---
  showAddNoteModal() { this.setData({ isEditing: false, currentNote: { id: null, title: '', content: '' }, showNoteModal: true, }); },
  showEditNoteModal(e) {
    const noteId = e.currentTarget.dataset.id;
    const note = this.data.notes.find(n => n.id === noteId);
    if (note) { this.setData({ isEditing: true, currentNote: { ...note }, showNoteModal: true, }); }
  },

  async handleNoteModalConfirm() {
    const note = this.data.currentNote;
    if (!note.title.trim()) { return wx.showToast({ title: '标题不能为空', icon: 'none' }); }
    
    this.hideModals();
    wx.showLoading({ title: '保存中...' });

    try {
      const payload = { title: note.title, content: note.content };
      if (this.data.isEditing) {
        await request({ url: `/notes/${note.id}`, method: 'PUT', data: payload });
      } else {
        // 这个创建逻辑也已经是正确的
        await request({
          url: `/notes/`,
          method: 'POST',
          data: { ...payload, item_type: 'note' }
        });
      }
      await this.fetchNotebookDetails();
      wx.showToast({ title: '已保存', icon: 'success' });
    } catch (err) {
      wx.hideLoading();
      wx.showToast({ title: '保存失败', icon: 'none' });
    }
  },

  onDeleteNote() {
    const noteId = this.data.currentNote.id;
    if (!noteId) return;
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这篇笔记吗？',
      confirmText: '删除',
      confirmColor: '#FF4D4F',
      success: async (res) => {
        if (res.confirm) {
          this.hideModals();
          wx.showLoading({ title: '删除中...' });
          try {
            await request({ url: `/notes/${noteId}`, method: 'DELETE' });
            await this.fetchNotebookDetails();
            wx.showToast({ title: '删除成功' });
          } catch (error) {
            wx.hideLoading();
            wx.showToast({ title: '删除失败', icon: 'none' });
          }
        }
      }
    });
  },
  
  goBack() {
    wx.navigateBack();
  },

  onShareAppMessage: function () {
    return getShareInfo();
  },

  onShareTimeline: function () {
    return getTimelineInfo();
  }
});