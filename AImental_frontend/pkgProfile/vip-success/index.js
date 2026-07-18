const PLAN_MAP = {
  light: {
    planCode: 'light',
    name: '轻语会员',
    priceText: '8.99',
    image: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/images/vip/member-badge-light.png',
    themeClass: 'light',
  },
  knowing: {
    planCode: 'knowing',
    name: '相知会员',
    priceText: '13.99',
    image: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/images/vip/member-badge-knowing.png',
    themeClass: 'knowing',
  },
  companion: {
    planCode: 'companion',
    name: '长伴会员',
    priceText: '18.99',
    image: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/images/vip/member-badge-companion.png',
    themeClass: 'companion',
  },
};

function decodeOption(value, fallback = '') {
  if (!value) {
    return fallback;
  }
  try {
    return decodeURIComponent(value);
  } catch (error) {
    return value;
  }
}

Page({
  data: {
    statusBarHeight: 24,
    plan: PLAN_MAP.knowing,
  },

  onLoad(options = {}) {
    this.initLayout();
    this.initPlan(options);
  },

  initLayout() {
    try {
      const windowInfo = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
      this.setData({
        statusBarHeight: windowInfo.statusBarHeight || 24,
      });
    } catch (error) {
      this.setData({ statusBarHeight: 24 });
    }
  },

  initPlan(options) {
    const rawPlanCode = decodeOption(options.plan_code || options.planCode, 'knowing');
    const planCode = rawPlanCode.replace(/^vip_/, '');
    const preset = PLAN_MAP[planCode] || PLAN_MAP.knowing;
    const name = decodeOption(options.name, preset.name);
    const priceText = decodeOption(options.price, preset.priceText);

    this.setData({
      plan: {
        ...preset,
        name,
        priceText,
      },
    });
  },

  handleBack() {
    wx.navigateBack({
      fail: () => {
        wx.switchTab({ url: '/pages/profile/index' });
      },
    });
  },

  startExperience() {
    wx.switchTab({ url: '/pages/ai-therapist/index' });
  },
});
