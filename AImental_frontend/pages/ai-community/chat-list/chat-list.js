// pages/ai-community/chat-list/chat-list.js

const SERVER_URL = 'https://api.feelyourself.cn';
const COMMUNITY_GUIDE_VERSION = 'v2';
const COMMUNITY_GUIDE_ICON = 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/images/community-redesign/chat-bg-pixel-cabin.png';
const app = getApp();

// --- 统一网络请求函数 ---
function request(options) {
  // 定义不同模块的基础URL
  const BASE_URLS = {
    user: `${SERVER_URL}/api/v1`,
    community: `${SERVER_URL}/api/v1/community`
  };
  // 默认使用 community 接口
  const finalBaseUrl = BASE_URLS[options.apiType] || BASE_URLS.community;

  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token');
    const header = { ...options.header };
    if (token) {
      header.Authorization = `Bearer ${token}`;
    }

    wx.request({
      ...options,
      url: `${finalBaseUrl}${options.url}`, // 根据 apiType 拼接 URL
      header,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else if (handlePrivacyConsentRequiredResponse(getCurrentPages().pop(), res)) {
          reject(res);
        } else if (res.statusCode === 401 && options.requiresAuth !== false) {
          // Token失效，获取当前页面实例并调用清理函数
          const currentPage = getCurrentPages().pop();
          if (currentPage && typeof currentPage.clearLoginState === 'function') {
            currentPage.clearLoginState();
          }
          reject(res);
        } else {
          reject(res);
        }
      },
      fail(err) {
        reject(err);
      }
    });
  });
}

