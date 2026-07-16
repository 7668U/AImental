// pages/daily-checkin/analysis.js
import * as echarts from './components-ecanvas/ec-canvas/echarts';

// --- 全局配置 ---
const API_BASE_URL = 'http://127.0.0.1:8000';

const ANALYSIS_TYPE_MAP = {
  mood_distribution: 'mood',
  tag_correlation: 'tag-mood',
  word_cloud: 'word-cloud',
  color_palette: 'color'
};
const BACKEND_ANALYSIS_TYPE_MAP = {
  mood: 'mood_distribution',
  'tag-mood': 'tag_correlation',
  'word-cloud': 'word_cloud',
  color: 'color_palette'
};
const CHART_FONT_FAMILY = 'PingFang SC, Microsoft YaHei, Helvetica Neue, Arial, sans-serif';
const ANALYSIS_MODULES = [
  {
    frontendType: 'mood_distribution',
    backendType: 'mood',
    title: '心情频次',
    chartTitle: '心情频次总览',
    chartId: 'chart_mood_distribution',
    icon: 'https://assets.feelyourself.cn/miniprogram/assets/v1/pkgDailyCheckin/images/analysis/report-mood-distribution.png'
  },
  {
    frontendType: 'tag_correlation',
    backendType: 'tag-mood',
    title: '状态关联',
    chartTitle: '状态关联总览',
    chartId: 'chart_tag_correlation',
    icon: 'https://assets.feelyourself.cn/miniprogram/assets/v1/pkgDailyCheckin/images/analysis/report-status-correlation.png'
  },
  {
    frontendType: 'word_cloud',
    backendType: 'word-cloud',
    title: '文字分析',
    chartTitle: '文字分析总览',
    chartId: 'chart_word_cloud',
    icon: 'https://assets.feelyourself.cn/miniprogram/assets/v1/pkgDailyCheckin/images/analysis/report-text-analysis.png'
  },
  {
    frontendType: 'color_palette',
    backendType: 'color',
    title: '情绪色卡',
    chartTitle: '情绪色卡总览',
    chartId: 'chart_color_palette',
    icon: 'https://assets.feelyourself.cn/miniprogram/assets/v1/pkgDailyCheckin/images/analysis/report-color-card.png'
  }
];

