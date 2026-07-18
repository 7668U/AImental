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
const BACKEND_ANALYSIS_TYPE_MAP = {
  mood: 'mood_distribution',
  'tag-mood': 'tag_correlation',
  'word-cloud': 'word_cloud',
  color: 'color_palette'
};
const MOOD_ANALYSIS_HISTORY_REPORT_KEY = 'mood_analysis_history_report';
const CHART_FONT_FAMILY = 'PingFang SC, Microsoft YaHei, Helvetica Neue, Arial, sans-serif';
const ANALYSIS_MODULES = [
  {
    frontendType: 'mood_distribution',
    backendType: 'mood',
    title: '心情频次',
    chartTitle: '心情频次总览',
    chartId: 'chart_mood_distribution',
    icon: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgDailyCheckin/images/analysis/report-mood-distribution.png'
  },
  {
    frontendType: 'tag_correlation',
    backendType: 'tag-mood',
    title: '状态关联',
    chartTitle: '状态关联总览',
    chartId: 'chart_tag_correlation',
    icon: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgDailyCheckin/images/analysis/report-status-correlation.png'
  },
  {
    frontendType: 'word_cloud',
    backendType: 'word-cloud',
    title: '文字分析',
    chartTitle: '文字分析总览',
    chartId: 'chart_word_cloud',
    icon: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgDailyCheckin/images/analysis/report-text-analysis.png'
  },
  {
    frontendType: 'color_palette',
    backendType: 'color',
    title: '情绪色卡',
    chartTitle: '情绪色卡总览',
    chartId: 'chart_color_palette',
    icon: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgDailyCheckin/images/analysis/report-color-card.png'
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
    isHistoryMode: false,
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
    isExporting: false,
    exportCanvasReady: false,
    exportCanvasWidth: 750,
    exportCanvasHeight: 1000,
    ec: {
      lazyLoad: true
    }
  },

  onLoad(options) {
    this.setNavSize();
    this.setData({
      isHistoryMode: options && options.from === 'history'
    });
    this.initDefaultPeriod(options || {});
  },
// --- 新增：为适配自定义导航栏新增的函数 ---
setNavSize() {
  const sysInfo = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
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
        maxDate: this.formatDate(this.getYesterday()),
        rangeLabel: this.formatRangeLabel(historyRange.startDate, historyRange.endDate),
        pendingAnalysisType: historyRange.frontendType || ''
      }, () => {
        this.setData({ isReady: true });
        if (this.data.isHistoryMode) {
          this.loadHistoryReport();
        }
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

  getYesterday() {
    const d = new Date();
    d.setDate(d.getDate() - 1);
    return d;
  },

  buildDateRangeByDays(days) {
    // 分析只到昨天为止：今天仍在进行中，不参与分析。
    const end = this.getYesterday();
    const start = this.getYesterday();
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

  async loadHistoryReport() {
    const historyReport = wx.getStorageSync(MOOD_ANALYSIS_HISTORY_REPORT_KEY);
    if (
      !historyReport ||
      historyReport.start_date !== this.data.rangeStartDate ||
      historyReport.end_date !== this.data.rangeEndDate
    ) {
      this.setData({ isLoading: false });
      wx.showToast({ title: '历史报告信息已失效', icon: 'none' });
      return;
    }

    const token = wx.getStorageSync('token');
    if (!token) {
      this.setData({ isLoading: false });
      wx.showToast({ title: '用户未登录', icon: 'none' });
      return;
    }

    this.setData({
      isLoading: true,
      analysisReports: [],
      activeReport: null,
      selectedAnalysis: '',
      isChartReady: false,
      colorCardResult: null,
    colorCardError: '',
    });

    try {
      let historyEligibility = {};
      try {
        const eligibilityRes = await this.fetchApiData(
          `/api/v1/report/eligibility/range/${this.data.rangeStartDate}/${this.data.rangeEndDate}`,
          token
        );
        historyEligibility = eligibilityRes.data || {};
      } catch (eligibilityError) {
        console.warn('history report eligibility unavailable:', eligibilityError);
      }

      const reports = await Promise.all(
        ANALYSIS_MODULES.map(async (module) => {
          const stored = (historyReport.reports || {})[module.frontendType];
          if (!stored) {
            return {
              ...module,
              error: true,
              skipMessage: '这份历史报告没有保存该分析模块。',
            };
          }

          if (
            module.backendType === 'word-cloud'
            && historyEligibility.can_word_analysis === false
          ) {
            return {
              ...module,
              chartData: null,
              chartUnavailable: true,
              interpretation: stored.summary_text || '',
              aiReport: stored.report_text || '',
              aiLoaded: true,
              aiLoading: false,
              aiError: false,
            };
          }

          try {
            const chartRes = await this.fetchApiData(
              `/api/v1/report/chart/range/${module.backendType}/${this.data.rangeStartDate}/${this.data.rangeEndDate}`,
              token
            );
            return {
              ...module,
              chartData: chartRes.data,
              interpretation: stored.summary_text || '',
              aiReport: stored.report_text || '',
              aiLoaded: true,
              aiLoading: false,
              aiError: false,
            };
          } catch (err) {
            return {
              ...module,
              interpretation: stored.summary_text || '',
              aiReport: stored.report_text || '',
              aiLoaded: true,
              aiLoading: false,
              aiError: false,
              chartData: null,
              chartError: true,
            };
          }
        })
      );

      this.setData({
        analysisReports: reports,
        activeReport: null,
        isChartReady: false,
        hasAnalyzed: true,
        isLoading: false,
      }, () => {
        wx.nextTick(() => {
          this.renderHistoryReportCharts(reports);
        });
        const colorReport = reports.find(item => (
          item.frontendType === 'color_palette' &&
          !item.error &&
          !item.skipped
        ));
        if (colorReport) {
          this.loadColorCardBackground(this.data.rangeStartDate, this.data.rangeEndDate, token);
        }
      });
    } catch (err) {
      console.error('加载历史分析报告失败:', err);
      this.setData({ isLoading: false });
      wx.showToast({ title: '历史报告加载失败', icon: 'none' });
    }
  },

  renderHistoryReportCharts(reports) {
    reports.forEach((report, index) => {
      if (!report.chartData || report.error || report.skipped) return;
      setTimeout(() => {
        this.renderChart(report.frontendType, report.chartData, report.chartId);
      }, index * 90);
    });
  },

  async exportHistoryReportImage() {
    if (!this.data.isHistoryMode || this.data.isExporting) return;
    const reports = this.data.analysisReports || [];
    if (!reports.length) {
      wx.showToast({ title: '报告还没有加载完成', icon: 'none' });
      return;
    }

    this.setData({ isExporting: true });
    wx.showLoading({ title: '正在生成长图...', mask: true });

    try {
      const chartImages = await this.captureHistoryChartImages(reports);
      const colorImageUrl = this.data.colorCardResult && this.data.colorCardResult.imageUrl;
      const colorImage = colorImageUrl
        ? await this.getExportImageInfo(colorImageUrl).catch(() => null)
        : null;
      const layout = this.buildHistoryExportLayout(reports, chartImages, colorImage);

      if (layout.height > 14000) {
        throw new Error('报告内容过长，暂时无法生成单张长图');
      }

      await new Promise((resolve) => {
        this.setData({
          exportCanvasReady: true,
          exportCanvasWidth: layout.width,
          exportCanvasHeight: layout.height,
        }, () => {
          wx.nextTick(() => setTimeout(resolve, 100));
        });
      });

      await this.drawHistoryExportCanvas(layout);
      const tempFilePath = await this.exportHistoryCanvas(layout);
      wx.hideLoading();
      await this.saveReportImageToAlbum(tempFilePath);
    } catch (error) {
      wx.hideLoading();
      console.error('导出心情分析报告失败:', error);
      wx.showToast({
        title: error.message || '报告图片生成失败',
        icon: 'none',
      });
    } finally {
      this.setData({
        isExporting: false,
        exportCanvasReady: false,
      });
    }
  },

  captureHistoryChartImages(reports) {
    const result = {};
    return Promise.all(
      reports.map((report) => {
        if (!report.chartData || report.error || report.skipped) {
          return Promise.resolve();
        }
        return this.captureChartImage(report.chartId)
          .then((path) => {
            if (path) result[report.frontendType] = path;
          })
          .catch(() => {});
      })
    ).then(() => result);
  },

  captureChartImage(chartId) {
    return new Promise((resolve, reject) => {
      const component = this.selectComponent(`#${chartId}`);
      if (!component || typeof component.canvasToTempFilePath !== 'function') {
        resolve('');
        return;
      }
      component.canvasToTempFilePath({
        fileType: 'png',
        quality: 1,
        success: (res) => resolve(res.tempFilePath || ''),
        fail: reject,
      });
    });
  },

  getExportImageInfo(src) {
    return new Promise((resolve, reject) => {
      wx.getImageInfo({
        src,
        success: (res) => resolve({
          path: res.path,
          width: res.width,
          height: res.height,
        }),
        fail: reject,
      });
    });
  },

  splitExportText(text, maxUnits = 27) {
    const source = String(text || '暂无内容').replace(/\r/g, '');
    const lines = [];
    source.split('\n').forEach((paragraph) => {
      if (!paragraph) {
        lines.push('');
        return;
      }
      let line = '';
      let units = 0;
      Array.from(paragraph).forEach((char) => {
        const charUnits = /[\x00-\xff]/.test(char) ? 0.56 : 1;
        if (line && units + charUnits > maxUnits) {
          lines.push(line);
          line = char;
          units = charUnits;
        } else {
          line += char;
          units += charUnits;
        }
      });
      if (line) lines.push(line);
    });
    return lines.length ? lines : ['暂无内容'];
  },

  buildHistoryExportLayout(reports, chartImages, colorImage) {
    const width = 750;
    const margin = 48;
    const contentWidth = width - margin * 2;
    let y = 52;
    const sections = [];

    y += 138;

    reports.forEach((report, index) => {
      const section = {
        report,
        index,
        headingY: y,
        chart: null,
        colorImage: null,
        cards: [],
      };
      y += 78;

      const chartPath = chartImages[report.frontendType];
      if (chartPath) {
        section.chart = {
          path: chartPath,
          x: margin,
          y,
          width: contentWidth,
          height: 410,
        };
        y += 434;
      }

      if (report.frontendType === 'color_palette' && colorImage && colorImage.path) {
        const imageWidth = 560;
        const imageHeight = Math.min(
          760,
          Math.max(360, Math.round(imageWidth * colorImage.height / colorImage.width))
        );
        section.colorImage = {
          ...colorImage,
          x: Math.round((width - imageWidth) / 2),
          y,
          width: imageWidth,
          height: imageHeight,
        };
        y += imageHeight + 24;
      }

      if (report.skipped || report.error) {
        const lines = this.splitExportText(report.skipMessage || '该模块暂时无法展示。');
        const height = 92 + lines.length * 38;
        section.cards.push({
          type: 'skip',
          title: report.title,
          lines,
          x: margin,
          y,
          width: contentWidth,
          height,
        });
        y += height + 26;
      } else {
        const interpretationLines = this.splitExportText(report.interpretation);
        const interpretationHeight = 98 + interpretationLines.length * 38;
        section.cards.push({
          type: 'interpretation',
          title: `${report.title}解读`,
          lines: interpretationLines,
          x: margin,
          y,
          width: contentWidth,
          height: interpretationHeight,
        });
        y += interpretationHeight + 22;

        const reportLines = this.splitExportText(report.aiReport);
        const reportHeight = 98 + reportLines.length * 38;
        section.cards.push({
          type: 'ai',
          title: `${report.title}报告`,
          lines: reportLines,
          x: margin,
          y,
          width: contentWidth,
          height: reportHeight,
        });
        y += reportHeight + 30;
      }

      sections.push(section);
      y += 30;
    });

    return {
      width,
      height: Math.ceil(y + 96),
      margin,
      contentWidth,
      sections,
    };
  },

  drawRoundedRect(ctx, x, y, width, height, radius, fillColor, strokeColor) {
    const r = Math.min(radius, width / 2, height / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + width - r, y);
    ctx.arcTo(x + width, y, x + width, y + r, r);
    ctx.lineTo(x + width, y + height - r);
    ctx.arcTo(x + width, y + height, x + width - r, y + height, r);
    ctx.lineTo(x + r, y + height);
    ctx.arcTo(x, y + height, x, y + height - r, r);
    ctx.lineTo(x, y + r);
    ctx.arcTo(x, y, x + r, y, r);
    ctx.closePath();
    if (fillColor) {
      ctx.setFillStyle(fillColor);
      ctx.fill();
    }
    if (strokeColor) {
      ctx.setStrokeStyle(strokeColor);
      ctx.setLineWidth(2);
      ctx.stroke();
    }
  },

  drawExportTextLines(ctx, lines, x, y, lineHeight) {
    lines.forEach((line, index) => {
      ctx.fillText(line || ' ', x, y + index * lineHeight);
    });
  },

  drawHistoryExportCanvas(layout) {
    return new Promise((resolve) => {
      const ctx = wx.createCanvasContext('history-report-export');
      const headerGradient = ctx.createLinearGradient(0, 0, layout.width, 190);
      headerGradient.addColorStop(0, '#ffd993');
      headerGradient.addColorStop(0.5, '#fff0cf');
      headerGradient.addColorStop(1, '#ffc978');

      ctx.setFillStyle('#fff8ed');
      ctx.fillRect(0, 0, layout.width, layout.height);
      ctx.setFillStyle(headerGradient);
      ctx.fillRect(0, 0, layout.width, 190);

      ctx.setTextAlign('center');
      ctx.setTextBaseline('top');
      ctx.setFillStyle('#5b3421');
      ctx.setFontSize(42);
      ctx.fillText('心情分析报告', layout.width / 2, 50);
      ctx.setFillStyle('#8b634d');
      ctx.setFontSize(25);
      ctx.fillText(
        `${this.data.rangeStartDate} 至 ${this.data.rangeEndDate}`,
        layout.width / 2,
        112
      );

      layout.sections.forEach((section) => {
        const report = section.report;
        const badgeX = layout.margin + 24;
        const badgeY = section.headingY + 8;
        ctx.setFillStyle('#ff8b2b');
        ctx.beginPath();
        ctx.arc(badgeX, badgeY + 19, 19, 0, Math.PI * 2);
        ctx.fill();
        ctx.setFillStyle('#ffffff');
        ctx.setFontSize(22);
        ctx.setTextAlign('center');
        ctx.fillText(String(section.index + 1), badgeX, badgeY + 7);

        ctx.setTextAlign('left');
        ctx.setFillStyle('#543522');
        ctx.setFontSize(33);
        ctx.fillText(report.title, badgeX + 38, section.headingY + 8);

        if (section.chart) {
          this.drawRoundedRect(
            ctx,
            section.chart.x,
            section.chart.y,
            section.chart.width,
            section.chart.height,
            24,
            '#fffdf9',
            '#f0dcc5'
          );
          ctx.drawImage(
            section.chart.path,
            section.chart.x + 16,
            section.chart.y + 16,
            section.chart.width - 32,
            section.chart.height - 32
          );
        }

        if (section.colorImage) {
          this.drawRoundedRect(
            ctx,
            section.colorImage.x - 8,
            section.colorImage.y - 8,
            section.colorImage.width + 16,
            section.colorImage.height + 16,
            24,
            '#fffdf9',
            '#f0dcc5'
          );
          ctx.drawImage(
            section.colorImage.path,
            section.colorImage.x,
            section.colorImage.y,
            section.colorImage.width,
            section.colorImage.height
          );
        }

        section.cards.forEach((card) => {
          const fillColor = card.type === 'ai' ? '#fff3df' : '#fffdf9';
          this.drawRoundedRect(
            ctx,
            card.x,
            card.y,
            card.width,
            card.height,
            24,
            fillColor,
            '#f0dcc5'
          );
          ctx.setTextAlign('left');
          ctx.setFillStyle('#543522');
          ctx.setFontSize(28);
          ctx.fillText(card.title, card.x + 28, card.y + 24);
          ctx.setFillStyle('#6b5143');
          ctx.setFontSize(24);
          this.drawExportTextLines(ctx, card.lines, card.x + 28, card.y + 70, 38);
        });
      });

      ctx.setTextAlign('center');
      ctx.setFillStyle('#b1886c');
      ctx.setFontSize(22);
      ctx.fillText('Feel Yourself · 心情日记', layout.width / 2, layout.height - 56);
      ctx.draw(false, () => setTimeout(resolve, 120));
    });
  },

  exportHistoryCanvas(layout) {
    return new Promise((resolve, reject) => {
      wx.canvasToTempFilePath({
        canvasId: 'history-report-export',
        x: 0,
        y: 0,
        width: layout.width,
        height: layout.height,
        destWidth: layout.width,
        destHeight: layout.height,
        fileType: 'jpg',
        quality: 0.94,
        success: (res) => resolve(res.tempFilePath),
        fail: reject,
      });
    });
  },

  saveReportImageToAlbum(filePath) {
    return new Promise((resolve) => {
      wx.saveImageToPhotosAlbum({
        filePath,
        success: () => {
          wx.showToast({ title: '报告已保存到相册', icon: 'success' });
          resolve(true);
        },
        fail: (error) => {
          const message = String(error && error.errMsg || '');
          if (message.includes('auth deny') || message.includes('auth denied')) {
            wx.showModal({
              title: '需要相册权限',
              content: '请在设置中允许保存图片到相册。',
              confirmText: '去设置',
              success: (res) => {
                if (res.confirm) wx.openSetting();
                resolve(false);
              },
            });
            return;
          }
          wx.previewImage({
            current: filePath,
            urls: [filePath],
            complete: () => resolve(false),
          });
          wx.showToast({ title: '可长按图片保存', icon: 'none' });
        },
      });
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
    const yesterday = this.formatDate(this.getYesterday());
    let startDate = e.detail.value;
    // 分析只到昨天为止，开始日期不能晚于昨天。
    if (this.parseDate(startDate) > this.parseDate(yesterday)) {
      startDate = yesterday;
    }
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
    const yesterday = this.formatDate(this.getYesterday());
    let endDate = e.detail.value;
    // 分析只到昨天为止，结束日期不能晚于昨天。
    if (this.parseDate(endDate) > this.parseDate(yesterday)) {
      endDate = yesterday;
      wx.showToast({ title: '只能分析今天之前的记录', icon: 'none' });
    }
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