const { getShareInfo, getTimelineInfo } = require('../../../utils/share.js');
const {
  confirmPrivacyAwareLogin,
  handlePrivacyConsentRequiredResponse,
  loginWithBackend,
  rejectPrivacyAwareLogin,
  requestPrivacyAwareLogin
} = require('../../../utils/auth.js');
Page({
  data: {
    serverUrl: SERVER_URL,
    chatList: [],
    isLoading: false,
    isRefreshing: false,
    statusBarHeight: 0,
    navBarHeight: 0,
    totalHeaderHeight: 0,
    isLoggedIn: false,
    isError: false,
    unreadCount: 0,
    communityActivityText: '正在等伙伴们来到这里',
    skeletonItems: [1, 2, 3],
    privacyVisible: false,
    showCommunityGuide: false,
    communityGuideIcon: COMMUNITY_GUIDE_ICON
  },

  onLoad: function (options) {
    this.setData({
      // statusBarHeight 不变
      statusBarHeight: app.globalData.statusBarHeight || 20,
      
      // 【修改】让本页面使用“紧凑版”的高度
      navBarHeight: app.globalData.compactNavBarHeight || 44, 
      totalHeaderHeight: app.globalData.compactTotalNavBarHeight || 64
    });
  },

  onShow: function () {
    // 每次进入页面都检查登录状态
    this.checkLoginStatus();
  },

  // --- 核心登录检查逻辑 ---
  checkLoginStatus() {
    const token = wx.getStorageSync('token');
    if (token) {
      // 如果有 token，设置为已登录状态并获取数据
      if (!this.data.isLoggedIn) { // 避免重复setData
          this.setData({ isLoggedIn: true });
      }
      this.getChatList();
      this.showCommunityGuideIfNeeded();
    } else {
      this.setData({ 
        isLoggedIn: false,
        unreadCount: 0,
        isRefreshing: false,
        communityActivityText: '正在认识这里的伙伴'
      });
      this.getGuestCharacters();
      this.showCommunityGuideIfNeeded();
    }
  },

  getCommunityGuideStorageKey() {
    const userInfo = wx.getStorageSync('userInfo') || {};
    const userKey = userInfo.id || userInfo.user_id || userInfo.openid || 'default';
    return `community_guide_seen_${COMMUNITY_GUIDE_VERSION}_${userKey}`;
  },

  showCommunityGuideIfNeeded() {
    const storageKey = this.getCommunityGuideStorageKey();
    if (wx.getStorageSync(storageKey) || this._communityGuideVisible) return;

    this._communityGuideVisible = true;
    setTimeout(() => {
      this.setData({ showCommunityGuide: true });
    }, 260);
  },

  handleConfirmCommunityGuide() {
    const storageKey = this.getCommunityGuideStorageKey();
    wx.setStorageSync(storageKey, true);
    this._communityGuideVisible = false;
    this.setData({ showCommunityGuide: false });
  },

  preventCommunityGuideClose() {},

  // --- 清理登录状态的函数，用于被 request 或其他页面逻辑调用 ---
  clearLoginState() {
    wx.removeStorageSync('token');
    wx.removeStorageSync('userInfo');
    this.setData({
      isLoggedIn: false,
      unreadCount: 0,
      isRefreshing: false,
      communityActivityText: '正在认识这里的伙伴'
    });
    this.getGuestCharacters();
    wx.showToast({ title: '登录已失效', icon: 'none' });
  },

  promptLogin(content = '登录后可以继续使用这个功能。') {
    wx.showModal({
      title: '登录后继续',
      content,
      confirmText: '去登录',
      cancelText: '先逛逛',
      confirmColor: '#ff6b16',
      success: (res) => {
        if (res.confirm) {
          this.handleLogin();
        }
      }
    });
  },

  handleLogin() {
    return requestPrivacyAwareLogin(this, this.performLogin);
  },

  async performLogin() {
    wx.showLoading({ title: '登录中...' });
    try {
      const tokenRes = await loginWithBackend(SERVER_URL + '/api/v1');
      if (tokenRes.access_token) {
        wx.setStorageSync('token', tokenRes.access_token);
        wx.hideLoading();
        wx.showToast({ title: '登录成功', icon: 'success' });
        this.setData({ isLoggedIn: true });
        await this.getChatList();
        this.showCommunityGuideIfNeeded();

        if (this._pendingChatCharacter) {
          const pendingCharacter = this._pendingChatCharacter;
          this._pendingChatCharacter = null;
          this.openChat(pendingCharacter);
        }
      } else {
        throw new Error('登录接口未返回 token');
      }
    } catch (error) {
      wx.hideLoading();
      wx.showToast({ title: '登录失败，请重试', icon: 'none' });
      console.error('登录失败: ' , error);
    }
  },

  onPrivacyConfirm() {
    return confirmPrivacyAwareLogin(this);
  },

  onPrivacyReject() {
    rejectPrivacyAwareLogin(this);
  },

  async getGuestCharacters() {
    if (this.data.isLoading) {
      this.setData({ isRefreshing: false });
      wx.stopPullDownRefresh();
      return;
    }

    this.setData({ isLoading: true, isError: false });
    try {
      const data = await request({
        url: '/characters',
        apiType: 'community',
        requiresAuth: false
      });

      const guestList = (data || []).map((item) => {
        const profile = item.profile || {};
        const identity = profile.identity_core || {};
        const traits = profile.personality_traits || {};
        const avatarUrl = item.avatar_url || 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/images/default-avatar.png';

        return {
          id: item.id,
          name: item.name,
          avatar: avatarUrl.startsWith('http') ? avatarUrl : SERVER_URL + avatarUrl,
          lastMessage: traits.philosophy || identity.occupation || '先看看资料，认识一下这位伙伴',
          unread: false,
          time: '游客可浏览',
          affinityStage: '初次见面',
          affinityTone: 'new',
          affinityScoreText: '0',
          affinityProgress: 4,
          presenceLabel: '在线',
          presenceTone: 'status'
        };
      });

      this.setData({
        chatList: guestList,
        communityActivityText: guestList.length
          ? `${guestList.length} 位伙伴正在这里生活`
          : '正在等伙伴们来到这里',
        isError: false
      });
    } catch (error) {
      console.error('加载游客角色列表失败:', error);
      this.setData({ isError: true, chatList: [] });
    } finally {
      this.setData({ isLoading: false, isRefreshing: false });
      wx.stopPullDownRefresh();
    }
  },

  // --- 使用新的 request 函数获取聊天列表 ---
  async getChatList() {
    if (this.data.isLoading) {
      this.setData({ isRefreshing: false });
      wx.stopPullDownRefresh();
      return;
    }
    this.setData({ isLoading: true, isError: false });
    wx.showNavigationBarLoading(); // 保留加载动画

    try {
      const data = await request({ 
        url: '/chats',
        apiType: 'community' // 指定使用社区接口的URL前缀
      });

      const formattedList = (data || []).map(item => {
        const affinityDisplay = this.buildAffinityDisplay(item.favorability);
        const avatarUrl = item.character_avatar_url || 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/images/default-avatar.png';

        return {
          id: item.character_id,
          name: item.character_name,
          avatar: avatarUrl.startsWith('http') ? avatarUrl : SERVER_URL + avatarUrl,
          lastMessage: item.last_message_snippet || '从一句你好开始认识彼此',
          unread: Boolean(item.unread),
          time: this.formatTimestamp(item.last_message_timestamp),
          ...affinityDisplay,
          presenceLabel: item.current_status || '在线',
          presenceTone: 'status'
        };
      });
      const unreadCount = formattedList.filter(item => item.unread).length;

      this.setData({ 
        chatList: formattedList,
        unreadCount,
        communityActivityText: this.buildCommunityActivityText(formattedList.length, unreadCount),
        isError: false
      });

    } catch (error) {
      console.error("加载列表失败:", error);
      // 如果不是401（已在request中处理），则显示通用错误
      if (!error || error.statusCode !== 401) {
        this.setData({ isError: true });
      }
    } finally {
      this.setData({ isLoading: false, isRefreshing: false });
      wx.hideNavigationBarLoading();
      wx.stopPullDownRefresh();
    }
  },

  onPullDownRefresh: function() {
    this.setData({ isRefreshing: true });
    if (this.data.isLoggedIn) {
      this.getChatList();
    } else {
      this.getGuestCharacters();
    }
  },

  retryGetChatList: function() {
    if (this.data.isLoggedIn) {
      this.getChatList();
    } else {
      this.getGuestCharacters();
    }
  },

  buildAffinityDisplay: function(value) {
    const rawScore = Number(value || 0);
    const score = Math.max(0, Math.min(100, Number.isFinite(rawScore) ? rawScore : 0));
    let stage = '初识观察';
    let tone = 'new';

    if (score >= 80) {
      stage = '高度亲近';
      tone = 'close';
    } else if (score >= 60) {
      stage = '亲近信任';
      tone = 'trusted';
    } else if (score >= 40) {
      stage = '稳定熟悉';
      tone = 'familiar';
    } else if (score >= 20) {
      stage = '开始熟悉';
      tone = 'warming';
    }

    return {
      affinityStage: stage,
      affinityTone: tone,
      affinityScoreText: String(Math.round(score)),
      affinityProgress: Math.max(4, Math.round(score))
    };
  },

  buildCommunityActivityText: function(characterCount, unreadCount) {
    if (unreadCount > 0) {
      return `${unreadCount} 位伙伴刚刚留下了新消息`;
    }
    if (characterCount > 0) {
      return `${characterCount} 位伙伴正在这里生活`;
    }
    return '正在等伙伴们来到这里';
  },
  navigateToChat: function(e) {
    const ai = e.currentTarget.dataset.ai;
    if (!this.data.isLoggedIn) {
      this._pendingChatCharacter = ai;
      this.promptLogin(`登录后可以进入与${ai.name}的会话，并保存你们的关系进度。`);
      return;
    }

    this.openChat(ai);
  },

  openChat: function(ai) {
    wx.navigateTo({ url: `/pkgCommunity/chat-interface/chat-interface?aiId=${ai.id}&name=${encodeURIComponent(ai.name)}&avatar=${encodeURIComponent(ai.avatar)}` });
  },

  formatTimestamp: function(timestamp) {
    if (!timestamp) return '初遇';
    const date = new Date(timestamp * 1e3);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
    if (date >= today) return `${date.getHours().toString().padStart(2, "0")}:${date.getMinutes().toString().padStart(2, "0")}`;
    if (date >= yesterday) return "昨天";
    return `${date.getFullYear()}/${(date.getMonth() + 1).toString().padStart(2, "0")}/${date.getDate().toString().padStart(2, "0")}`;
  },

  onShareAppMessage: function () {
    return getShareInfo();
  },

  onShareTimeline: function () {
    return getTimelineInfo();
  }
});

