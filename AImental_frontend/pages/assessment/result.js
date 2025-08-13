// pages/assessment/result/result.js (渐变条 + 文字标签最终版)

const SERVER_BASE_URL = 'http://127.0.0.1:8000';
const ASSESSMENTS_API_URL = `${SERVER_BASE_URL}/api/v1/assessments`;

Page({
  data: {
    isLoading: true,
    source: '',
    result: null,
    totalScore: 0,
    scoreSegments: [], // ✅ 【已加回】重新启用此数据，用于生成文字标签
    pointerPosition: 0,
    pointerLabelAlign: 'center',
    scoreMarkers: [],
  },

  onLoad(options) {
    if (options.from) {
      this.setData({ source: options.from });
    }

    if (options.record_id) {
      this.fetchResultById(options.record_id);
    } else if (options.data) {
      try {
        const resultData = JSON.parse(decodeURIComponent(options.data));
        this.processAndRender(resultData);
      } catch (e) {
        console.error("解析初次结果数据失败", e);
        this.showErrorAndGoBack('结果加载失败');
      }
    } else {
      this.showErrorAndGoBack('无效的访问');
    }
  },

  fetchResultById(recordId) {
    wx.request({
      url: `${ASSESSMENTS_API_URL}/history/${recordId}`,
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
      success: (res) => {
        if (res.statusCode === 200) {
          this.processAndRender(res.data);
        } else {
          console.error("获取历史详情失败", res);
          this.showErrorAndGoBack('加载历史详情失败');
        }
      },
      fail: (err) => {
        console.error("请求历史详情失败", err);
        this.showErrorAndGoBack('网络请求失败');
      }
    });
  },
  
  processAndRender(resultData) {
    this.setData({ result: resultData });
    
    const type = resultData?.scale_details?.assessment_type;

    if (type === 'scoring') {
      const jsonData = resultData.scale_details.json_data;
      const interpretations = jsonData.interpretations || [];
      
      if (interpretations.length === 0) {
        this.showErrorAndGoBack('问卷分数段未定义');
        return;
      }

      const userScore = resultData.final_score;
      
      const minPossibleScore = interpretations[0].min_score;
      const maxPossibleScore = interpretations[interpretations.length - 1].max_score;
      const totalScorableRange = maxPossibleScore - minPossibleScore;

      if (totalScorableRange <= 0) {
        this.showErrorAndGoBack('问卷分数范围无效');
        return;
      }
      
      // ✅ 【核心修改已集成】重新计算 scoreSegments 用于生成文字标签
      const scoreSegments = interpretations.map((interp, index) => {
        const prevMaxScore = index === 0 ? minPossibleScore : interpretations[index - 1].max_score;
        const width = ((interp.max_score - prevMaxScore) / totalScorableRange) * 100;
        // color 属性虽然不用，但保留也无妨
        return {
          level: interp.level,
          width: width,
          color: 'transparent' // 颜色不再重要
        };
      });

      const pointerPosition = ((userScore - minPossibleScore) / totalScorableRange) * 100;

      let pointerLabelAlign = 'center';
      if (pointerPosition > 85) pointerLabelAlign = 'left';
      else if (pointerPosition < 15) pointerLabelAlign = 'right';

      const scoreMarkers = [];
      for (let i = 0; i < interpretations.length - 1; i++) {
        const interp = interpretations[i];
        scoreMarkers.push({
          score: interp.max_score,
          position: ((interp.max_score - minPossibleScore) / totalScorableRange) * 100
        });
      }

      this.setData({
        totalScore: maxPossibleScore,
        scoreSegments: scoreSegments, // ✅ 【已加回】将计算好的标签数据传给WXML
        pointerPosition: pointerPosition,
        pointerLabelAlign: pointerLabelAlign,
        scoreMarkers: scoreMarkers,
        isLoading: false
      });

    } else if (type === 'categorical') {
      this.setData({
        isLoading: false
      });
    } else {
      console.error("无法识别的结果类型", resultData);
      this.showErrorAndGoBack('结果类型无法识别');
    }
  },

  handleConfirm() {
    if (this.data.source === 'history') {
      wx.navigateBack();
    } else {
      wx.reLaunch({
        url: '/pages/assessment/index'
      });
    }
  },

  showErrorAndGoBack(title) {
    wx.showToast({
      title: title,
      icon: 'error',
      duration: 2000
    });
    
    setTimeout(() => {
      if (getCurrentPages().length > 1) {
        wx.navigateBack();
      } else {
        wx.reLaunch({
          url: '/pages/assessment/index'
        });
      }
    }, 2000);
  }
});