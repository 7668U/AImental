// note.js (The final, correct version)

// --- 辅助函数 ---
function request(options) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token');
    wx.request({
      ...options,
      url: `http://127.0.0.1:8000/api/v1${options.url}`,
      header: { ...options.header, 'Authorization': `Bearer ${token}` },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) { resolve(res.data); }
        else {
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


Page({
  data: {
    navBarHeight: getApp().globalData.navBarHeight,
    notebookId: null,
    notebookName: '',
    todos: [],
    notes: [],
    uncompletedTodoCount: 0,
    isEditing: false,
    showTodoModal: false,
    currentTodo: { id: null, content: '' },
    showNoteModal: false,
    currentNote: { id: null, title: '', content: '' },
  },

  onLoad(options) {
    const id = options.id || options.scene;
    if (id) {
      this.setData({ notebookId: id });
      this.fetchNotebookDetails();
    } else {
      wx.showToast({ title: '无效的笔记本ID', icon: 'none' });
    }
  },
  
  onUnload() {
    // 这是一个安全措施，确保在离开此页面时，
    // 任何可能残留的 wx.showLoading 都会被强制关闭，
    // 防止它影响到其他页面。
    wx.hideLoading();
  },

  async fetchNotebookDetails() {
    wx.showLoading({ title: '加载中...' });
    try {
      const [notebookData, items] = await Promise.all([
        request({ url: `/notebooks/${this.data.notebookId}` }),
        request({ url: `/notebooks/${this.data.notebookId}/notes/` })
      ]);
      const todos = items.filter(item => item.item_type === 'todo');
      const notes = items.filter(item => item.item_type === 'note');
      this.setData({
        notebookName: notebookData.name,
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
      if (field === 'title') {
        this.setData({ 'currentNote.title': value });
      } else if (field === 'noteContent') {
        this.setData({ 'currentNote.content': value });
      }
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
        await request({ url: `/notebooks/${this.data.notebookId}/notes/`, method: 'POST', data: { item_type: 'todo', content: todo.content } });
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

  async handleNoteModalConfirm() {
    const note = this.data.currentNote;
    if (!note.title.trim()) { return wx.showToast({ title: '标题不能为空', icon: 'none' }); }
    this.hideModals();
    wx.showLoading({ title: '保存中...' });
    try {
      const payload = {
        title: note.title,
        content: note.content
      };
      if (this.data.isEditing) {
        await request({ url: `/notes/${note.id}`, method: 'PUT', data: payload });
      } else {
        await request({ url: `/notebooks/${this.data.notebookId}/notes/`, method: 'POST', data: { ...payload, item_type: 'note' } });
      }
      await this.fetchNotebookDetails();
      wx.showToast({ title: '已保存', icon: 'success' });
    } catch (err) {
      wx.hideLoading();
      wx.showToast({ title: '保存失败', icon: 'none' });
    }
  },
  
  goBack() {
    wx.navigateBack();
  }
});