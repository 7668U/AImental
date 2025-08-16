// pages/daily-checkin/record.js
const { getShareInfo, getTimelineInfo } = require('../../utils/share.js');
Page({
  /**
   * 页面的初始数据
   */
  data: {
    // 1. 心情数据
    moods: [
      { name: '开心', icon: 'happy', selected: false },
      { name: '平静', icon: 'calm', selected: false },
      { name: '难过', icon: 'sad', selected: false },
      { name: '生气', icon: 'angry', selected: false },
      { name: '放松', icon: 'relaxed', selected: false },
      { name: '迷茫', icon: 'confused', selected: false },
      { name: '尴尬', icon: 'embarass', selected: false },
      { name: '疲惫', icon: 'tired', selected: false },
      { name: '兴奋', icon: 'excited', selected: false },
    ],
    // 2. 状态数据 (标签) - 支持多选
    statuses: [
      { name: '工作', icon: 'work', selected: false },
      { name: '学习', icon: 'study', selected: false },
      { name: '美食', icon: 'food', selected: false },
      { name: '生病', icon: 'health', selected: false },
      { name: '远足', icon: 'outdoor', selected: false },
      { name: '娱乐', icon: 'game', selected: false },
      { name: '躺平', icon: 'sleep', selected: false },
      { name: '运动', icon: 'sports', selected: false },
    ],
    // 3. 颜色数据
    colors: [
      { value: '#FFC107', name: '暖阳橙', selected: false },
      { value: '#81D4FA', name: '晴空蓝', selected: false },
      { value: '#A5D6A7', name: '薄荷绿', selected: false },
      { value: '#B0BEC5', name: '静谧灰', selected: false },
      { value: '#F48FB1', name: '樱花粉', selected: false },
      { value: '#C5CAE9', name: '香芋紫', selected: false },
      { value: '#FF8A80', name: '珊瑚红', selected: false },
      { value: '#FFF59D', name: '柠檬黄', selected: false },
      { value: '#80CBC4', name: '湖水青', selected: false },
      { value: '#7986CB', name: '深海蓝', selected: false },
      { value: '#BCAAA4', name: '奶咖棕', selected: false },
      { value: '#F5F5F5', name: '云朵白', selected: false },
    ],
    // 4. 用户输入数据
    textContent: "",
    imageUrl: "", // 用于显示的URL（可能是本地或远程）
    tempFilePath: "", // 仅用于记录用户新选择的本地图片路径
    
    // 5. 模式相关状态
    isEditMode: false,  // 是否是加载了已有数据的模式 (包括可编辑的今天和只读的过去)
    isLocked: false,    // 页面是否锁定为只读 (当查看过去记录时为 true)
    checkinId: null,
    pageDate: null,     // 记录当前页面的日期
  },

  /**
   * 【重构】生命周期函数--监听页面加载
   */
  onLoad(options) {
    if (options.mode === 'edit' || options.mode === 'view') {
      // --- 编辑或查看模式 ---
      // 从日历查看时，会传入 date；从首页编辑今日时，date 为空
      const dateStr = options.date || this.getTodayString(); 
      this.setData({ 
        isEditMode: true,
        pageDate: dateStr 
      });
      this.loadCheckinData(dateStr); // 使用新的通用函数加载指定日期的数据
    } else {
      // --- 新建模式 ---
      this.setData({ 
        isEditMode: false,
        isLocked: false,
        pageDate: this.getTodayString()
      });
      wx.setNavigationBarTitle({ title: '记录今日心情' });
    }
  },

  /**
   * 【新增】通用函数：获取指定日期的记录并填充表单
   * @param {string} dateStr - 'YYYY-MM-DD' 格式的日期字符串
   */
  loadCheckinData(dateToFetch) {
    // 1. 判断是否为今天，以决定是否锁定页面
    const isToday = dateToFetch === this.getTodayString();

    if (!isToday) {
      this.setData({ isLocked: true });
      wx.setNavigationBarTitle({ title: '查看历史心情' });
    } else {
      this.setData({ isLocked: false });
      wx.setNavigationBarTitle({ title: '修改今日心情' });
    }

    // 2. 发起网络请求获取数据
    const token = wx.getStorageSync('token');
    if (!token) return;

    wx.showLoading({ title: '加载中...' });
    wx.request({
      url: `http://127.0.0.1:8000/api/v1/checkin/date/${dateToFetch}`,
      method: 'GET',
      header: { 'Authorization': `Bearer ${token}` },
      success: (res) => {
        if (res.statusCode === 200) {
          const checkinData = res.data;
          this.setData({ checkinId: checkinData.id });
          this.populateForm(checkinData);
        } else {
          wx.showToast({ title: '加载记录失败', icon: 'none' });
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
  
  /**
   * 【修正并增强】填充表单的辅助函数
   */
  populateForm(data) {
    let newMoods = JSON.parse(JSON.stringify(this.data.moods));
    let moodIndex = newMoods.findIndex(item => item.name === data.mood);
    if (moodIndex > -1) {
      newMoods.forEach(item => item.selected = false);
      newMoods[moodIndex].selected = true;
    }
    
    let newStatuses = JSON.parse(JSON.stringify(this.data.statuses));
    const selectedTags = data.tags ? data.tags.split(',') : [];
    newStatuses.forEach(item => {
      item.selected = selectedTags.includes(item.name);
    });

    let newColors = JSON.parse(JSON.stringify(this.data.colors));
    let colorIndex = newColors.findIndex(item => item.value === data.color);
    if (colorIndex > -1) {
      newColors.forEach(item => item.selected = false);
      newColors[colorIndex].selected = true;
    }
    
    this.setData({
      moods: newMoods,
      statuses: newStatuses,
      colors: newColors,
      textContent: data.text_content || '',
      imageUrl: data.image_url ? `http://127.0.0.1:8000${data.image_url}` : '',
    });
  },
  
  /**
   * 【修改】处理选择事件，增加锁定判断和多选逻辑
   */
  handleSelect(e) {
    if (this.data.isLocked) return;
    const { type, index } = e.currentTarget.dataset;
    let list = this.data[type];

    if (type === 'statuses') {
      list[index].selected = !list[index].selected;
    } else {
      if (list[index].selected) return;
      list.forEach(item => item.selected = false);
      list[index].selected = true;
    }
    this.setData({ [type]: list });
  },

  onTextInput(e) {
    if (this.data.isLocked) return;
    this.setData({ textContent: e.detail.value });
  },

  chooseImage() {
    if (this.data.isLocked) return;
    const isServerImage = this.data.imageUrl && !this.data.tempFilePath;
    const itemList = isServerImage 
      ? ['更换图片', '预览图片', '删除图片']
      : ['更换图片', '删除图片'];

    wx.showActionSheet({
      itemList: itemList,
      success: (res) => {
        const tapIndex = res.tapIndex;
        if (isServerImage) {
          if (tapIndex === 0) this.selectNewImage();
          if (tapIndex === 1) wx.previewImage({ urls: [this.data.imageUrl] });
          if (tapIndex === 2) this.setData({ imageUrl: '', tempFilePath: '' });
        } else {
          if (tapIndex === 0) this.selectNewImage();
          if (tapIndex === 1) this.setData({ imageUrl: '', tempFilePath: '' });
        }
      }
    });
  },

  selectNewImage() {
    wx.chooseMedia({
      count: 1, mediaType: ['image'], sourceType: ['album', 'camera'],
      success: (res) => {
        const tempPath = res.tempFiles[0].tempFilePath;
        this.setData({ imageUrl: tempPath, tempFilePath: tempPath });
      }
    });
  },

  /**
   * 【修正并增强】提交函数
   */
  submitCheckin() {
    if (this.data.isLocked) {
      wx.showToast({ title: '不能修改历史记录哦', icon: 'none' });
      return;
    }

    const selectedMood = this.data.moods.find(item => item.selected);
    const selectedStatuses = this.data.statuses.filter(item => item.selected);
    const selectedColor = this.data.colors.find(item => item.selected);

    if (!selectedMood || selectedStatuses.length === 0 || !selectedColor) {
      wx.showToast({ title: '请完成所有选择', icon: 'none' });
      return;
    }
    const token = wx.getStorageSync('token');
    if (!token) return;

    const textData = {
      mood: selectedMood.name,
      tags: selectedStatuses.map(item => item.name).join(','),
      color: selectedColor.value,
      text_content: this.data.textContent,
    };

    wx.showLoading({ title: '正在处理...' });
    
    if (this.data.isEditMode) {
      this.updateCheckinRecord(textData);
    } else {
      this.createCheckinRecord(textData);
    }
  },

  /**
   * 辅助函数：创建新记录
   */
  createCheckinRecord(data) {
    this.sendRequest({
      url: 'http://127.0.0.1:8000/api/v1/checkin/',
      method: 'POST',
      data: data,
      successCallback: (res) => {
        const checkinId = res.data.id;
        if (this.data.tempFilePath) {
          this.uploadImageForCheckin(checkinId, this.data.tempFilePath, "心情已封存");
        } else {
          this.handleSubmitSuccess("心情已封存");
        }
      },
      failTitle: '提交失败'
    });
  },

  /**
   * 辅助函数：更新现有记录
   */
  updateCheckinRecord(data) {
    this.sendRequest({
      url: `http://127.0.0.1:8000/api/v1/checkin/${this.data.checkinId}`,
      method: 'PUT',
      data: data,
      successCallback: (res) => {
        if (this.data.tempFilePath) {
          this.uploadImageForCheckin(this.data.checkinId, this.data.tempFilePath, "修改成功");
        } else {
          this.handleSubmitSuccess("修改成功");
        }
      },
      failTitle: '修改失败'
    });
  },
  
  /**
   * 辅助函数：上传图片
   */
  uploadImageForCheckin(checkinId, filePath, successTitle) {
    const token = wx.getStorageSync('token');
    wx.uploadFile({
      url: `http://127.0.0.1:8000/api/v1/checkin/${checkinId}/image`,
      filePath: filePath, name: 'image', header: { 'Authorization': `Bearer ${token}` },
      success: (res) => {
        if (res.statusCode === 200) {
          this.handleSubmitSuccess(successTitle);
        } else {
          this.handleApiError(res, '图片上传失败');
        }
      },
      fail: () => this.handleSubmitFail('图片上传失败')
    });
  },

  /**
   * 辅助函数：通用请求封装
   */
  sendRequest({url, method, data, successCallback, failTitle}) {
    const token = wx.getStorageSync('token');
    wx.request({
      url, method, data,
      header: { 'Authorization': `Bearer ${token}` },
      success: (res) => {
        if (res.statusCode === 200 || res.statusCode === 201) {
          successCallback(res);
        } else {
          this.handleApiError(res, failTitle);
        }
      },
      fail: () => this.handleSubmitFail('网络请求失败')
    });
  },
  
  /**
   * 辅助函数：通用成功处理
   */
  handleSubmitSuccess(title) {
    wx.hideLoading();
    wx.showToast({ title: title, icon: 'success' });
    setTimeout(() => { wx.navigateBack(); }, 1500);
  },

  /**
   * 辅助函数：通用失败处理
   */
  handleSubmitFail(title) {
    wx.hideLoading();
    wx.showToast({ title: title, icon: 'none' });
  },

  /**
   * 辅助函数：处理API返回的错误信息
   */
  handleApiError(res, defaultTitle) {
    try {
      const responseData = JSON.parse(res.data);
      this.handleSubmitFail(responseData.detail || defaultTitle);
    } catch(e) {
      this.handleSubmitFail(defaultTitle);
    }
  },

  /**
   * 辅助函数：获取 'YYYY-MM-DD' 格式的当天日期
   */
  getTodayString() {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  },

  onShareAppMessage: function () {
    return getShareInfo();
  },

  onShareTimeline: function () {
    return getTimelineInfo();
  }
});