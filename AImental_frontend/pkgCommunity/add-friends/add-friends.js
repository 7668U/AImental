// pages/add-friends/js - 最终版
// 接口和服务器地址配置
const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';
const SERVER_URL = 'http://127.0.0.1:8000';
let pageJustPerformedShare = false;
Page({
  /**
   * 页面的初始数据
   */
  data: {
    serverUrl: SERVER_URL,
    currentIndex: 0,
    aiList: [],
    hintText: '',
    isEmpty: false,
    isAnimating: false, 
    // --- 以下为自定义弹窗所需数据 ---
    isModalVisible: false,      // 控制弹窗的显示与隐藏
    verificationMessage: '',    // 存储弹窗输入框的内容
    modalCharacterInfo: {},     // 临时存储当前要添加的好友信息（id, index）
    modalCharacterName: '',     // 临时存储当前要添加的好友名字，用于在弹窗标题显示
    isFullyUnlocked: false, // 新增一个状态，方便知道当前是否已解锁
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad: function (options) {
    this.loadDiscoverableCharacters();
  },

  /**
   * [最终修正版] 生命周期函数--监听页面显示
   * onShow 负责核心的分享成功判断逻辑。
   */
  onShow: function () {
    console.log("onShow 触发。开始检查缓存中的分享旗帜...");

    // 【关键修改】从缓存中读取旗帜
    try {
      const justShared = wx.getStorageSync('pageJustPerformedShare');
      if (justShared) {
        // 如果旗帜存在，说明刚从分享界面返回。
        console.log("检测到从分享返回，准备执行解锁...");
        
        // 1. 立刻把旗帜从缓存中删除，避免重复执行
        wx.removeStorageSync('pageJustPerformedShare');
        console.log('分享旗帜已从缓存中移除');

        // 2. 执行分享成功的核心逻辑
        this.handleShareSuccess();
      } else {
        console.log("未在缓存中发现分享旗帜，正常显示页面。");
      }
    } catch (e) {
      console.error('读取分享缓存失败', e);
    }
  },

  // * --- 【在这里新增 onShow 生命周期函数】 ---
  // */
  /**
   * [终极调试版] 生命周期函数--监听页面显示
   */
  /**
   * 封装的API请求函数 (Promise化) - 【修正版】
   */
  _request: function(options) {
    return new Promise((resolve, reject) => {
      const token = wx.getStorageSync('token');
      if (!token) {
        wx.showToast({ title: '请先登录', icon: 'none' });
        reject({ message: 'No token', noAuth: true });
        return;
      }

      let requestUrl = options.url;
      if (!requestUrl.startsWith('http')) {
        requestUrl = API_BASE_URL + requestUrl;
      }

      wx.request({
        url: requestUrl,
        method: options.method || 'GET',
        header: { 'Authorization': `Bearer ${token}`, ...options.header },
        data: options.data || {},
        success: (res) => {
          // --- 【关键代码-开始】 ---
          // 检查HTTP状态码
          if (res.statusCode >= 200 && res.statusCode < 300) {
            // 状态码正常，Promise成功，并把数据传递出去
            resolve(res.data); 
          } else {
            // 状态码异常（如404, 500等），Promise失败，并把错误信息传递出去
            console.error('API Error:', res);
            wx.showToast({ title: res.data.detail || '请求失败', icon: 'none' });
            reject(res);
          }
          // --- 【关键代码-结束】 ---
        },
        fail: (err) => {
          // --- 【关键代码-开始】 ---
          // 网络请求本身就失败了（比如断网）
          console.error('Request Failed:', err);
          wx.showToast({ title: '无法连接服务器', icon: 'none' });
          reject(err);
          // --- 【关键代码-结束】 ---
        }
      });
    });
  },
  /**
   * [调试版] 从服务器加载角色数据
   */
  loadDiscoverableCharacters: function() {
    wx.showLoading({ title: '加载中...' });
    this._request({ url: '/community/discover/characters' })
      .then(data => {
        // --- 调试日志 1: 打印收到的原始数据 ---
        console.log('成功获取到后端数据:', data);

        // --- 使用 try...catch 包裹核心逻辑，防止报错导致白屏 ---
        try {
          // 检查关键数据是否存在，如果不存在，就给出提示
          if (!data || !Array.isArray(data.characters)) {
            console.error("后端返回的数据格式不正确！期望得到一个包含 characters 数组的对象。");
            // 即使数据格式不对，也隐藏加载框，并提示用户
            this.setData({ isEmpty: true, hintText: '数据解析失败，请稍后重试' });
            return; // 提前结束，不再往下执行
          }

          const characterList = data.characters.map((item) => ({
            ...item,
            tags: item.profile?.personality_traits?.personality_tags?.slice(0, 3) || [],
            animationClass: 'inactive',
            isLocked: false 
          }));

          if (!data.is_fully_unlocked && data.total_count > 0) {
            characterList.push({
              id: 'locked-card',
              isLocked: true
            });
          }
          
          if (characterList.length > 0 && !characterList[0].isLocked) {
            characterList[0].animationClass = 'active';
          }
          
          console.log('准备渲染的数据:', characterList); // --- 调试日志 2: 打印处理后的数据 ---
          
          this.setData({
            aiList: characterList,
            isFullyUnlocked: data.is_fully_unlocked,
            isEmpty: data.total_count === 0,
            hintText: data.is_fully_unlocked ? '～ 左右滑动发现新朋友 ～' : '～ 分享给好友解锁更多伙伴 ～',
          });

        } catch (e) {
          // 如果 try 里面的代码执行出错，就会在这里捕获到
          console.error('处理数据时发生严重错误:', e);
          this.setData({ isEmpty: true, hintText: '处理数据时出错，请检查控制台' });
        }
      })
      .catch(err => {
        // 网络请求本身的失败会在这里捕获
        console.error('网络请求失败:', err);
        this.setData({ isEmpty: true, hintText: '加载失败，请稍后重试' });
      })
      .finally(() => {
        // 无论成功还是失败，最后都隐藏加载框
        wx.hideLoading();
      });
  },

  /**
   * [新增] 专门处理分享成功的函数
   */
  handleShareSuccess: function() {
    console.log("执行解锁逻辑...");
    wx.showToast({ title: '正在解锁...', icon: 'loading', duration: 3000 });

    this._request({
      // 【建议修改】使用拼接的方式，而不是硬编码
      url: '/users/me/unlock-community', 
      method: 'PUT',
    }).then(apiRes => {
      wx.hideLoading();
      wx.showToast({ title: '解锁成功！', icon: 'success' });
      this.loadDiscoverableCharacters();
    }).catch(apiErr => {
      wx.hideLoading();
      wx.showToast({ title: '解锁请求失败', icon: 'none' });
    });
},
    /**
   * [重构] 处理分享逻辑
   */
/**
   * [终极调试版] 处理分享逻辑
   */
  /**
   * [最终修正版] 处理分享逻辑
   * 我们把所有调试用的 Toast 都换成 console.log，这样就不会互相覆盖了。
   */
  /**
   * [最终修正版] 处理分享逻辑
   * 我们把所有调试用的 Toast 都换成 console.log，这样就不会互相覆盖了。
   */
  onShareAppMessage: function (res) {
    console.log('分享面板已弹出 (极简测试版)');
    
    // 【关键修改】不再使用页面变量，而是将分享状态存入缓存
    try {
      wx.setStorageSync('pageJustPerformedShare', true);
      console.log('分享旗帜已存入缓存');
    } catch (e) {
      console.error('设置分享缓存失败', e);
    }

    // 只返回一个标题，暂时移除 path 和 imageUrl
    return {
      title: '这是一个分享测试',
      // 推荐加上 path，指向当前页面，保证用户点击后能回到正确的地方
      path: '/pkgCommunity/add-friends/add-friends',
      imageUrl: '/images/share-cover.png' // 【关键】这里就是分享图片的路径
    }
  },

  shareToUnlock: function() {
    wx.showToast({
      title: '请点击右上角进行分享',
      icon: 'none',
      duration: 2000
    });
  },
  /**
   * Swiper滑动事件，处理淡入淡出动画
   */
  onSwiperChange: function(e) {
    if (e.detail.source !== 'touch' || this.data.isAnimating) return;

    this.setData({ isAnimating: true });
    let aiList = this.data.aiList;

    // 将所有卡片都设置为非激活状态
    aiList.forEach(item => item.animationClass = 'inactive');
    
    // 仅将当前显示的卡片设置为激活状态
    if (aiList[e.detail.current]) {
        aiList[e.detail.current].animationClass = 'active';
    }
    
    this.setData({
      aiList: aiList,
      currentIndex: e.detail.current
    });

    // 等待动画播放完毕后，再解除锁定
    setTimeout(() => {
      this.setData({ isAnimating: false });
    }, 450);
  },

  /**
   * 点击添加按钮，显示自定义弹窗
   */
  showVerificationModal: function(e) {
    const { id, index, name } = e.currentTarget.dataset;
    this.setData({
      isModalVisible: true,
      modalCharacterInfo: { id, index },
      modalCharacterName: name,
      verificationMessage: '' // 清空上次的输入
    });
  },

  /**
   * 监听弹窗内输入框的输入
   */
  onVerificationInput: function(e) {
    this.setData({
      verificationMessage: e.detail.value
    });
  },

  /**
   * 点击弹窗的“取消”按钮或遮罩层
   */
  onModalCancel: function() {
    this.setData({
      isModalVisible: false
    });
  },

  /**
   * 点击弹窗的“发送”按钮
   */
  onModalConfirm: function() {
    const { id, index } = this.data.modalCharacterInfo;
    const message = this.data.verificationMessage || `你好，我是${wx.getStorageSync('userInfo')?.nickname || '一位旅行者'}，可以交个朋友吗？`;

    this.setData({ isModalVisible: false });
    this.sendFriendRequest(id, index, message);
  },

  /**
   * 独立的发送好友请求的函数
   */
  sendFriendRequest: function(id, index, message) {
    wx.showLoading({ title: '正在发送...' });
    this._request({
      url: `/community/friendship/request/${id}`,
      method: 'POST',
      data: { verification_message: message }
    })
    .then(data => {
      wx.hideLoading();
      wx.showToast({ title: '请求已发送', icon: 'success' });
      this.removeCard(index);
    })
    .catch(err => {
      wx.hideLoading();
    });
  },

  /**
   * 带动画地移除卡片
   */
  removeCard: function(index) {
    let aiList = this.data.aiList;
    aiList[index].animationClass = 'disappearing';
    this.setData({ aiList });

    setTimeout(() => {
      aiList.splice(index, 1);
      if (aiList.length === 0) {
        this.setData({ aiList: [], isEmpty: true, hintText: '～ 社区暂无新成员 ～' });
        return;
      }
      const newCurrentIndex = Math.max(0, Math.min(index, aiList.length - 1));
      
      // 重新激活当前卡片
      aiList.forEach((item, i) => { 
        item.animationClass = i === newCurrentIndex ? 'active' : 'inactive';
      });

      this.setData({ aiList, currentIndex: newCurrentIndex });
    }, 400); // 动画时长
  },

  /**
   * 跳转到历史记录页面
   */
  goToHistory: function() {
    wx.navigateTo({
      url: '../request-history/request-history',
    });
  }
});