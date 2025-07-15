// pages/profile/history_analysis.js
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
    const eventChannel = this.getOpenerEventChannel();
    eventChannel.on('acceptDataFromHistoryPage', (data) => {
      console.log('接收到的数据:', data);

      const { groupData, reportData } = data;
      
      const formattedRecords = groupData.records.map(r => ({
        ...r,
        completed_at_formatted: r.completed_at_formatted || this.formatDate(r.completed_at)
      }));

      this.setData({
        scaleName: groupData.scale_name,
        currentScaleRecords: formattedRecords,
        analysisReport: reportData
      });

      wx.setNavigationBarTitle({
        title: `${groupData.scale_name}分析报告`
      });

      // ✅ 【核心修正 ①】: 删除错误的 .selectComponent().exec() 调用
      // ECharts的 onInit 机制已经确保了 chart 实例存在。
      // 我们只需要直接调用 setupChart 函数来设置数据即可。
      // 为确保万无一失，可以在调用前检查一下chart实例是否存在。
      if (chart) {
        this.setupChart(formattedRecords);
      } else {
        // 如果 chart 还未初始化，可以稍微延迟一下再试
        // 这种情况很少见，但可以增加代码健壮性
        setTimeout(() => {
          this.setupChart(formattedRecords);
        }, 300);
      }
    });
  },
  
  setupChart(records) {
    if (!chart || !records || records.length === 0) {
      console.warn("图表初始化失败：无有效chart实例或数据为空");
      return;
    }
    const reversedRecords = records.slice().reverse();
    const chartLabels = reversedRecords.map(r => this.formatDateForChart(r.completed_at));
    const chartData = reversedRecords.map(r => r.final_score);

    const option = {
      tooltip: { trigger: 'axis' },
      grid: { left: '12%', right: '10%', bottom: '15%', containLabel: true },
      xAxis: { type: 'category', data: chartLabels, boundaryGap: false },
      yAxis: { type: 'value', name: '得分' },
      series: [{
        name: '分数',
        type: 'line',
        smooth: true,
        data: chartData,
        itemStyle: { color: '#F7931E' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{
            offset: 0,
            color: 'rgba(247, 147, 30, 0.3)'
          }, {
            offset: 1,
            color: 'rgba(247, 147, 30, 0)'
          }])
        }
      }]
    };
    chart.setOption(option, true);
  },

  handleConfirm() {
    wx.navigateBack();
  },

  formatDate(dateStr) {
    return new Date(dateStr).toLocaleString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' });
  },

  // ✅ 【核心修正 ②】: 调整日期格式以满足 "年.月.日" 的要求
  formatDateForChart(dateStr) {
    const d = new Date(dateStr);
    const year = d.getFullYear();
    const month = d.getMonth() + 1; // 月份是从0开始的，所以要+1
    const day = d.getDate();
    return `${year}.${month}.${day}`;
  },
  onUnload() {
    // We comment out or remove the chart.dispose() call to avoid the
    // compatibility error with the Mini Program's environment.
    // The Mini Program will handle memory cleanup when the page is destroyed.
    chart = null;
  }
});