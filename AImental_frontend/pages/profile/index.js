// index.js (正确分离的版本)

// --- 配置 ---
const SERVER_BASE_URL = 'http://127.0.0.1:8000'; 
const API_BASE_URL = `${SERVER_BASE_URL}/api/v1/users`; 
const VIP_API_BASE_URL = `${SERVER_BASE_URL}/api/v1/vip`;
const defaultAvatarUrl = 'https://assets.feelyourself.cn/miniprogram/assets/v1/images/default-avatar.png';
const MEMBERSHIP_ICON_BY_PLAN = {
  light: 'https://assets.feelyourself.cn/miniprogram/assets/v1/images/vip/member-badge-light.png',
  knowing: 'https://assets.feelyourself.cn/miniprogram/assets/v1/images/vip/member-badge-knowing.png',
  companion: 'https://assets.feelyourself.cn/miniprogram/assets/v1/images/vip/member-badge-companion.png',
  vip_light: 'https://assets.feelyourself.cn/miniprogram/assets/v1/images/vip/member-badge-light.png',
  vip_knowing: 'https://assets.feelyourself.cn/miniprogram/assets/v1/images/vip/member-badge-knowing.png',
  vip_companion: 'https://assets.feelyourself.cn/miniprogram/assets/v1/images/vip/member-badge-companion.png',
};

function getMembershipIcon(planCode) {
  return MEMBERSHIP_ICON_BY_PLAN[planCode] || MEMBERSHIP_ICON_BY_PLAN.knowing;
}

