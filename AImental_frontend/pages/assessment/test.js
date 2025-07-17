// pages/assessment/test.js

const API_BASE_URL = 'https://api.feelyourself.cn';

Page({
  data: {
    scaleId: null,
    scaleData: null,
    questions: [],
    totalQuestions: 0,
    currentIndex: 0,
    progress: 0,
    answers: {},
    isSubmitting: false,
    answeredCount: 0, // 用于精确追踪已答题数量
  },

  /**
   * 页面加载
   */
  onLoad(options) {
    if (options.id) {
      this.setData({ scaleId: options.id });
      this.fetchScaleData(options.id);
    } else {
      wx.showToast({ title: '参数错误', icon: 'error' });
      setTimeout(() => wx.navigateBack(), 1500);
    }
  },

  /**
   * 从后端API获取测评问卷数据 (最终修正版)
   * 能够同时处理“自带选项的问题”和“使用公共选项模板的问题”
   */
  fetchScaleData(scaleId) {
    wx.showLoading({ title: '加载中...' });
    wx.request({
      url: `${API_BASE_URL}/api/v1/assessments/${scaleId}`,
      method: 'GET',
      success: (res) => {
        if (res.statusCode === 200) {
          // res.data 的结构是 { id: '...', name: '...', json_data: { ... } }
          const scaleData = res.data;
          
          // 1. 直接获取已经由后端解析好的 json_data 对象
          const jsonData = scaleData.json_data || {};
          
          // 2.【关键逻辑】处理问题和选项
          let questions = jsonData.questions || [];
          // 尝试从 json_data 的顶层获取公共选项模板
          const commonChoices = jsonData.choices; 

          // 检查是否存在共用选项模板
          if (commonChoices && commonChoices.length > 0) {
            // 遍历所有问题，为那些没有自带选项的问题“嫁接”上共用的选项
            questions = questions.map(question => {
              if (!question.choices || question.choices.length === 0) {
                return {
                  ...question,          // 保留问题原有的 text, order 等信息
                  choices: commonChoices // 将公共选项模板赋给它
                };
              }
              // 如果问题本身有选项，则优先使用它自己的
              return question;
            });
          }
          
          // 3. 将处理好的、确保带有选项的 questions 数组设置到页面
          this.setData({
            scaleData: scaleData,
            questions: questions,
            totalQuestions: questions.length,
          });
          this.updateProgress();
          
        } else {
          wx.showToast({ title: `加载失败: ${res.statusCode}`, icon: 'error' });
        }
      },
      fail: (err) => {
        wx.showToast({ title: '网络请求失败', icon: 'error' });
        console.error("fetchScaleData failed:", err);
      },
      complete: () => {
        wx.hideLoading();
      }
    });
  },

  /**
   * 用户选择选项时的处理函数
   */
  onRadioChange(e) {
    const questionOrder = e.currentTarget.dataset.order;
    const optionScore = Number(e.detail.value);
    
    // 更新答案
    this.setData({
      [`answers.${questionOrder}`]: optionScore
    });

    // 答题后立刻更新进度和已答题数
    this.updateProgress();

    // 自动跳转到下一题
    setTimeout(() => {
      if (this.data.currentIndex < this.data.totalQuestions - 1) {
        this.setData({ currentIndex: this.data.currentIndex + 1 });
      }
    }, 200);
  },
  
  /**
   * 更新进度条
   */
  updateProgress() {
    const answeredCount = Object.keys(this.data.answers).length;
    const progress = this.data.totalQuestions > 0 ? (answeredCount / this.data.totalQuestions) * 100 : 0;
    this.setData({ 
      progress: progress,
      answeredCount: answeredCount
    });
  },

  /**
   * Swiper切换时更新当前页码
   */
  onSwiperChange(e) {
    if(e.detail.source === 'touch'){
      this.setData({ currentIndex: e.detail.current });
    }
  },

  /**
   * 点击“上一题”
   */
  prevQuestion() {
    if (this.data.currentIndex > 0) {
      this.setData({ currentIndex: this.data.currentIndex - 1 });
    }
  },

  /**
   * 点击“下一题”
   */
  nextQuestion() {
    if (this.data.answers.hasOwnProperty(this.data.questions[this.data.currentIndex].order)) {
      if (this.data.currentIndex < this.data.totalQuestions - 1) {
        this.setData({ currentIndex: this.data.currentIndex + 1 });
      }
    } else {
      wx.showToast({
        title: '请先回答当前题目',
        icon: 'none'
      });
    }
  },

  /**
   * 提交测评
   */
  submitAssessment() {
    if (this.data.isSubmitting) return;

    if (this.data.answeredCount < this.data.totalQuestions) {
      wx.showToast({
        title: '您还有题目未完成',
        icon: 'none'
      });
      return;
    }
    
    this.setData({ isSubmitting: true });

    // 【关键修正】将读取的键名从 'access_token' 改为 'token'
    const token = wx.getStorageSync('token');
    
    if (!token) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      this.setData({ isSubmitting: false });
      return;
    }

    const requestData = {
      scale_id: this.data.scaleId,
      answers: this.data.answers,
    };

    wx.request({
      url: `${API_BASE_URL}/api/v1/assessments/submit`,
      method: 'POST',
      header: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      data: requestData,
      success: (res) => {
        if (res.statusCode === 200) {
          const resultData = JSON.stringify(res.data);
          wx.redirectTo({
            url: `./result?data=${encodeURIComponent(resultData)}`,
          });
        } else {
          wx.showToast({ title: `提交失败: ${res.data.detail || '未知错误'}`, icon: 'none' });
        }
      },
      fail: (err) => {
        wx.showToast({ title: '网络请求失败', icon: 'error' });
      },
      complete: () => {
        this.setData({ isSubmitting: false });
      }
    });
  }
});
