// pages/daily-checkin/analysis.js
import * as echarts from './components-ecanvas/ec-canvas/echarts';

// --- 全局配置 ---
const API_BASE_URL = 'https://api.feelyourself.cn';

const ANALYSIS_TYPE_MAP = {
  mood_distribution: 'mood',
  tag_correlation: 'tag-mood',
  word_cloud: 'word-cloud',
  color_palette: 'color'
};

const { getShareInfo, getTimelineInfo } = require('../utils/share.js');
Page({
  data: {
    // --- 新增：导航栏数据 ---
    navTop: 0,
    navHeight: 0,
    // --- 控制器状态 ---
    isReady: false,
    selectedTimeRange: 'monthly',
    selectedAnalysis: '',
    quarterMap: [
      { label: '春季', value: 'Q1' }, { label: '夏季', value: 'Q2' },
      { label: '秋季', value: 'Q3' }, { label: '冬季', value: 'Q4' }
    ],
    showPicker: false,
    pickerMode: 'monthly',
    periodLabels: { monthly: '选择月份', quarterly: '选择季度', yearly: '选择年度' },
    periodValues: { monthly: '', quarterly: '', yearly: '' },
    
    // --- 内容区状态 ---
    isLoading: false,
    analysisResult: null,
    ec: {
      lazyLoad: true
    }
  },

  onLoad(options) {
    this.setNavSize();
    this.initDefaultPeriod();
  },
// --- 新增：为适配自定义导航栏新增的函数 ---
setNavSize() {
  const sysInfo = wx.getSystemInfoSync();
  const menuButtonInfo = wx.getMenuButtonBoundingClientRect();
  this.setData({
    navTop: sysInfo.statusBarHeight,
    navHeight: menuButtonInfo.height + (menuButtonInfo.top - sysInfo.statusBarHeight) * 2
  });
},

navigateBack() {
  wx.navigateBack({
    delta: 1
  });
},

  initDefaultPeriod() {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth();
    const monthForDisplay = month + 1;
    const quarterIndex = Math.floor(month / 3);
    const currentQuarterInfo = this.data.quarterMap[quarterIndex];

    this.setData({
      'periodLabels.monthly': `${year}年 ${monthForDisplay}月`,
      'periodValues.monthly': `${year}-${String(monthForDisplay).padStart(2, '0')}`,
      'periodLabels.quarterly': `${year}年 ${currentQuarterInfo.label}`,
      'periodValues.quarterly': `${year}-${currentQuarterInfo.value}`,
      'periodLabels.yearly': `${year}年`,
      'periodValues.yearly': String(year),
    }, () => {
      this.setData({ isReady: true });
    });
  },
  
  selectAnalysis(e) {
    if (!this.data.isReady) {
      wx.showToast({ title: '页面正在初始化...', icon: 'none' });
      return;
    }
      
    const frontendType = e.currentTarget.dataset.type;

    this.setData({
      selectedAnalysis: frontendType,
      isLoading: true,
      analysisResult: null,
    });

    const range = this.data.selectedTimeRange;
    const periodValue = this.data.periodValues[range];
    const backendType = ANALYSIS_TYPE_MAP[frontendType];

    let year, value;
    if (range === 'yearly') { [year, value] = [periodValue, 1]; } 
    else if (range === 'quarterly') { [year, value] = periodValue.split('-Q'); } 
    else { [year, value] = periodValue.split('-'); }

    const token = wx.getStorageSync('token');
    if (!token) {
      wx.showToast({ title: '用户未登录', icon: 'none' });
      this.setData({ isLoading: false });
      return;
    }

    const chartPromise = this.fetchApiData(`/api/v1/report/chart/${backendType}/${range}/${year}/${value}`, token);
    const aiPromise = this.fetchApiData(`/api/v1/report/ai/${backendType}/${range}/${year}/${value}`, token);

    Promise.all([chartPromise, aiPromise])
      .then(([chartRes, aiRes]) => {
        this.setData({
          analysisResult: {
            chartData: chartRes.data,
            interpretation: chartRes.data.interpretation,
            aiReport: aiRes.data.report_text
          },
          isLoading: false
        }, () => {
          // 现在所有分析类型都通过这个统一的函数来渲染图表
          wx.nextTick(() => {
            this.renderChart(frontendType, chartRes.data);
          });
        });
      })
      .catch(err => {
        console.error("API请求失败:", err);
        wx.showToast({ title: err.errMsg || '生成报告失败', icon: 'none', duration: 2000 });
        this.setData({ isLoading: false, analysisResult: null });
      });
  },
  
  fetchApiData(url, token) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: API_BASE_URL + url,
        method: 'GET',
        header: { 'Authorization': `Bearer ${token}` },
        success: (res) => {
          if (res.statusCode >= 200 && res.statusCode < 300) { resolve(res); } 
          else { reject({ errMsg: res.data.detail || `服务器错误 ${res.statusCode}` }); }
        },
        fail: (err) => { reject(err); }
      });
    });
  },

  renderChart(type, data) {
    const chartComponent = this.selectComponent('#analysis-chart');
    if (!chartComponent) { return; }
    chartComponent.init((canvas, width, height, dpr) => {
        const chart = echarts.init(canvas, null, { width, height, devicePixelRatio: dpr });
        let option;
        switch (type) {
            case 'mood_distribution':
                option = this.getMoodChartOption(data);
                break;
            case 'tag_correlation':
                option = this.getTagMoodChartOption(data);
                break;
            case 'word_cloud':
                option = this.getWordCloudPieChartOption(data);
                break;
            case 'color_palette': // 【修改】调用新的饼图函数
                option = this.getColorPieChartOption(data);
                break;
            default: return;
        }
        chart.setOption(option);
        return chart;
    });
  },

  getMoodChartOption(data) {
    return {
      title: { text: data.dominant_mood, subtext: `共打卡 ${data.total_checkins} 天`, left: 'center', top: 'center', textStyle: { fontSize: 24, fontWeight: 'bold', color: '#333' }, subtextStyle: { fontSize: 14, color: '#666' } },
      tooltip: { trigger: 'item', formatter: '{b}: {c}次 ({d}%)' },
      legend: { orient: 'vertical', left: 'left', top: 'center', data: data.mood_distribution.map(item => item.name) },
      series: [{ name: '情绪分布', type: 'pie', radius: ['50%', '70%'], avoidLabelOverlap: false, label: { show: false }, emphasis: { scale: true, scaleSize: 8 }, labelLine: { show: false }, data: data.mood_distribution }]
    };
  },

  getTagMoodChartOption(data) {
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { data: data.chart_data.series.map(item => item.name), top: 5 },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: data.chart_data.categories },
      series: data.chart_data.series.map(s => ({ ...s, type: 'bar', stack: 'total' }))
    };
  },

  getWordCloudPieChartOption(data) {
    const pieData = data.word_list.slice(0, 10);
    return {
      tooltip: { trigger: 'item', formatter: '{b} : {c}次 ({d}%)' },
      legend: { top: '5%', left: 'center' },
      series: [{
          name: '高频词汇', type: 'pie', radius: '55%', center: ['50%', '60%'], data: pieData,
          itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2, shadowBlur: 20, shadowColor: 'rgba(0, 0, 0, 0.2)', shadowOffsetX: 5, shadowOffsetY: 5, },
          emphasis: { itemStyle: { shadowBlur: 25, shadowOffsetX: 0, shadowOffsetY: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' } }
        }
      ]
    };
  },

  /**
   * 【全新】@description 生成【情绪色彩分析】的饼图配置
   */
  getColorPieChartOption(data) {
    // 安全检查，确保后端返回的是我们期望的旧格式
    if (!data || !Array.isArray(data.color_palette)) {
      console.error("getColorPieChartOption: 无效的数据格式，缺少 color_palette 数组。");
      return {};
    }

    return {
      tooltip: {
        trigger: 'item',
        formatter: '{b} : {c}%'
      },
      legend: {
        top: 'bottom',
        left: 'center'
      },
      series: [{
        name: '情绪色卡',
        type: 'pie',
        radius: '60%', // 一个标准的饼图
        center: ['50%', '50%'],
        // 数据需要转换格式，并为每个扇区设置颜色
        data: data.color_palette.map(item => ({
          value: item.percent,
          name: item.name,
          itemStyle: {
            color: item.hex
          }
        })),
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }]
    };
  },

  // ===================================================
  // ========== 【新增功能】处理周期选择器的相关逻辑 ==========
  // ===================================================

  /**
   * @description: 点击“月/季/年”按钮时触发
   */
  openPicker(e) {
    const range = e.currentTarget.dataset.range;
    this.setData({
      selectedTimeRange: range, // 更新高亮按钮
      pickerMode: range,        // 设置选择器模式
      showPicker: true          // 弹出选择器
    });
  },

  /**
   * @description: 周期选择器点击“确认”后触发
   */
  onPickerConfirm(e) {
    const { label, value } = e.detail;
    const range = this.data.selectedTimeRange;

    // 更新按钮标签和内部值，并清空旧的分析结果
    this.setData({
      [`periodLabels.${range}`]: label,
      [`periodValues.${range}`]: value,
      showPicker: false,
      selectedAnalysis: '',
      analysisResult: null
    });
  },

  /**
   * @description: 周期选择器请求关闭时触发
   */
  onPickerClose() {
    this.setData({
      showPicker: false // 关闭选择器
    });
  },

  onShareAppMessage: function () {
    return getShareInfo();
  },

  onShareTimeline: function () {
    return getTimelineInfo();
  }
});
