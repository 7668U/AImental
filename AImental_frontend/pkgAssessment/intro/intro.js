const { getShareInfo, getTimelineInfo } = require('../../utils/share.js');
const { getScaleDisplayName, getScaleIconName } = require('../../utils/assessment-display.js');

function request(options) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token');
    wx.request({
      ...options,
      url: `http://127.0.0.1:8000/api/v1${options.url}`,
      header: {
        ...options.header,
        'Authorization': `Bearer ${token}`
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          reject(res);
        }
      },
      fail(err) {
        reject(err);
      }
    });
  });
}

const DEFAULT_ICON_PATH = '/images/assessment/default.png';

const SCALE_INTRO_COPY = {
  SDS: {
    summary: '了解近两周的低落、兴趣、精力和自我感受，帮助你温和地观察当前情绪状态。',
    instruction: '请根据最近两周的真实感受选择最符合的一项，不需要反复斟酌。'
  },
  'BDI-II': {
    summary: '了解近两周的低落、兴趣、精力和自我感受，帮助你温和地观察当前情绪状态。',
    instruction: '请根据最近两周的真实感受选择最符合的一项，不需要反复斟酌。'
  },
  SAS: {
    summary: '观察近期紧张、不安和身体化焦虑感，帮助你了解压力下的反应强度。',
    instruction: '按最近一段时间的实际体验作答，选择最贴近自己的频率。'
  },
  BRMS: {
    summary: '评估情绪高涨、精力增加和冲动倾向，帮助你识别情绪能量变化。',
    instruction: '请根据近期状态选择最符合的一项，保持直觉作答。'
  },
  SAD: {
    summary: '了解社交场景中的回避和苦恼感，帮助你看见人际压力来源。',
    instruction: '请按平时在社交中的真实反应作答。'
  },
  IAS: {
    summary: '观察与人互动时的紧张、担心和不自在，帮助你理解交流中的焦虑。',
    instruction: '请回想常见互动场景，选择最贴近你的感受。'
  },
  Lonely: {
    summary: '觉察不同关系中的孤独感和连接需求，帮助你理解自己的陪伴感受。',
    instruction: '请根据近期真实关系体验作答。'
  },
  SES: {
    summary: '了解自我评价和自我接纳程度，帮助你看见内在价值感。',
    instruction: '请按你通常对自己的看法选择答案。'
  },
  APS: {
    summary: '观察拖延、行动阻力和任务压力，帮助你理解自己的行动模式。',
    instruction: '请根据日常学习、工作或生活中的真实习惯作答。'
  },
  CLT: {
    summary: '探索创造力、想象力和解决问题方式，帮助你发现思维特点。',
    instruction: '请按第一反应选择，不必追求标准答案。'
  },
  'mbti-93': {
    summary: '探索性格偏好、能量来源和相处方式，帮助你认识自己的行为倾向。',
    instruction: '请选择更像平常自己的选项，而不是理想中的自己。'
  },
  AAS: {
    summary: '了解亲密关系中的依恋安全感，帮助你看见靠近与独立的模式。',
    instruction: '请根据真实关系体验作答。'
  },
  ECR: {
    summary: '观察亲密关系中的焦虑和回避倾向，帮助你理解安全感需求。',
    instruction: '请以稳定亲密关系中的常见感受为准。'
  },
  LAMT: {
    summary: '探索你对爱情、陪伴和关系期待的态度，帮助你理解恋爱观。',
    instruction: '按第一反应选择最像自己的答案。'
  },
  LDCT: {
    summary: '了解恋爱关系中的表达、沟通和相处习惯，帮助你看见互动风格。',
    instruction: '请以真实相处方式作答，不需要选择最完美的答案。'
  },
  TPS: {
    summary: '通过情景选择探索性格中更真实的一面，看见内在渴望和互动模式。',
    instruction: '请阅读每个情景，并从选项中选择第一反应。'
  },
  ICI: {
    summary: '探索你在人际中的吸引力和闪光点，帮助你看见自己的独特魅力。',
    instruction: '请凭直觉选择最符合自己的答案。'
  },
  'REAL-MAJOR-V1': {
    summary: '从兴趣和选择中发现更贴近你的专业方向，看看真实偏好在哪里。',
    instruction: '请放下现实限制，选择更让你心动的选项。'
  },
  AGLT: {
    summary: '用轻松方式探索你的年度好运关键词，给当下生活一点积极提醒。',
    instruction: '请按直觉作答，享受这个轻松的小测试。'
  }
};

Page({
  data: {
    scale: null, // Stores the fetched scale details
    scaleId: null, // Stores the ID passed from the previous page
    passedDisplayTitle: '',
    isLoading: true,
    isError: false
  },

  onLoad(options) {
    const scaleId = options.id; // Get the scaleId from the URL parameters
    const displayTitle = options.title ? decodeURIComponent(options.title) : '';
    if (scaleId) {
      this.setData({
        scaleId: scaleId,
        passedDisplayTitle: displayTitle
      });
      this.fetchScaleDetails(scaleId);
    } else {
      this.setData({ isError: true, isLoading: false });
      wx.showToast({
        title: '问卷ID缺失',
        icon: 'none'
      });
    }
  },

  async fetchScaleDetails(scaleId) {
    this.setData({ isLoading: true, isError: false });
    try {
      const scaleData = await request({ url: `/assessments/${scaleId}`, method: 'GET' });

      const shortCopy = this.getShortCopy(scaleData);
      const displayName = this.data.passedDisplayTitle || getScaleDisplayName(scaleData.short_name, scaleData.name);
      scaleData.name = displayName;
      scaleData.displayName = displayName;
      scaleData.iconPath = `/images/assessment/scale-icons/${getScaleIconName(scaleData.short_name)}.png`;
      scaleData.coverSummary = shortCopy.summary;
      scaleData.coverInstruction = shortCopy.instruction;

      this.setData({
        scale: scaleData,
        isLoading: false
      });
    } catch (error) {
      console.error("fetchScaleDetails failed:", error);
      this.setData({ isError: true, isLoading: false });
      wx.showToast({
        title: '加载问卷详情失败',
        icon: 'none'
      });
    }
  },

  getShortCopy(scaleData) {
    const copy = SCALE_INTRO_COPY[scaleData.short_name];
    if (copy) return copy;
    return {
      summary: scaleData.description || '通过简短测评了解自己的状态和倾向，获得一份清晰的自我观察结果。',
      instruction: '请根据第一反应作答，选择最符合自己的选项。'
    };
  },

  startTest() {
    const scaleId = this.data.scaleId;
    if (scaleId) {
      wx.redirectTo({
        url: `/pkgAssessment/test?id=${scaleId}`,
      });
    } else {
      wx.showToast({
        title: '无法开始测试，问卷ID缺失',
        icon: 'none'
      });
    }
  },

  handleIconError(e) {
    this.setData({
      'scale.iconPath': DEFAULT_ICON_PATH
    });
  },

  onShareAppMessage: function () {
    return getShareInfo();
  },

  onShareTimeline: function () {
    return getTimelineInfo();
  }
});
