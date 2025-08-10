// pages/daily-checkin/note/note.js

// --- Helper Functions ---
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

function debounce(fn, delay) {
  let timer = null;
  return function(...args) {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      fn.apply(this, args);
    }, delay);
  };
}

Page({
  data: {
    navBarHeight: getApp().globalData.navBarHeight,
    notebookId: null,
    notebookName: '',
    todos: [],
    note: { id: null, content: '' },
    lastSavedName: '',
    isTodoCollapsed: false,
    isNoteCollapsed: false,
  },

  onLoad(options) {
    const id = options.id;
    if (id) {
      this.setData({ notebookId: id });
      this.fetchNotebookDetails();
    } else {
      console.error('No notebook ID provided');
      wx.showToast({ title: '加载失败，无效的ID', icon: 'none' });
    }
    // Initialize debounced handlers here to maintain `this` context
    this.handleTodoInput = debounce(this.saveTodoInput, 500);
    this.handleNoteInput = debounce(this.saveNoteInput, 500);
  },

  async fetchNotebookDetails() {
    wx.showLoading({ title: '加载中...' });
    try {
      const notebook = await request({ url: `/notebooks/${this.data.notebookId}` });
      const items = await request({ url: `/notebooks/${this.data.notebookId}/notes/` });

      const todos = items.filter(item => item.item_type === 'todo');
      const note = items.find(item => item.item_type === 'note') || { id: null, content: '' };

      this.setData({
        notebookName: notebook.name,
        lastSavedName: notebook.name,
        todos,
        note
      });
    } catch (error) {
      wx.showToast({ title: '加载笔记失败', icon: 'none' });
    } finally {
      wx.hideLoading();
    }
  },

  // --- Title Logic ---
  onTitleBlur(e) {
    const newName = e.detail.value;
    if (newName !== this.data.lastSavedName) {
      this.updateNotebook({ name: newName });
    }
  },

  async updateNotebook(data) {
    try {
      await request({
        url: `/notebooks/${this.data.notebookId}`,
        method: 'PUT',
        data
      });
      this.setData({ lastSavedName: data.name });
      wx.showToast({ title: '标题已保存', icon: 'success', duration: 1000 });
    } catch (error) {
      wx.showToast({ title: '标题保存失败', icon: 'none' });
    }
  },

  // --- Todo Logic ---
  async onTodoChange(e) {
    const todoId = e.currentTarget.dataset.id;
    const is_completed = e.detail.value.length > 0;
    try {
      await this.updateNoteItem(todoId, { is_completed });
      const index = this.data.todos.findIndex(t => t.id === todoId);
      this.setData({ [`todos[${index}].is_completed`]: is_completed });
    } catch (error) {
      console.error('Failed to update todo status', error);
    }
  },

  saveTodoInput(e) {
    const todoId = e.currentTarget.dataset.id;
    const content = e.detail.value;
    this.updateNoteItem(todoId, { content });
  },

  async onTodoConfirm(e) {
    const content = e.detail.value;
    if (!content) return;
    try {
      await this.createNoteItem({ item_type: 'todo', content });
      this.fetchNotebookDetails();
    } catch (error) {
      wx.showToast({ title: '添加失败', icon: 'none' });
    }
  },

  // --- Note Logic ---
  saveNoteInput(e) {
    const content = e.detail.value;
    const noteId = this.data.note.id;
    if (noteId) {
      this.updateNoteItem(noteId, { content });
    } else {
      this.createNoteItem({ item_type: 'note', content }).then(newNote => {
        this.setData({ 'note.id': newNote.id });
      });
    }
  },

  // --- API Helpers ---
  async updateNoteItem(itemId, data) {
    return request({
      url: `/notes/${itemId}`,
      method: 'PUT',
      data
    });
  },

  async createNoteItem(data) {
    return request({
      url: `/notebooks/${this.data.notebookId}/notes/`,
      method: 'POST',
      data
    });
  },

  // --- Collapse Logic ---
  toggleTodoSection() {
    this.setData({ isTodoCollapsed: !this.data.isTodoCollapsed });
  },

  toggleNoteSection() {
    this.setData({ isNoteCollapsed: !this.data.isNoteCollapsed });
  },

  goBack() {
    wx.navigateBack();
  }
});