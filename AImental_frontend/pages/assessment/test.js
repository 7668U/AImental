// pages/assessment/test.js (兼容版)

const API_BASE_URL = 'http://127.0.0.1:8000';

Page({
  data: {
    scaleId: null,
    scaleData: null, // 将在这里存储完整的量表信息，包括 assessment_type
    questions: [],
    totalQuestions: 0,
    currentIndex: 0,
    progress: 0,
    answers: {},
    isSubmitting: false,
    answeredCount: 0,
  },

  onLoad(options) {
    if (options.id) {
      this.setData({ scaleId: options.id });
      this.fetchScaleData(options.id);
    } else {
      wx.showToast({ title: '参数错误', icon: 'error' });
      setTimeout(() => wx.navigateBack(), 1500);
    }
  },

  fetchScaleData(scaleId) {
    wx.showLoading({ title: '加载中...' });
    wx.request({
      url: `${API_BASE_URL}/api/v1/assessments/${scaleId}`,
      method: 'GET',
      header: {
        'Authorization': `Bearer ${wx.getStorageSync('token')}`
      },
      success: (res) => {
        if (res.statusCode === 200) {
          const scaleData = res.data;
          const jsonData = scaleData.json_data || {};
          let questions = jsonData.questions || [];
          const commonChoices = jsonData.choices;

          // 这个处理逻辑非常棒，它确保了无论是哪种测试，选项数组的字段名都统一为 'choices'
          questions = questions.map(question => {
            if (question.options && question.options.length > 0) {
              question.choices = question.options;
              delete question.options;
            }
            if ((!question.choices || question.choices.length === 0) && commonChoices) {
              return { ...question, choices: commonChoices };
            }
            return question;
          });
          
          this.setData({
            scaleData: scaleData, // 存储完整数据，供 WXML 判断类型
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

  onRadioChange(e) {
    const questionOrder = e.currentTarget.dataset.order;
    // ✅ 【核心修正】
    // 直接获取 e.detail.value，它就是我们在 WXML 中绑定的 <radio> 的 value
    // 无论是 'scoring' 的分数(如"3")，还是 'categorical' 的ID(如"A")，都作为字符串处理
    const selectedValue = e.detail.value;
    
    // 检查一下确保拿到了有效值
    if (selectedValue === undefined || selectedValue === null) {
        console.error("获取选项值失败，请检查WXML中radio的value绑定。");
        return;
    }

    this.setData({
      [`answers.${questionOrder}`]: selectedValue
    });

    this.updateProgress();

    setTimeout(() => {
      if (this.data.currentIndex < this.data.totalQuestions - 1) {
        this.setData({ currentIndex: this.data.currentIndex + 1 });
      }
    }, 200);
  },
  
  updateProgress() {
    // 修正：确保答案不为空值时才计数
    const answeredCount = Object.values(this.data.answers).filter(v => v !== '' && v !== null && v !== undefined).length;
    const progress = this.data.totalQuestions > 0 ? (answeredCount / this.data.totalQuestions) * 100 : 0;
    this.setData({ 
      progress: progress,
      answeredCount: answeredCount
    });
  },

  onSwiperChange(e) {
    if (e.detail.source === 'touch') {
      const newIndex = e.detail.current;
      const oldIndex = this.data.currentIndex;

      if (newIndex > oldIndex) {
        const currentQuestionOrder = this.data.questions[oldIndex].order;
        if (!this.data.answers.hasOwnProperty(currentQuestionOrder) || this.data.answers[currentQuestionOrder] === '') {
          wx.showToast({
            title: '请先回答当前题目',
            icon: 'none'
          });
          this.setData({ currentIndex: oldIndex });
          return;
        }
      }
      this.setData({ currentIndex: newIndex });
    }
  },

  prevQuestion() {
    if (this.data.currentIndex > 0) {
      this.setData({ currentIndex: this.data.currentIndex - 1 });
    }
  },

  nextQuestion() {
    const currentQuestionOrder = this.data.questions[this.data.currentIndex].order;
    if (this.data.answers.hasOwnProperty(currentQuestionOrder) && this.data.answers[currentQuestionOrder] !== '') {
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
          let errorMsg = '未知错误';
          if (res.data && res.data.detail) {
            if (Array.isArray(res.data.detail)) {
              errorMsg = res.data.detail.map(d => d.msg).join('; ');
            } else {
              errorMsg = res.data.detail;
            }
          }
          wx.showToast({ title: `提交失败: ${errorMsg}`, icon: 'none', duration: 3000 });
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