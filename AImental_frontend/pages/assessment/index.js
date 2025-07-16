// pages/assessment/index/index.js

const API_BASE_URL = 'http://49.233.220.130:8000';
const DEFAULT_ICON_PATH = '/images/assessment/default.png'; // 默认图标路径

Page({
  data: {
    scaleList: [],      // 测评列表
    isLoading: true,    // 是否正在加载
    isError: false,     // 是否加载失败
  },

  /**
   * 页面加载时执行
   */
  onLoad(options) {
    this.fetchScaleList();
  },

  /**
   * 下拉刷新时执行
   */
  onPullDownRefresh() {
    this.fetchScaleList();
  },

  /**
   * 从后端API获取测评列表
   */
  fetchScaleList() {
    this.setData({ isLoading: true, isError: false });

    wx.request({
      url: `${API_BASE_URL}/api/v1/assessments/`,
      method: 'GET',
      success: (res) => {
        if (res.statusCode === 200) {
          // 对返回的数据进行处理，为每个测试添加图标路径
          const processedList = res.data.map(scale => {
            // 我们使用量表的 short_name (如'phq-9') 作为图标的文件名
            const iconName = scale.short_name ? scale.short_name.toLowerCase() : 'default';
            return {
              ...scale,
              iconPath: `/images/assessment/${iconName}.png`
            };
          });
          this.setData({ scaleList: processedList });
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
        wx.stopPullDownRefresh(); // 停止下拉刷新动画
      }
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
    const updatedPath = `scaleList[${errorIndex}].iconPath`;
    this.setData({
      [updatedPath]: DEFAULT_ICON_PATH
    });
  }
});