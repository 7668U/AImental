// pages/assessment/index/index.js

const API_BASE_URL = 'http://127.0.0.1:8000';
const DEFAULT_ICON_PATH = '/images/assessment/default.png'; // 默认图标路径
const DEFAULT_CATEGORY = '专业测试'; // [新增] 默认显示的分类

Page({
  data: {
    statusBarHeight: 0, // [新增] 状态栏高度
    rawScaleList: [],
    displayScaleList: [],
    activeCategory: '专业测试',
    isLoading: true,
    isError: false,
  },

  onLoad(options) {
    // [新增] 动态获取状态栏高度
    const systemInfo = wx.getSystemInfoSync();
    this.setData({
      statusBarHeight: systemInfo.statusBarHeight
    });
    
    // 原有的逻辑保持不变
    this.fetchScaleList();
  },

  /**
   * 从后端API获取测评列表
   */
/**
   * 从后端API获取测评列表 (最终修正版：已添加授权Header)
   */
  fetchScaleList() {
    this.setData({ isLoading: true, isError: false });

    // [新增] 从本地缓存中获取登录后保存的Token
    // 请确保 'token' 是您在登录成功后，使用 wx.setStorageSync 保存的键名
    const token = wx.getStorageSync('token');

    // 如果没有token，说明用户未登录，可以直接处理，避免向后端发送无效请求
    if (!token) {
      this.setData({
        isLoading: false,
        isError: true, // 或者可以设置为一个特定的“未登录”状态
      });
      // 提示用户去登录
      wx.showToast({
        title: '请先登录',
        icon: 'none',
        duration: 2000
      });
      return; // 终止函数执行
    }

    wx.request({
      url: `${API_BASE_URL}/api/v1/assessments/`,
      method: 'GET',
      // [新增] 加入包含用户凭证的请求头
      header: {
        'Authorization': `Bearer ${token}`
        // 如果您的后端需要的不是Bearer类型，请修改这里
        // 例如: 'Authorization': token
      },
      success: (res) => {
        // [修改] 增加对401状态码的判断
        if (res.statusCode === 401) {
          // Token可能已过期或无效，引导用户重新登录
          this.setData({ isError: true, isLoading: false });
          wx.showToast({
            title: '登录状态已失效，请重新登录',
            icon: 'none'
          });
          // 这里可以加上跳转到登录页的逻辑
          // wx.navigateTo({ url: '/pages/login/index' });
          return;
        }

        if (res.statusCode === 200) {
          const rawList = res.data || [];
          const processedList = rawList.map(scale => {
            const iconName = scale.short_name ? scale.short_name.toLowerCase() : 'default';
            return {
              ...scale,
              iconPath: `/images/assessment/${iconName}.png`
            };
          });
          
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
        // complete回调中的setData是安全的
        this.setData({ isLoading: false });
        wx.stopPullDownRefresh();
      }
    });
  },
  /**
   * [新增] 点击分类按钮时的处理函数
   * @param {Object} e 事件对象，从wxml的data-category获取分类名
   */
  switchCategory(e) {
    const newCategory = e.currentTarget.dataset.category;
    
    // 如果点击的已经是当前分类，则不执行任何操作，避免不必要的重复渲染
    if (newCategory === this.data.activeCategory) {
      return;
    }

    // 更新当前激活的分类
    this.setData({
      activeCategory: newCategory
    });
    
    // 调用方法，根据新的分类名来筛选和显示列表
    this.filterAndSetDisplayList(newCategory);
  },

  /**
   * [新增] 根据分类名过滤并设置显示的列表
   * @param {string} categoryName 需要显示的分类名称
   */
  filterAndSetDisplayList(categoryName) {
    // 从原始列表中筛选出所有符合当前分类的项
    const filteredList = this.data.rawScaleList.filter(scale => scale.category === categoryName);
    
    // 更新到页面显示列表
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
   * 如果某个图标不存在，就用默认图标替代
   */
  handleIconError(e) {
    const errorIndex = e.currentTarget.dataset.index;
    // [修改] 更新路径，确保作用于当前显示的列表 displayScaleList
    const updatedPath = `displayScaleList[${errorIndex}].iconPath`;
    this.setData({
      [updatedPath]: DEFAULT_ICON_PATH
    });
  }
});