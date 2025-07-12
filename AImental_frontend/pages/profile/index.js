// /pages/profile/index.js

// --- 配置 ---
const SERVER_BASE_URL = 'http://127.0.0.1:8000'; 
const API_BASE_URL = `${SERVER_BASE_URL}/api/v1/users`; 

const defaultAvatarUrl = '/images/default-avatar.png';

Page({
  data: {
    isLogin: false,
    userInfo: {
      avatar_url: defaultAvatarUrl,
      nickname: '访客'
    },
  },

  onShow: function () {
    // 每次进入页面都检查登录状态并尝试刷新用户信息
    this.checkLoginStatus();
  },
  
  checkLoginStatus: function() {
    try {
      const token = wx.getStorageSync('token');
      if (token) {
        // **【核心逻辑修正】**
        // 只要有token，就认为用户是登录状态，并立即去服务器获取最新信息。
        // 这样可以确保即使用户在其他设备上修改了信息，这里也能同步。
        this.setData({ isLogin: true });
        this.fetchUserProfile(token);

        // 为了更好的用户体验，可以先用缓存里的旧数据快速显示一下
        const cachedUserInfo = wx.getStorageSync('userInfo');
        if (cachedUserInfo) {
          this.setData({ userInfo: cachedUserInfo });
        }

      } else {
        // 没有token，就是未登录状态
        this.setData({
          isLogin: false,
          userInfo: {
            avatar_url: defaultAvatarUrl,
            nickname: '访客'
          }
        });
      }
    } catch (e) {
      console.error("获取本地缓存失败", e);
    }
  },

  /**
   * 用户点击“点击登录”按钮
   */
  login: function() {
    wx.showLoading({ title: '请授权...' });
    wx.getUserProfile({
      desc: '用于完善您的个人资料',
      success: (profileRes) => {
        wx.showLoading({ title: '正在登录...' });
        wx.login({
          success: loginRes => {
            if (loginRes.code) {
              wx.request({
                url: `${API_BASE_URL}/login`,
                method: 'POST',
                data: {
                  code: loginRes.code,
                  nickname: profileRes.userInfo.nickName,
                  avatar_url: profileRes.userInfo.avatarUrl,
                },
                success: (apiRes) => {
                  wx.hideLoading();
                  if (apiRes.statusCode === 200 && apiRes.data.access_token) {
                    const token = apiRes.data.access_token;
                    wx.setStorageSync('token', token);
                    // 登录成功后，立即获取一次完整的、带服务器地址的用户信息
                    this.fetchUserProfile(token);
                  } else {
                    wx.showToast({ title: apiRes.data.detail || '登录失败', icon: 'none' });
                  }
                },
                fail: (err) => {
                  wx.hideLoading();
                  wx.showToast({ title: '请求登录接口失败', icon: 'none' });
                }
              });
            } else {
              wx.hideLoading();
              wx.showToast({ title: '获取凭证失败', icon: 'none' });
            }
          }
        });
      },
      fail: (err) => {
        wx.hideLoading();
        wx.showToast({ title: '您已取消授权', icon: 'none' });
      }
    });
  },

  /**
   * 使用token从后端获取当前用户的详细信息
   */
  fetchUserProfile: function(token) {
    // 不再显示“加载中”，让刷新在后台静默进行
    wx.request({
      url: `${API_BASE_URL}/me`,
      method: 'GET',
      header: { 'Authorization': `Bearer ${token}` },
      success: (res) => {
        if (res.statusCode === 200) {
          // **【重要】** 每次从后端获取到信息后，都检查并拼接完整的头像URL
          if (res.data.avatar_url && !res.data.avatar_url.startsWith('http')) {
            res.data.avatar_url = SERVER_BASE_URL + res.data.avatar_url;
          }
          // 将最新的、带完整URL的信息存入缓存和页面
          wx.setStorageSync('userInfo', res.data);
          this.setData({
            userInfo: res.data,
            isLogin: true,
          });
        } else {
          // 如果token失效，清理登录状态
          this.clearLoginState();
        }
      },
      fail: (err) => {
        // 网络请求失败时，不做处理，继续用缓存数据
        console.error("fetchUserProfile failed:", err);
      }
    });
  },

  // ... logout, clearLoginState, onChangeAvatar, chooseAndUploadAvatar 等函数保持不变 ...
  // ... goTo... 跳转函数也保持不变 ...

  // (为了完整性，我还是把它们贴在下面)
  logout: function() {
    wx.showModal({
      title: '提示',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '正在退出...' });
          const token = wx.getStorageSync('token');
          if (token) {
            wx.request({
              url: `${API_BASE_URL}/logout`,
              method: 'POST',
              header: { 'Authorization': `Bearer ${token}` },
              complete: () => {
                wx.hideLoading();
                this.clearLoginState();
                wx.showToast({ title: '已退出', icon: 'success' });
              }
            });
          } else {
            this.clearLoginState();
            wx.hideLoading();
          }
        }
      }
    });
  },
  clearLoginState: function() {
    wx.removeStorageSync('token');
    wx.removeStorageSync('userInfo');
    this.setData({
      isLogin: false,
      userInfo: {
        avatar_url: defaultAvatarUrl,
        nickname: '访客'
      }
    });
  },
  onChangeAvatar: function() {
    if (!this.data.isLogin) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    wx.showActionSheet({
      itemList: ['更换头像'],
      success: (res) => {
        if (res.tapIndex === 0) {
          this.chooseAndUploadAvatar();
        }
      },
    });
  },
  chooseAndUploadAvatar: function() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      sizeType: ['compressed'],
      success: (res) => {
        wx.showLoading({ title: '正在上传...' });
        const tempFilePath = res.tempFiles[0].tempFilePath;
        const token = wx.getStorageSync('token');
        wx.uploadFile({
          url: `${API_BASE_URL}/me/avatar`,
          filePath: tempFilePath,
          name: 'image',
          header: { 'Authorization': `Bearer ${token}` },
          success: (uploadRes) => {
            wx.hideLoading();
            const data = JSON.parse(uploadRes.data);
            if (uploadRes.statusCode === 200) {
              wx.showToast({ title: '头像更新成功!', icon: 'success' });
              const fullAvatarUrl = SERVER_BASE_URL + data.new_avatar_url;
              const newUserInfo = { ...this.data.userInfo, avatar_url: fullAvatarUrl };
              this.setData({ userInfo: newUserInfo });
              wx.setStorageSync('userInfo', newUserInfo);
            } else {
              wx.showToast({ title: data.detail || '上传失败', icon: 'none' });
            }
          },
          fail: (err) => {
            wx.hideLoading();
            wx.showToast({ title: '请求上传接口失败', icon: 'none' });
          }
        });
      }
    });
  },
  goToUserInfo: function() { if (!this.data.isLogin) { wx.showToast({ title: '请先登录', icon: 'none' }); return; } wx.navigateTo({ url: '/pages/profile-edit/index' }); },
  goToReports: function() { if (!this.data.isLogin) { wx.showToast({ title: '请先登录', icon: 'none' }); return; } wx.navigateTo({ url: '/pages/reports-list/index' }); },
  goToFeedback: function() { wx.navigateTo({ url: '/pages/feedback/index' }); },
  goToAboutUs: function() { wx.navigateTo({ url: '/pages/about-us/index' }); }
});