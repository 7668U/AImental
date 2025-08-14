// pages/add-friends/js - 最终版
// 接口和服务器地址配置
const API_BASE_URL = 'http://127.0.0.1:8000/api/v1/community';
const SERVER_URL = 'http://127.0.0.1:8000';

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
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad: function (options) {
    this.loadDiscoverableCharacters();
  },

  /**
   * 封装的API请求函数 (Promise化)
   */
  _request: function(options) {
    return new Promise((resolve, reject) => {
      const token = wx.getStorageSync('token');
      if (!token) {
        wx.showToast({ title: '请先登录', icon: 'none' });
        reject({ message: 'No token', noAuth: true });
        return;
      }
      wx.request({
        url: API_BASE_URL + options.url,
        method: options.method || 'GET',
        header: { 'Authorization': `Bearer ${token}`, ...options.header },
        data: options.data || {},
        success: (res) => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(res.data);
          } else {
            console.error('API Error:', res);
            wx.showToast({ title: res.data.detail || '请求失败', icon: 'none' });
            reject(res);
          }
        },
        fail: (err) => {
          console.error('Request Failed:', err);
          wx.showToast({ title: '无法连接服务器', icon: 'none' });
          reject(err);
        }
      });
    });
  },

  /**
   * 加载可发现的AI角色列表
   */
  loadDiscoverableCharacters: function() {
    wx.showLoading({ title: '加载中...' });
    this._request({ url: '/discover/characters' })
      .then(data => {
        const processedList = data.map((item) => ({
          ...item,
          tags: item.profile?.personality_traits?.personality_tags?.slice(0, 3) || [],
          // 初始状态为非激活，准备入场动画
          animationClass: 'inactive' 
        }));
        
        // 让第一张卡片激活入场
        if (processedList.length > 0) {
          processedList[0].animationClass = 'active';
        }
        
        this.setData({
          aiList: processedList,
          isEmpty: processedList.length === 0,
          hintText: processedList.length > 0 ? '～ 左右滑动发现新朋友 ～' : '～ 社区暂无新成员 ～',
          currentIndex: 0,
        });
      })
      .catch(err => {
        this.setData({ isEmpty: true, hintText: '加载失败，请稍后重试' });
      })
      .finally(() => {
        wx.hideLoading();
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
      url: `/friendship/request/${id}`,
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
      url: '/pages/ai-community/request-history/request-history',
    });
  }
});