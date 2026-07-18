const { getShareInfo, getTimelineInfo } = require('../../utils/share.js');
const { getScaleDisplayName, getScaleIconName } = require('../utils/assessment-display.js');

const SERVER_BASE_URL = 'http://127.0.0.1:8000';

function request(options) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token');
    const header = { ...options.header };
    if (token) {
      header.Authorization = `Bearer ${token}`;
    }

    wx.request({
      ...options,
      url: `http://127.0.0.1:8000/api/v1${options.url}`,
      header,
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

const DEFAULT_ICON_PATH = 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/images/assessment/default.png';

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
    summary: '观察任务启动阻力、压力来源和行动节奏，温和理解拖延背后的原因。',
    instruction: '请根据日常学习、工作或生活中的真实状态作答，答案只是帮助你看见自己的行动模式。'
  },
  CLT: {
    summary: '了解自己在好奇心、联想力、开放度和创意落地上的整体倾向。',
    instruction: '请根据最近一个月的大多数真实状态作答，选择最符合你的选项。'
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
    summary: '通过一连串画面化选择，看看你的潜意识更在意安全感、探索、关系还是控制感。',
    instruction: '不要分析太久，请按第一反应选择最贴近你内心画面的答案。'
  },
  ICI: {
    summary: '探索你在人际中的吸引力和闪光点，帮助你看见自己的独特魅力。',
    instruction: '请凭直觉选择最符合自己的答案。'
  },
  'REAL-MAJOR-V1': {
    summary: '通过轻松情境题，看看你更偏爱哪种任务、成就感与工作方式，找到更适合你的职业方向。',
    instruction: '请选你真的更愿意做的事，而不是“看起来更厉害”的答案。'
  },
  AGLT: {
    summary: '探索你身上的天赋信号，发现那些还没完全亮起来的潜能！',
    instruction: '请凭直觉选择最像自己的答案，看看你的天赋雷达会指向哪里。'
  },
  RFLT: {
    summary: '探索你的近期好运气，看看生活正在悄悄送你什么小惊喜！',
    instruction: '请凭直觉选择最像自己的答案，抽取一张属于你的近期好运签。'
  },
  'SOUL-DRINK': {
    summary: '用 15 道第一反应题，测出你的灵魂饮料是哪一杯。',
    instruction: '请不要选“我应该怎样”，而是选“我更自然会怎样”。'
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
      scaleData.iconPath = `https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgAssessment/images/scale-icons/${getScaleIconName(scaleData.short_name)}.png`;
      scaleData.coverImagePath = this.resolveAssetUrl(scaleData.cover_image_url);
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

  resolveAssetUrl(url) {
    if (!url) return '';
    const normalizedUrl = String(url);
    if (/^https?:\/\//.test(normalizedUrl)) return normalizedUrl;
    return `${SERVER_BASE_URL}${normalizedUrl.startsWith('/') ? '' : '/'}${normalizedUrl}`;
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

  handleCoverImageError() {
    this.setData({
      'scale.coverImagePath': ''
    });
  },

  onShareAppMessage: function () {
    return getShareInfo();
  },

  onShareTimeline: function () {
    return getTimelineInfo();
  }
});
