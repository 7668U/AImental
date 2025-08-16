// pages/profile/history_analysis.js
const { getShareInfo, getTimelineInfo } = require('../../utils/share.js');
import * as echarts from '../daily-checkin/components/ec-canvas/echarts';

let chart = null;

function initChart(canvas, width, height, dpr) {
  chart = echarts.init(canvas, null, {
    width: width,
    height: height,
    devicePixelRatio: dpr
  });
  canvas.setChart(chart);
  return chart;
}

Page({
  data: {
    scaleName: '分析报告',
    isLoadingReport: false,
    currentScaleRecords: [],
    analysisReport: {},
    ec: {
      onInit: initChart
    }
  },

  onLoad(options) {
    const id = options.id;
    // 伪造一些数据用于展示
    this.setData({
      analysisId: id,
      report: {
        title: "关于近期情绪波动的深度分析",
        date: "2023年10月27日",
        summary: "报告显示，您近期的情绪状态整体稳定，但存在轻微的焦虑迹象，主要与工作压力和睡眠质量有关。积极情绪如“开心”和“放松”占据主导，但“疲惫”和“迷茫”也频繁出现。",
        suggestions: [
          "建议增加晚间放松活动，如冥想或阅读，以改善睡眠。",
          "尝试将大型工作任务分解为更小的部分，减轻压力感。",
          "与朋友或家人沟通，分享您的感受，有助于缓解焦虑情绪。"
        ]
      }
    });
  },

  onShareAppMessage: function () {
    return getShareInfo();
  },

  onShareTimeline: function () {
    return getTimelineInfo();
  }
});