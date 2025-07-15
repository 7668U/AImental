// pages/inform/inform.js
const app = getApp();

Page({
  data: {
    // 自定义导航栏相关数据
    navTop: 0,
    navHeight: 0,
    // 用户信息
    nickName: 'AImental', // 初始昵称，实际应从服务器获取
    isEditingNickname: false, // 控制是否处于昵称编辑状态
    genderRange: ['男', '女', '保密'],
    genderIndex: 0,
    birthday: '请选择您的生日',
    currentDate: ''
  },

  onLoad(options) {
    this.setNavSize();
    this.setCurrentDate();
    // 假设从缓存或服务器获取了用户昵称
    // wx.getStorage({
    //   key: 'userInfo',
    //   success: (res) => {
    //     this.setData({ nickName: res.data.nickName });
    //   }
    // });
  },

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
    this.setData({
      currentDate: `${year}-${month}-${day}`
    });
  },

  navigateBack() {
    wx.navigateBack({
      delta: 1
    });
  },

  // --- 昵称修改相关函数 ---
  editNickname() {
    this.setData({
      isEditingNickname: true
    });
  },

  onNickNameInput(e) {
    this.setData({
      nickName: e.detail.value
    });
  },

  saveNickname() {
    this.setData({
      isEditingNickname: false
    });
    // 在这里添加将新昵称保存到服务器或本地缓存的逻辑
    console.log('保存新昵称:', this.data.nickName);
    wx.showToast({
      title: '昵称已保存',
      icon: 'success'
    });
  },
  // -------------------------

  bindGenderChange: function(e) {
    this.setData({
      genderIndex: e.detail.value
    });
    console.log('保存性别:', this.data.genderRange[e.detail.value]);
  },

  bindBirthdayChange: function(e) {
    this.setData({
      birthday: e.detail.value
    });
    console.log('保存生日:', e.detail.value);
  },
});