const { getShareInfo, getTimelineInfo } = require('../../utils/share.js');
const { loginWithBackend } = require('../../utils/auth.js');
const { hasCurrentPrivacyConsent } = require('../../utils/privacy.js');
const {
  isDirectUploadUnavailable,
  uploadPrivateImageDirect,
} = require('../../utils/private-media-upload.js');
Page({
  data: {
    isLogin: false,
    isMember: false,
    membership: null,
    membershipAvatarIcon: '',
    vipTestToolsAvailable: false,
    cancelVipLoading: false,
    vipEntryTitle: '成为会员',
    vipEntryDesc: '查看会员套餐与专属权益',
    privacyVisible: false,
    topSafeHeight: 72,
    userInfo: {
      avatar_url: defaultAvatarUrl,
      nickname: '访客'
    },
  },

  onLoad: function () {
    this.initLayoutMetrics();
  },

  onShow: function () {
    this.checkLoginStatus();
  },

  initLayoutMetrics: function() {
    const fallback = { statusBarHeight: 24 };
    let systemInfo = fallback;
    try {
      systemInfo = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
    } catch (e) {
      systemInfo = fallback;
    }
    const statusBarHeight = systemInfo.statusBarHeight || fallback.statusBarHeight;
    this.setData({
      topSafeHeight: statusBarHeight + 36,
    });
  },
  
  checkLoginStatus: function() {
    try {
      const token = wx.getStorageSync('token');
      if (token) {
        this.setData({ isLogin: true });
        this.fetchUserProfile(token);
        this.fetchVipState(token);
        const cachedUserInfo = wx.getStorageSync('userInfo');
        if (cachedUserInfo) {
          this.setData({ userInfo: cachedUserInfo });
        }
      } else {
        this.setData({
          isLogin: false,
          isMember: false,
          membership: null,
          membershipAvatarIcon: '',
          vipTestToolsAvailable: false,
          cancelVipLoading: false,
          vipEntryTitle: '成为会员',
          vipEntryDesc: '查看会员套餐与专属权益',
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
    if (!hasCurrentPrivacyConsent()) {
      this.setData({ privacyVisible: true });
      return;
    }
    this.performLogin();
  },

  performLogin: function() {
    wx.showLoading({ title: '登录中...' });
    loginWithBackend(SERVER_BASE_URL + '/api/v1')
      .then((apiRes) => {
        wx.hideLoading();
        if (apiRes.access_token) {
          const token = apiRes.access_token;
          wx.setStorageSync('token', token);
          this.fetchUserProfile(token);
          wx.showToast({ title: '登录成功', icon: 'success' });
        } else {
          console.error('登录 API 返回异常:', apiRes);
          wx.showToast({ title: apiRes.detail || '登录失败', icon: 'none' });
        }
      })
      .catch((err) => {
        wx.hideLoading();
        console.error('登录请求失败:', err);
        wx.showToast({ title: '登录失败，请重试', icon: 'none' });
      });
  },

  onPrivacyConfirm: function() {
    this.setData({ privacyVisible: false });
    this.performLogin();
  },

  onPrivacyReject: function() {
    this.setData({ privacyVisible: false });
    wx.showToast({
      title: '同意隐私协议后才能登录',
      icon: 'none'
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

  fetchVipState: function(token) {
    wx.request({
      url: `${VIP_API_BASE_URL}/me`,
      method: 'GET',
      header: { 'Authorization': `Bearer ${token}` },
      success: (res) => {
        if (res.statusCode !== 200) {
          return;
        }
        const membership = res.data && res.data.membership;
        const isMember = Boolean(
          res.data
          && res.data.user_type === 'member'
          && membership
          && membership.status === 'active'
        );
        this.setData({
          isMember,
          membership: isMember ? membership : null,
          membershipAvatarIcon: isMember ? getMembershipIcon(membership.plan_code) : '',
          vipTestToolsAvailable: Boolean(res.data && res.data.test_tools_available),
          vipEntryTitle: isMember ? '会员权益' : '成为会员',
          vipEntryDesc: isMember
            ? `${membership.plan_name || '当前会员'} · 查看当前额度`
            : '查看会员套餐与专属权益',
        });
      },
      fail: (err) => {
        console.error('fetchVipState failed:', err);
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
      isMember: false,
      membership: null,
      membershipAvatarIcon: '',
      vipTestToolsAvailable: false,
      cancelVipLoading: false,
      vipEntryTitle: '成为会员',
      vipEntryDesc: '查看会员套餐与专属权益',
      userInfo: {
        avatar_url: defaultAvatarUrl,
        nickname: '访客'
      }
    });
  },

  onChangeAvatar: function() {
    if (!this.data.isLogin) {
      wx.showToast({ title: '请先登录才能换头像哦~', icon: 'none' });
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
        this.uploadAvatarFile({
          url: `${API_BASE_URL}/me/avatar`,
          filePath: tempFilePath,
          name: 'image',
          header: { 'Authorization': `Bearer ${token}` },
          success: (uploadRes) => {
            wx.hideLoading();
            const data = JSON.parse(uploadRes.data);
            if (uploadRes.statusCode === 200) {
              wx.showToast({ title: '头像更新成功!', icon: 'success' });
              const fullAvatarUrl = data.new_avatar_url.startsWith('http')
                ? data.new_avatar_url
                : SERVER_BASE_URL + data.new_avatar_url;
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

  uploadAvatarFile: function(options) {
    const token = wx.getStorageSync('token');
    uploadPrivateImageDirect({
      apiBaseUrl: SERVER_BASE_URL,
      token,
      mediaType: 'avatar',
      filePath: options.filePath,
      bindUrl: `${API_BASE_URL}/me/avatar/direct`,
      bindMethod: 'PUT',
    })
      .then((data) => {
        options.success({
          statusCode: 200,
          data: JSON.stringify(data),
        });
      })
      .catch((error) => {
        if (isDirectUploadUnavailable(error)) {
          wx.uploadFile(options);
          return;
        }
        options.fail(error);
      });
  },
  
  goToVip: function() {
    wx.navigateTo({
      url: '/pkgProfile/vip/index'
    });
  },

  cancelVipForTesting: function() {
    if (this.data.cancelVipLoading) {
      return;
    }
    const token = wx.getStorageSync('token');
    if (!token) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    wx.showModal({
      title: '临时测试按钮',
      content: '确认把当前账号重置为非会员吗？会员额度也会从当前状态里移除。',
      confirmText: '确认取消',
      cancelText: '再想想',
      success: (modalRes) => {
        if (!modalRes.confirm) {
          return;
        }
        this.setData({ cancelVipLoading: true });
        wx.request({
          url: `${VIP_API_BASE_URL}/me/test-cancel-membership`,
          method: 'POST',
          header: { 'Authorization': `Bearer ${token}` },
          success: (res) => {
            if (res.statusCode !== 200) {
              const detail = res.data && res.data.detail;
              const message = typeof detail === 'string'
                ? detail
                : (detail && detail.message) || '取消会员测试失败';
              wx.showToast({ title: message, icon: 'none' });
              return;
            }
            wx.showToast({ title: '已重置为非会员', icon: 'success' });
            this.fetchVipState(token);
          },
          fail: () => {
            wx.showToast({ title: '请求失败，请稍后重试', icon: 'none' });
          },
          complete: () => {
            this.setData({ cancelVipLoading: false });
          },
        });
      },
    });
  },

  goToUserInfo: function() { if (!this.data.isLogin) { wx.showToast({ title: '请先登录才能查看个人信息哦~', icon: 'none' }); return; } wx.navigateTo({ url: '/pkgProfile/inform' }); },
  goToFeedback: function() {
    // --- 核心改动：在这里添加登录判断 ---
    if (!this.data.isLogin) {
      wx.showToast({
        title: '请先登录才能反馈哦~', // 提示用户需要登录
        icon: 'none'
      });
      return; // 终止函数，不进行跳转
    }
    // ------------------------------------
  
    // 如果代码能执行到这里，说明用户已登录
    wx.navigateTo({ 
      url: '/pkgProfile/feedback' 
    });
  },
  goToReports: function() {
    // 这段登录判断逻辑是正确的，需要保留
    if (!this.data.isLogin) {
      wx.showToast({
        title: '请先登录才能查看测试历史哦~',
        icon: 'none'
      });
      return;
    }
    
    // 只需修改这里的 url 指向我们新创建的 history 页面
    wx.navigateTo({
      url: '/pkgProfile/history' 
    });
  },

  goToPrivacy: function() {
    wx.navigateTo({
      url: '/pkgProfile/privacy'
    });
  },

  /**
   * ✅ 点击“关于我们”，跳转到 about 页面
   */
  goToAboutUs: function() {
    wx.navigateTo({
      url: '/pkgProfile/about' // <-- 确保这个路径是正确的！
    });
  },

  onShareAppMessage: function () {
    return getShareInfo();
  },

  onShareTimeline: function () {
    return getTimelineInfo();
  }
});