const { getShareInfo, getTimelineInfo } = require('../utils/share.js');
const {
  isVipQuotaExhaustedError,
  showVipQuotaModal,
} = require('../utils/vip-quota.js');
Page({
  data: {
    // --- 新增：导航栏数据 ---
    navTop: 0,
    navHeight: 0,
    // --- 控制器状态 ---
    isReady: false,
    selectedAnalysis: '',
    dayOptions: [
      { label: '近3天', days: 3 },
      { label: '近7天', days: 7 },
      { label: '近14天', days: 14 },
      { label: '近30天', days: 30 }
    ],
    selectedDayCount: 7,
    selectedRangeDays: 7,
    rangeStartDate: '',
    rangeEndDate: '',
    rangeLabel: '',
    maxDate: '',
    
    // --- 内容区状态 ---
    isLoading: false,
    analysisResult: null,
    analysisReports: [],
    activeReport: null,
    isChartReady: false,
    hasAnalyzed: false,
    pendingAnalysisType: '',
    isColorCardLoading: false,
    colorCardResult: null,
    colorCardError: '',
    ec: {
      lazyLoad: true
    }
  },

  onLoad(options) {
    this.setNavSize();
    this.initDefaultPeriod(options || {});
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

  initDefaultPeriod(options = {}) {
    const historyRange = this.getHistoryRangeFromOptions(options);
    if (historyRange) {
      this.setData({
        selectedDayCount: 0,
        selectedRangeDays: historyRange.days,
        rangeStartDate: historyRange.startDate,
        rangeEndDate: historyRange.endDate,
        maxDate: this.formatDate(new Date()),
        rangeLabel: this.formatRangeLabel(historyRange.startDate, historyRange.endDate),
        pendingAnalysisType: historyRange.frontendType || ''
      }, () => {
        this.setData({ isReady: true });
      });
      return;
    }

    const range = this.buildDateRangeByDays(this.data.selectedDayCount);

    this.setData({
      rangeStartDate: range.startDate,
      rangeEndDate: range.endDate,
      maxDate: range.endDate,
      selectedRangeDays: range.days,
      rangeLabel: this.formatRangeLabel(range.startDate, range.endDate),
    }, () => {
      this.setData({ isReady: true });
    });
  },

  getHistoryRangeFromOptions(options = {}) {
    const startDate = options.start_date || options.startDate;
    const endDate = options.end_date || options.endDate;
    const rawType = options.type || options.analysis_type || options.analysisType || '';
    const decodedType = rawType ? decodeURIComponent(rawType) : '';
    const frontendType = ANALYSIS_TYPE_MAP[decodedType] ? decodedType : BACKEND_ANALYSIS_TYPE_MAP[decodedType];

    if (!startDate || !endDate) return null;
    const days = this.getRangeDays(startDate, endDate);
    if (!Number.isFinite(days) || days <= 0) return null;

    return {
      startDate,
      endDate,
      days,
      frontendType
    };
  },

  buildDateRangeByDays(days) {
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - days + 1);
    return {
      startDate: this.formatDate(start),
      endDate: this.formatDate(end),
      days
    };
  },

  formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  },

  parseDate(dateStr) {
    const [year, month, day] = dateStr.split('-').map(Number);
    return new Date(year, month - 1, day);
  },

  getRangeDays(startDate, endDate) {
    const start = this.parseDate(startDate);
    const end = this.parseDate(endDate);
    return Math.floor((end - start) / 86400000) + 1;
  },

  formatRangeLabel(startDate, endDate) {
    const start = this.parseDate(startDate);
    const end = this.parseDate(endDate);
    const sameYear = start.getFullYear() === end.getFullYear();
    const startLabel = sameYear
      ? `${start.getMonth() + 1}月${start.getDate()}日`
      : `${start.getFullYear()}年${start.getMonth() + 1}月${start.getDate()}日`;
    return `${startLabel} - ${end.getMonth() + 1}月${end.getDate()}日`;
  },

  resetAnalysisResult() {
    this.setData({
      selectedAnalysis: '',
      analysisResult: null,
      analysisReports: [],
      activeReport: null,
      isChartReady: false,
      hasAnalyzed: false,
      isColorCardLoading: false,
      colorCardResult: null,
      colorCardError: ''
    });
  },

  async loadAllAnalyses() {
    if (!this.data.isReady) return;
    if (this.data.isLoading) return;

    const startDate = this.data.rangeStartDate;
    const endDate = this.data.rangeEndDate;
    const token = wx.getStorageSync('token');
    if (!token) {
      wx.showToast({ title: '用户未登录', icon: 'none' });
      return;
    }

    this.setData({
      isLoading: true,
      selectedAnalysis: '',
      analysisResult: null,
      analysisReports: [],
      activeReport: null,
      isChartReady: false,
      hasAnalyzed: false,
      isColorCardLoading: false,
      colorCardResult: null,
      colorCardError: ''
    });

    let eligibility = {};
    try {
      const eligibilityRes = await this.fetchApiData(`/api/v1/report/eligibility/range/${startDate}/${endDate}`, token);
      eligibility = eligibilityRes.data || {};
      if (!eligibility.can_analyze) {
        this.setData({ isLoading: false });
        this.showNotEnoughDataModal(eligibility);
        return;
      }
    } catch (err) {
      this.setData({ isLoading: false });
      if (isVipQuotaExhaustedError(err)) {
        showVipQuotaModal({ error: err, feature: 'mood_analysis' });
        return;
      }
      wx.showToast({ title: err.errMsg || '暂时无法检查打卡数据', icon: 'none' });
      return;
    }

    const chartTasks = ANALYSIS_MODULES.map(module => (
      this.loadReportModule(module, token, startDate, endDate, eligibility)
    ));
    const aiReportsPromise = this.fetchApiData(`/api/v1/report/ai/range/all/${startDate}/${endDate}`, token)
      .then((res) => res.data || {})
      .catch((err) => ({ __error: err.errMsg || 'AI 报告暂时没有生成成功，请稍后再试。' }));

    Promise.all([Promise.all(chartTasks), aiReportsPromise])
      .then(([chartReports, aiReports]) => {
        const reports = chartReports.map((report) => {
          if (report.skipped || report.error) return report;
          if (aiReports.__error) {
            return {
              ...report,
              aiReport: aiReports.__error,
              aiLoaded: false,
              aiLoading: false,
              aiError: true
            };
          }

          const aiReport = aiReports[report.backendType];
          if (!aiReport) return report;
          if (aiReport.skipped) {
            return {
              ...report,
              skipped: true,
              skipMessage: aiReport.report_text || report.skipMessage || `${report.title}暂时无法生成。`
            };
          }

          return {
            ...report,
            interpretation: aiReport.summary_text || report.interpretation || '',
            aiReport: aiReport.report_text || '',
            aiLoaded: true,
            aiLoading: false,
            aiError: false
          };
        });
        this.setData({
          analysisReports: reports,
          activeReport: null,
          isChartReady: false,
          selectedAnalysis: '',
          hasAnalyzed: true,
          isLoading: false
        });
      })
      .catch((err) => {
        console.error('批量生成报告失败:', err);
        this.setData({ isLoading: false });
        if (isVipQuotaExhaustedError(err)) {
          showVipQuotaModal({ error: err, feature: 'mood_analysis' });
          return;
        }
        wx.showToast({ title: err.errMsg || '生成报告失败', icon: 'none' });
      });
  },

  selectReportSection(e) {
    const frontendType = e.currentTarget.dataset.type;
    const report = (this.data.analysisReports || []).find(item => item.frontendType === frontendType);
    if (!report) return;

    this.setData({
      selectedAnalysis: frontendType,
      activeReport: report,
      isChartReady: false,
      isColorCardLoading: false,
      colorCardResult: null,
      colorCardError: ''
    }, () => {
      if (report.skipped || report.error || !report.chartData) return;
      wx.nextTick(() => {
        this.setData({ isChartReady: true }, () => {
          wx.nextTick(() => {
            this.renderChart(report.frontendType, report.chartData);
          });
        });
      });
      if (report.frontendType === 'color_palette') {
        const token = wx.getStorageSync('token');
        this.loadColorCardBackground(this.data.rangeStartDate, this.data.rangeEndDate, token);
      }
    });
  },

  loadReportModule(module, token, startDate, endDate, eligibility) {
    const minTextChars = eligibility.min_text_chars || 20;
    const textCharCount = eligibility.text_char_count || 0;
    if (module.backendType === 'word-cloud' && textCharCount < minTextChars) {
      return Promise.resolve({
        ...module,
        skipped: true,
        skipMessage: `这段时间的文字总字数为 ${textCharCount} 字，少于 ${minTextChars} 字，无法进行文字分析。`
      });
    }

    return this.fetchApiData(`/api/v1/report/chart/range/${module.backendType}/${startDate}/${endDate}`, token)
      .then((chartRes) => ({
        ...module,
        chartData: chartRes.data,
        interpretation: chartRes.data.interpretation || '',
        aiReport: '',
        aiLoaded: false,
        aiLoading: false,
        aiError: false
      }))
      .catch((err) => ({
        ...module,
        error: true,
        skipMessage: err.errMsg || `${module.title}暂时无法生成。`
      }));
  },

  fetchApiData(url, token) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: API_BASE_URL + url,
        method: 'GET',
        header: { 'Authorization': `Bearer ${token}` },
        success: (res) => {
          if (res.statusCode >= 200 && res.statusCode < 300) { resolve(res); } 
          else { reject({ errMsg: this.formatApiError(res.data, res.statusCode) }); }
        },
        fail: (err) => { reject(err); }
      });
    });
  },

  formatApiError(data, statusCode) {
    const detail = data && data.detail;
    if (detail && typeof detail === 'object') {
      return detail.message || detail.code || `服务器错误 ${statusCode}`;
    }
    return detail || `服务器错误 ${statusCode}`;
  },

  showNotEnoughDataModal(eligibility) {
    const periodName = eligibility.period_name || '这个周期';
    const minDays = eligibility.min_days || 3;
    const reason = eligibility.reason || '';
    const content = reason === 'range_too_short'
      ? `心情分析需要选择至少连续${minDays}天。请把开始和结束日期拉开一点点。`
      : `您在${periodName}内还没有心情记录，暂时无法分析哦~\n先去留下几次此刻心情吧~`;
    wx.showModal({
      title: '还差一点点哦',
      content,
      confirmText: reason === 'range_too_short' ? '知道啦' : '去记录',
      showCancel: reason !== 'range_too_short',
      cancelText: '知道啦',
      success: (res) => {
        if (res.confirm && reason !== 'range_too_short') {
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

  loadColorCardBackground(startDate, endDate, token) {
    this.setData({
      isColorCardLoading: true,
      colorCardResult: null,
      colorCardError: ''
    });

    this.fetchApiData(`/api/v1/report/color-card/range/${startDate}/${endDate}`, token)
      .then((res) => {
        const payload = res.data || {};
        const imageResult = payload.image_result || {};
        this.setData({
          colorCardResult: {
            ...payload,
            imageUrl: this.normalizeAssetUrl(imageResult.background_image_url),
            isCached: !!imageResult.cached,
          },
          colorCardError: imageResult.background_image_url ? '' : (imageResult.error || 'AI 颜色背景图暂时生成失败')
        });
      })
      .catch((err) => {
        if (isVipQuotaExhaustedError(err)) {
          showVipQuotaModal({ error: err, feature: 'mood_analysis' });
        }
        this.setData({
          colorCardResult: null,
          colorCardError: isVipQuotaExhaustedError(err)
            ? ''
            : (err.errMsg || 'AI 颜色背景图暂时生成失败')
        });
      })
      .finally(() => {
        this.setData({ isColorCardLoading: false });
      });
  },

  previewColorCardImage() {
    const url = this.data.colorCardResult && this.data.colorCardResult.imageUrl;
    if (!url) return;
    wx.previewImage({ current: url, urls: [url] });
  },

  renderChart(type, data, chartId = 'analysis-chart') {
    const chartComponent = this.selectComponent(`#${chartId}`);
    if (!chartComponent) { return; }
    if (chartComponent.chart && typeof chartComponent.chart.dispose === 'function') {
      chartComponent.chart.dispose();
      chartComponent.chart = null;
    }
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
      animation: false,
      textStyle: {
        fontFamily: CHART_FONT_FAMILY,
        color: '#543522',
        fontWeight: 500
      },
      tooltip: { trigger: 'item', formatter: tooltipFormatter },
      legend: {
        top: '5%',
        left: 'center',
        textStyle: {
          fontFamily: CHART_FONT_FAMILY,
          color: '#543522',
          fontWeight: 500
        }
      },
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
      name: '心情频次',
      data: data.mood_distribution,
      tooltipFormatter: '{b}: {c}次 ({d}%)'
    });
  },

  getTagMoodChartOption(data) {
    return {
      animation: false,
      textStyle: {
        fontFamily: CHART_FONT_FAMILY,
        color: '#543522',
        fontWeight: 500
      },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: {
        data: data.chart_data.series.map(item => item.name),
        top: 5,
        textStyle: {
          fontFamily: CHART_FONT_FAMILY,
          color: '#543522',
          fontWeight: 500
        }
      },
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

  selectDayRange(e) {
    const days = Number(e.currentTarget.dataset.days);
    const range = this.buildDateRangeByDays(days);
    this.setData({
      selectedDayCount: days,
      selectedRangeDays: range.days,
      rangeStartDate: range.startDate,
      rangeEndDate: range.endDate,
      rangeLabel: this.formatRangeLabel(range.startDate, range.endDate)
    });
    this.resetAnalysisResult();
  },

  onStartDateChange(e) {
    const startDate = e.detail.value;
    let endDate = this.data.rangeEndDate;
    if (this.parseDate(startDate) > this.parseDate(endDate)) {
      endDate = startDate;
    }
    const days = this.getRangeDays(startDate, endDate);
    this.setData({
      selectedDayCount: 0,
      selectedRangeDays: days,
      rangeStartDate: startDate,
      rangeEndDate: endDate,
      rangeLabel: this.formatRangeLabel(startDate, endDate)
    });
    this.resetAnalysisResult();
  },

  onEndDateChange(e) {
    const endDate = e.detail.value;
    let startDate = this.data.rangeStartDate;
    if (this.parseDate(endDate) < this.parseDate(startDate)) {
      startDate = endDate;
    }
    const days = this.getRangeDays(startDate, endDate);
    this.setData({
      selectedDayCount: 0,
      selectedRangeDays: days,
      rangeStartDate: startDate,
      rangeEndDate: endDate,
      rangeLabel: this.formatRangeLabel(startDate, endDate)
    });
    this.resetAnalysisResult();
  },

  onShareAppMessage: function () {
    return getShareInfo();
  },

  onShareTimeline: function () {
    return getTimelineInfo();
  }
});
