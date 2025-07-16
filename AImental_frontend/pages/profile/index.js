// index.js (正确分离的版本)

// --- 配置 ---
const SERVER_BASE_URL = 'http://49.233.220.130:8000'; 
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
    this.checkLoginStatus();
  },
  
  checkLoginStatus: function() {
    try {
      const token = wx.getStorageSync('token');
      if (token) {
        this.setData({ isLogin: true });
        this.fetchUserProfile(token);
        const cachedUserInfo = wx.getStorageSync('userInfo');
        if (cachedUserInfo) {
          this.setData({ userInfo: cachedUserInfo });
        }
      } else {
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

  fetchUserProfile: function(token) {
    wx.request({
      url: `${API_BASE_URL}/me`,
      method: 'GET',
      header: { 'Authorization': `Bearer ${token}` },
      success: (res) => {
        if (res.statusCode === 200) {
          if (res.data.avatar_url && !res.data.avatar_url.startsWith('http')) {
            res.data.avatar_url = SERVER_BASE_URL + res.data.avatar_url;
          }
          wx.setStorageSync('userInfo', res.data);
          this.setData({
            userInfo: res.data,
            isLogin: true,
          });
        } else {
          this.clearLoginState();
        }
      },
      fail: (err) => {
        console.error("fetchUserProfile failed:", err);
      }
    });
  },

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
  
  goToUserInfo: function() { if (!this.data.isLogin) { wx.showToast({ title: '请先登录', icon: 'none' }); return; } wx.navigateTo({ url: '/pages/profile/inform' }); },
  goToFeedback: function() { wx.navigateTo({ url: '/pages/profile/feedback' }); },
  goToReports: function() {
    // 这段登录判断逻辑是正确的，需要保留
    if (!this.data.isLogin) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      });
      return;
    }
    
    // 只需修改这里的 url 指向我们新创建的 history 页面
    wx.navigateTo({
      url: '/pages/profile/history' 
    });
  },

  /**
   * ✅ 点击“关于我们”，跳转到 about 页面
   */
  goToAboutUs: function() {
    wx.navigateTo({
      url: './about' // <-- 确保这个路径是正确的！
    });
  }
});