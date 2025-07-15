// pages/inform/inform.js (终极方案版)

const SERVER_BASE_URL = 'http://127.0.0.1:8000/api/v1';
const API_BASE_URL = `${SERVER_BASE_URL}/users`;

Page({
  data: {
    navTop: 0,
    navHeight: 0,
    avatar_url: '',
    nickname: '',
    genderIndex: 2,
    birthday: '请选择您的生日',
    genderRange: ['男', '女', '保密'],
    isEditingNickname: false,
    currentDate: '',
    _originalData: null
  },

  onLoad(options) {
    this.setNavSize();
    this.setCurrentDate();
    this.fetchUserInfo();
  },

  onHide: function () { if (this.data.isEditingNickname) { this.saveNickname(); } },
  onUnload: function () { if (this.data.isEditingNickname) { this.saveNickname(); } },

  setNavSize() {
    const sysInfo = wx.getSystemInfoSync();
    const menuButtonInfo = wx.getMenuButtonBoundingClientRect();
    this.setData({
      navTop: sysInfo.statusBarHeight,
      navHeight: menuButtonInfo.height + (menuButtonInfo.top - sysInfo.statusBarHeight) * 2
    });
  },

  setCurrentDate() {
    const now = new Date();
    const year = now.getFullYear();
    const month = (now.getMonth() + 1).toString().padStart(2, '0');
    const day = now.getDate().toString().padStart(2, '0');
    this.setData({ currentDate: `${year}-${month}-${day}` });
  },

  navigateBack() { wx.navigateBack({ delta: 1 }); },

  fetchUserInfo() {
    const token = wx.getStorageSync('token');
    if (!token) { return; }
    wx.showLoading({ title: '加载中...' });
    wx.request({
      url: `${API_BASE_URL}/me/info`,
      method: 'GET',
      header: { 'Authorization': `Bearer ${token}` },
      success: (res) => {
        if (res.statusCode === 200) {
          const data = res.data;
          // console.log('【侦探日志】从服务器收到的原始用户信息:', res.data);
          let genderIndex = 2;
          if (data.gender === 1) genderIndex = 0;
          if (data.gender === 2) genderIndex = 1;
          const cachedUserInfo = wx.getStorageSync('userInfo');
          const profile = {
            nickname: data.nickname || '',
            birthday: data.birthday || '请选择您的生日',
            genderIndex: genderIndex,
            avatar_url: cachedUserInfo.avatar_url || ''
          };
          this.setData({ ...profile, _originalData: profile });
        }
      },
      complete: () => { wx.hideLoading(); }
    });
  },

  updateUserInfo(updateData) {
    const token = wx.getStorageSync('token');
    if (!token) { return; }
    wx.request({
      url: `${API_BASE_URL}/me/info`,
      method: 'PUT',
      header: { 'Authorization': `Bearer ${token}` },
      data: updateData,
      success: (res) => {
        if (res.statusCode === 200) {
          wx.showToast({ title: '保存成功', icon: 'success' });
          console.log('保存成功，正在重新拉取最新信息...');
          this.fetchUserInfo();
          const userInfo = wx.getStorageSync('userInfo') || {};
          const newUserInfo = { ...userInfo, ...updateData };
          wx.setStorageSync('userInfo', newUserInfo);
        } else {
          wx.showToast({ title: '保存失败', icon: 'none' });
          this.setData({ ...this.data._originalData });
        }
      },
      fail: () => wx.showToast({ title: '网络错误', icon: 'none' })
    });
  },

  editNickname() { this.setData({ isEditingNickname: true }); },
  onNickNameInput(e) { this.setData({ nickname: e.detail.value }); },

  saveNickname(e) {
    if (!this.data.isEditingNickname) { return; }
    this.setData({ isEditingNickname: false });
    const newNickname = this.data.nickname.trim();
    if (newNickname && newNickname !== this.data._originalData.nickname) {
      this.updateUserInfo({ nickname: newNickname });
    } else {
      this.setData({ nickname: this.data._originalData.nickname });
    }
  },

  bindGenderChange(e) {
    const newIndex = parseInt(e.detail.value);
    if (newIndex === this.data.genderIndex) return;
    this.setData({ genderIndex: newIndex });
    const genderMap = [1, 2, 0]; 
    const backendGender = genderMap[newIndex];
    this.updateUserInfo({ gender: backendGender });
  },

  bindBirthdayChange(e) {
    const newBirthday = e.detail.value;
    if (newBirthday === this.data.birthday) return;
    this.setData({ birthday: newBirthday });
    this.updateUserInfo({ birthday: newBirthday });
  },

  onChangeAvatar: function() {
    wx.showActionSheet({
      itemList: ['更换头像'],
      success: (res) => { if (res.tapIndex === 0) { this.chooseAndUploadAvatar(); } },
    });
  },

  chooseAndUploadAvatar: function() {
    wx.chooseMedia({
      count: 1, mediaType: ['image'], sourceType: ['album', 'camera'], sizeType: ['compressed'],
      success: (res) => {
        wx.showLoading({ title: '正在上传...' });
        const tempFilePath = res.tempFiles[0].tempFilePath;
        const token = wx.getStorageSync('token');
        wx.uploadFile({
          url: `${API_BASE_URL}/me/avatar`,
          filePath: tempFilePath, name: 'image',
          header: { 'Authorization': `Bearer ${token}` },
          success: (uploadRes) => {
            if (uploadRes.statusCode === 200) {
              wx.showToast({ title: '头像更新成功!', icon: 'success' });
              this.fetchUserInfo(); // 头像更新成功后，也调用 fetchUserInfo 刷新所有信息
            }
          },
          complete: () => wx.hideLoading()
        });
      }
    });
  },
});