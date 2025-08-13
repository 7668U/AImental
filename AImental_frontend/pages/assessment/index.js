// pages/assessment/index/index.js

const API_BASE_URL = 'http://127.0.0.1:8000';
const DEFAULT_ICON_PATH = '/images/assessment/default.png';
const DEFAULT_CATEGORY = '专业测试';

Page({
  data: {
    isLoggedIn: false,        // [新增] 登录状态，默认为未登录
    statusBarHeight: 0,
    rawScaleList: [],
    displayScaleList: [],
    activeCategory: DEFAULT_CATEGORY,
    isLoading: false,         // [修改] 初始状态不加载，等待登录检查后触发
    isError: false,
  },

  /**
   * [修改] 使用 onShow 代替 onLoad
   * onShow 能保证每次进入页面（或从其他页面返回）时都检查登录状态，体验更佳
   */
  onShow() {
    // 动态获取状态栏高度
    const systemInfo = wx.getSystemInfoSync();
    this.setData({
      statusBarHeight: systemInfo.statusBarHeight
    });
    
    // 每次显示页面时，都检查登录状态
    this.checkLoginStatus();
  },
  
  /**
   * [新增] 检查登录状态的核心函数
   */
  checkLoginStatus() {
    const token = wx.getStorageSync('token');
    if (token) {
      // 如果有token，则更新为已登录状态，并开始加载数据
      this.setData({ isLoggedIn: true });
      this.fetchScaleList();
    } else {
      // 如果没有token，则确保为未登录状态，页面会显示登录提示
      this.setData({ isLoggedIn: false });
    }
  },

  /**
   * [新增] 处理来自 login-prompt 组件的登录成功事件
   */
  handleLogin() {
    // 当用户在 login-prompt 组件中成功登录后，该组件会触发此函数
    // 我们只需重新检查一遍登录状态，页面就会自动刷新为已登录界面
    this.checkLoginStatus();
  },

  /**
   * 从后端API获取测评列表
   */
  fetchScaleList() {
    this.setData({ isLoading: true, isError: false });
    const token = wx.getStorageSync('token');
    
    wx.request({
      url: `${API_BASE_URL}/api/v1/assessments/`,
      method: 'GET',
      header: {
        'Authorization': `Bearer ${token}`
      },
      success: (res) => {
        if (res.statusCode === 401) {
          // Token已过期或无效，切换回未登录状态
          this.setData({ isLoggedIn: false, isLoading: false });
          wx.showToast({ title: '登录已失效，请重新登录', icon: 'none' });
          return;
        }

        if (res.statusCode === 200) {
          const rawList = res.data || [];
          const processedList = rawList.map(scale => ({
            ...scale,
            iconPath: `/images/assessment/${scale.short_name ? scale.short_name.toLowerCase() : 'default'}.png`
          }));
          
          const filteredDisplayList = processedList.filter(scale => scale.category === this.data.activeCategory);

          this.setData({
            rawScaleList: processedList,
            displayScaleList: filteredDisplayList
          });
        } else {
          this.setData({ isError: true });
        }
      },
      fail: (err) => {
        this.setData({ isError: true });
        console.error("fetchScaleList failed:", err);
      },
      complete: () => {
        this.setData({ isLoading: false });
        if (this.data.isLoggedIn) { // 只有在登录状态下才停止下拉刷新
          wx.stopPullDownRefresh();
        }
      }
    });
  },
  
  /**
   * [新增] 下拉刷新逻辑
   */
  onPullDownRefresh() {
    if (this.data.isLoggedIn) {
      this.fetchScaleList();
    } else {
      // 如果未登录，则不执行任何操作，并立即停止刷新动画
      wx.stopPullDownRefresh();
    }
  },

  /**
   * 点击分类按钮时的处理函数
   */
  switchCategory(e) {
    const newCategory = e.currentTarget.dataset.category;
    if (newCategory === this.data.activeCategory) {
      return;
    }
    this.setData({
      activeCategory: newCategory
    });
    this.filterAndSetDisplayList(newCategory);
  },

  /**
   * 根据分类名过滤并设置显示的列表
   */
  filterAndSetDisplayList(categoryName) {
    const filteredList = this.data.rawScaleList.filter(scale => scale.category === categoryName);
    this.setData({
      displayScaleList: filteredList
    });
  },

  /**
   * 点击卡片，跳转到答题页面
   */
  goToTest(e) {
    const scaleId = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `./test?id=${scaleId}`,
    });
  },
  
  /**
   * 图标加载失败时的容错处理
   */
  handleIconError(e) {
    const errorIndex = e.currentTarget.dataset.index;
    const updatedPath = `displayScaleList[${errorIndex}].iconPath`;
    this.setData({
      [updatedPath]: DEFAULT_ICON_PATH
    });
  }
});