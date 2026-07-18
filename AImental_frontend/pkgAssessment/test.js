const { getShareInfo, getTimelineInfo } = require('../utils/share.js');
const {
  confirmPrivacyAwareLogin,
  loginWithBackend,
  rejectPrivacyAwareLogin,
  requestPrivacyAwareLogin
} = require('../utils/auth.js');
// pages/assessment/test.js (兼容版)

const API_BASE_URL = 'https://api.feelyourself.cn';

function hasAnswerValue(value) {
  return value !== '' && value !== null && value !== undefined;
}

function isScorePlaceholder(text) {
  return /^\s*-?\d+分选项\s*$/.test(String(text || ''));
}

function splitQuestionTextOptions(text, expectedCount) {
  const parts = String(text || '')
    .split(/\s*[\/／]\s*/)
    .map(part => part.trim())
    .filter(Boolean);

  if (parts.length < expectedCount) {
    return null;
  }

  const optionTexts = parts.slice(-expectedCount);
  if (optionTexts.some(part => isScorePlaceholder(part))) {
    return null;
  }

  return {
    text: parts.length === expectedCount
      ? '请选择最符合你最近两周状态的一项'
      : parts.slice(0, -expectedCount).join(' / '),
    optionTexts,
  };
}

function normalizeQuestion(question, commonChoices) {
  const normalized = { ...question };
  let choices = [];

  if (Array.isArray(normalized.options) && normalized.options.length > 0) {
    choices = normalized.options;
    delete normalized.options;
  } else if (Array.isArray(normalized.choices) && normalized.choices.length > 0) {
    choices = normalized.choices;
  } else if (Array.isArray(commonChoices)) {
    choices = commonChoices;
  }

  choices = choices.map(choice => ({ ...choice }));

  if (choices.length > 0 && choices.every(choice => isScorePlaceholder(choice.text))) {
    const splitResult = splitQuestionTextOptions(normalized.text, choices.length);
    if (splitResult) {
      normalized.text = splitResult.text;
      choices = choices.map((choice, index) => ({
        ...choice,
        text: splitResult.optionTexts[index],
      }));
    }
  }

  normalized.choices = choices;
  return normalized;
}

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
    statusBarHeight: 0,
    navBarHeight: 56,
    isAnswerCardOpen: false,
    answerCardItems: [],
    privacyVisible: false,
  },

  onLoad(options) {
    this.setupNavBar();
    if (options.id) {
      this.setData({ scaleId: options.id });
      this.fetchScaleData(options.id);
    } else {
      wx.showToast({ title: '参数错误', icon: 'error' });
      setTimeout(() => wx.navigateBack(), 1500);
    }
  },

  setupNavBar() {
    try {
      const windowInfo = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
      const menuButtonInfo = wx.getMenuButtonBoundingClientRect();
      const statusBarHeight = windowInfo.statusBarHeight || 0;
      const navBarHeight = (menuButtonInfo.top - statusBarHeight) * 2 + menuButtonInfo.height;
      this.setData({ statusBarHeight, navBarHeight });
    } catch (err) {
      this.setData({ statusBarHeight: 24, navBarHeight: 56 });
    }
  },

  goBack() {
    wx.navigateBack();
  },

  fetchScaleData(scaleId) {
    wx.showLoading({ title: '加载中...' });
    const token = wx.getStorageSync('token');
    const header = {};
    if (token) {
      header.Authorization = `Bearer ${token}`;
    }

    wx.request({
      url: `${API_BASE_URL}/api/v1/assessments/${scaleId}`,
      method: 'GET',
      header,
      success: (res) => {
        console.log('API 原始响应:', res); 
        
        if (res.statusCode === 200) {

          // --- 变量只在这里声明一次 ---
          const scaleData = res.data;
          // const jsonData = scaleData.json_data || {};
          let questions = scaleData.questions || [];   
          const commonChoices = scaleData.choices || []; // 同样，直接从 scaleData 获取 choices
          // --------------------------



          questions = questions.map(question => normalizeQuestion(question, commonChoices));
          
          this.setData({
            scaleData: scaleData, // 存储完整数据，供 WXML 判断类型
            questions: questions,
            totalQuestions: questions.length,
          });
          this.syncAnswerState();
          
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
    }, () => {
      this.syncAnswerState();

      setTimeout(() => {
        if (this.data.currentIndex < this.data.totalQuestions - 1) {
          this.navigateToQuestion(this.data.currentIndex + 1, {
            showBlockedToast: true
          });
        }
      }, 200);
    });
  },
  
  isQuestionAnswered(order) {
    return hasAnswerValue(this.data.answers[order]);
  },

  findFirstUnansweredIndexBefore(targetIndex) {
    const maxIndex = Math.min(Math.max(targetIndex, 0), this.data.questions.length);

    for (let index = 0; index < maxIndex; index += 1) {
      const question = this.data.questions[index];
      if (question && !this.isQuestionAnswered(question.order)) {
        return index;
      }
    }

    return -1;
  },

  showUnansweredQuestionToast(index) {
    const question = this.data.questions[index];
    const questionLabel = question ? `第${question.order}题` : '当前题目';
    wx.showToast({
      title: `请先回答${questionLabel}`,
      icon: 'none'
    });
  },

  syncAnswerState(extraData = {}) {
    const currentIndex = Object.prototype.hasOwnProperty.call(extraData, 'currentIndex')
      ? extraData.currentIndex
      : this.data.currentIndex;
    const answeredCount = Object.values(this.data.answers).filter(value => hasAnswerValue(value)).length;
    const progress = this.data.totalQuestions > 0 ? (answeredCount / this.data.totalQuestions) * 100 : 0;
    const answerCardItems = this.data.questions.map((question, index) => ({
      order: question.order,
      index,
      answered: this.isQuestionAnswered(question.order),
      current: index === currentIndex,
    }));

    this.setData({
      progress,
      answeredCount,
      answerCardItems,
      ...extraData,
    });
  },

  navigateToQuestion(targetIndex, options = {}) {
    const {
      closeAnswerCard = false,
      showBlockedToast = true,
    } = options;

    if (!this.data.totalQuestions) {
      return;
    }

    const safeIndex = Math.max(0, Math.min(targetIndex, this.data.totalQuestions - 1));
    let nextIndex = safeIndex;

    if (safeIndex > this.data.currentIndex) {
      const blockedIndex = this.findFirstUnansweredIndexBefore(safeIndex);
      if (blockedIndex !== -1) {
        nextIndex = blockedIndex;
        if (showBlockedToast) {
          this.showUnansweredQuestionToast(blockedIndex);
        }
      }
    }

    this.syncAnswerState({
      currentIndex: nextIndex,
      ...(closeAnswerCard ? { isAnswerCardOpen: false } : {}),
    });
  },

  onSwiperChange(e) {
    if (e.detail.source === 'touch') {
      const newIndex = e.detail.current;
      if (newIndex !== this.data.currentIndex) {
        this.navigateToQuestion(newIndex, {
          showBlockedToast: true
        });
      }
    }
  },

  prevQuestion() {
    if (this.data.currentIndex > 0) {
      this.navigateToQuestion(this.data.currentIndex - 1, {
        showBlockedToast: false
      });
    }
  },

  nextQuestion() {
    const currentQuestionOrder = this.data.questions[this.data.currentIndex].order;
    if (this.isQuestionAnswered(currentQuestionOrder)) {
      if (this.data.currentIndex < this.data.totalQuestions - 1) {
        this.navigateToQuestion(this.data.currentIndex + 1, {
          showBlockedToast: true
        });
      } else {
        this.submitAssessment();
      }
    } else {
      this.showUnansweredQuestionToast(this.data.currentIndex);
    }
  },

  toggleAnswerCard() {
    this.setData({
      isAnswerCardOpen: !this.data.isAnswerCardOpen
    });
  },

  goToQuestionFromCard(e) {
    const targetIndex = Number(e.currentTarget.dataset.index);
    if (Number.isNaN(targetIndex)) {
      return;
    }

    this.navigateToQuestion(targetIndex, {
      closeAnswerCard: true,
      showBlockedToast: true
    });
  },

  promptLoginForResult() {
    wx.showModal({
      title: '登录后查看结果',
      content: '测评可以先体验，登录后就能生成并保存你的个人结果。',
      confirmText: '去登录',
      cancelText: '先逛逛',
      confirmColor: '#ff6b16',
      success: (res) => {
        if (res.confirm) {
          this.handleLogin();
        }
      }
    });
  },

  handleLogin() {
    return requestPrivacyAwareLogin(this, this.loginAndSubmitAssessment);
  },

  async loginAndSubmitAssessment() {
    wx.showLoading({ title: '登录中...' });
    try {
      const tokenRes = await loginWithBackend(`${API_BASE_URL}/api/v1`);
      if (!tokenRes || !tokenRes.access_token) {
        throw new Error('登录接口未返回 token');
      }

      wx.setStorageSync('token', tokenRes.access_token);
      wx.hideLoading();
      wx.showToast({ title: '登录成功', icon: 'success' });
      this.submitAssessment();
    } catch (error) {
      wx.hideLoading();
      console.error('测评提交前登录失败:', error);
      wx.showToast({ title: '登录失败，请重试', icon: 'none' });
    }
  },

  onPrivacyConfirm() {
    return confirmPrivacyAwareLogin(this);
  },

  onPrivacyReject() {
    rejectPrivacyAwareLogin(this);
  },

  submitAssessment() {
    if (this.data.isSubmitting) return;

    if (this.data.answeredCount < this.data.totalQuestions) {
      const firstUnansweredIndex = this.findFirstUnansweredIndexBefore(this.data.totalQuestions);
      if (firstUnansweredIndex !== -1) {
        this.syncAnswerState({
          currentIndex: firstUnansweredIndex
        });
        this.showUnansweredQuestionToast(firstUnansweredIndex);
      } else {
        wx.showToast({
          title: '您还有题目未完成',
          icon: 'none'
        });
      }
      return;
    }
    
    const token = wx.getStorageSync('token');
    if (!token) {
      this.promptLoginForResult();
      return;
    }

    this.setData({ isSubmitting: true });

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
            url: `/pkgAssessment/result?data=${encodeURIComponent(resultData)}`,
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
  },

  onShareAppMessage: function () {
    return getShareInfo();
  },

  onShareTimeline: function () {
    return getTimelineInfo();
  }
});
