// pages/daily-checkin/analysis.js
import * as echarts from './components-ecanvas/ec-canvas/echarts';

// --- 全局配置 ---
const API_BASE_URL = 'https://feelyourself.cn';

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
    isColorCardLoading: false,
    colorCardResult: null,
    colorCardError: '',
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
  
  async selectAnalysis(e) {
    if (!this.data.isReady) {
      wx.showToast({ title: '页面正在初始化...', icon: 'none' });
      return;
    }
      
    const frontendType = e.currentTarget.dataset.type;

    this.setData({
      selectedAnalysis: frontendType,
      isLoading: true,
      analysisResult: null,
      isColorCardLoading: false,
      colorCardResult: null,
      colorCardError: '',
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

    try {
      const eligibilityRes = await this.fetchApiData(`/api/v1/report/eligibility/${range}/${year}/${value}`, token);
      const eligibility = eligibilityRes.data || {};
      if (!eligibility.can_analyze) {
        this.setData({
          isLoading: false,
          analysisResult: null,
          isColorCardLoading: false,
          colorCardResult: null,
          colorCardError: ''
        });
        this.showNotEnoughDataModal(eligibility);
        return;
      }
    } catch (err) {
      this.setData({
        isLoading: false,
        analysisResult: null,
        isColorCardLoading: false,
        colorCardResult: null,
        colorCardError: ''
      });
      wx.showToast({ title: err.errMsg || '暂时无法检查打卡天数', icon: 'none' });
      return;
    }

    const chartPromise = this.fetchApiData(`/api/v1/report/chart/${backendType}/${range}/${year}/${value}`, token);
    const aiPromise = this.fetchApiData(`/api/v1/report/ai/${backendType}/${range}/${year}/${value}`, token);

    Promise.all([chartPromise, aiPromise])
      .then(([chartRes, aiRes]) => {
        this.setData({
          analysisResult: {
            chartData: chartRes.data,
            interpretation: aiRes.data.summary_text || chartRes.data.interpretation,
            colorMixInterpretation: '',
            aiReport: aiRes.data.report_text || ''
          },
          isLoading: false
        }, () => {
          wx.nextTick(() => {
            this.renderChart(frontendType, chartRes.data);
          });
          if (frontendType === 'color_palette') {
            this.loadColorCardBackground(range, year, value, token);
          }
        });
      })
      .catch(err => {
        console.error("API请求失败:", err);
        wx.showToast({ title: err.errMsg || '生成报告失败', icon: 'none', duration: 2000 });
        this.setData({
          isLoading: false,
          analysisResult: null,
          isColorCardLoading: false,
          colorCardResult: null,
          colorCardError: ''
        });
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

  showNotEnoughDataModal(eligibility) {
    const periodName = eligibility.period_name || '这个周期';
    const minDays = eligibility.min_days || 5;
    wx.showModal({
      title: '还差一点点哦',
      content: `您在${periodName}的打卡数据不大于5天，无法进行分析哦~\n快去积极记录心情吧~`,
      confirmText: '去记录',
      cancelText: '知道啦',
      success: (res) => {
        if (res.confirm) {
          wx.navigateTo({ url: '/pkgDailyCheckin/record' });
        }
      }
    });
  },

  normalizeAssetUrl(url) {
    if (!url) return '';
    if (/^https?:\/\//.test(url) || url.startsWith('wxfile://') || url.startsWith('cloud://')) {
      return url;
    }
    return `${API_BASE_URL}${url}`;
  },

  loadColorCardBackground(range, year, value, token) {
    this.setData({
      isColorCardLoading: true,
      colorCardResult: null,
      colorCardError: ''
    });

    this.fetchApiData(`/api/v1/report/color-card/${range}/${year}/${value}`, token)
      .then((res) => {
        const payload = res.data || {};
        const imageResult = payload.image_result || {};
        const colorMixInterpretation = this.buildColorMixInterpretation(payload);
        const nextData = {
          colorCardResult: {
            ...payload,
            imageUrl: this.normalizeAssetUrl(imageResult.background_image_url),
            isCached: !!imageResult.cached,
          },
          colorCardError: imageResult.background_image_url ? '' : (imageResult.error || 'AI 颜色背景图暂时生成失败')
        };

        if (this.data.analysisResult) {
          nextData['analysisResult.colorMixInterpretation'] = colorMixInterpretation;
        }

        this.setData(nextData);
      })
      .catch((err) => {
        this.setData({
          colorCardResult: null,
          colorCardError: err.errMsg || 'AI 颜色背景图暂时生成失败'
        });
      })
      .finally(() => {
        this.setData({ isColorCardLoading: false });
      });
  },

  buildColorMixInterpretation(colorCardPayload) {
    const namingResult = colorCardPayload.naming_result || {};
    const mixedColor = colorCardPayload.mixed_color || {};
    const colorName = namingResult.color_name || mixedColor.hex || '';
    if (!colorName) return '';

    return `把你这段时间记录下来的颜色混合在一起，得到的总和颜色是「${colorName}」。`;
  },

  previewColorCardImage() {
    const url = this.data.colorCardResult && this.data.colorCardResult.imageUrl;
    if (!url) return;
    wx.previewImage({ current: url, urls: [url] });
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

  getSoftPieChartOption({ name, data, tooltipFormatter, center = ['50%', '60%'], radius = '55%' }) {
    return {
      tooltip: { trigger: 'item', formatter: tooltipFormatter },
      legend: { top: '5%', left: 'center' },
      series: [{
        name,
        type: 'pie',
        radius,
        center,
        data,
        label: { show: false },
        labelLine: { show: false },
        itemStyle: {
          borderRadius: 8,
          borderColor: '#fff',
          borderWidth: 2,
          shadowBlur: 20,
          shadowColor: 'rgba(0, 0, 0, 0.2)',
          shadowOffsetX: 5,
          shadowOffsetY: 5,
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 25,
            shadowOffsetX: 0,
            shadowOffsetY: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }]
    };
  },

  getMoodChartOption(data) {
    return this.getSoftPieChartOption({
      name: '情绪分布',
      data: data.mood_distribution,
      tooltipFormatter: '{b}: {c}次 ({d}%)'
    });
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
    return this.getSoftPieChartOption({
      name: '高频词汇',
      data: pieData,
      tooltipFormatter: '{b} : {c}次 ({d}%)'
    });
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

    return this.getSoftPieChartOption({
      name: '情绪色卡',
      tooltipFormatter: '{b} : {c}%',
      data: data.color_palette.map(item => ({
          value: item.percent,
          name: item.name,
          itemStyle: {
            color: item.hex
          }
      }))
    });
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
