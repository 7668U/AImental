const SERVER_BASE_URL = 'http://127.0.0.1:8000';
const VIP_API_BASE_URL = `${SERVER_BASE_URL}/api/v1/vip`;

const FEATURE_PRESENTATION = {
  tree_hole: {
    name: '心情树洞',
    icon: '/images/vip/feature-tree-hole.png',
  },
  community: {
    name: '心灵社区',
    icon: '/images/vip/feature-community.png',
  },
  mood_analysis: {
    name: '单项心情分析',
    icon: '/images/vip/feature-mood-analysis.png',
  },
  assessment_analysis: {
    name: '测评分析',
    icon: '/images/vip/feature-assessment-analysis.png',
  },
};

const FEATURE_ORDER = [
  'tree_hole',
  'community',
  'mood_analysis',
  'assessment_analysis',
];

const PLAN_PRESENTATION = {
  light: {
    image: '/images/vip/plan-light.png',
  },
  knowing: {
    image: '/images/vip/plan-knowing.png',
  },
  companion: {
    image: '/images/vip/plan-companion.png',
  },
};

const FALLBACK_PRODUCTS = [
  {
    code: 'vip_light',
    product_type: 'membership',
    plan_code: 'light',
    name: '轻语会员',
    price_fen: 899,
    quotas: {
      tree_hole: 300,
      community: 500,
      mood_analysis: 40,
      assessment_analysis: 50,
    },
  },
  {
    code: 'vip_knowing',
    product_type: 'membership',
    plan_code: 'knowing',
    name: '相知会员',
    recommended: true,
    price_fen: 1399,
    quotas: {
      tree_hole: 600,
      community: 1200,
      mood_analysis: 80,
      assessment_analysis: 100,
    },
  },
  {
    code: 'vip_companion',
    product_type: 'membership',
    plan_code: 'companion',
    name: '长伴会员',
    price_fen: 1899,
    quotas: {
      tree_hole: 1200,
      community: 2400,
      mood_analysis: 120,
      assessment_analysis: 200,
    },
  },
];

function formatPrice(priceFen) {
  const normalized = Number(priceFen) || 0;
  return (normalized / 100).toFixed(2);
}

function formatProduct(product, currentPlanCode) {
  const presentation = PLAN_PRESENTATION[product.plan_code] || PLAN_PRESENTATION.light;
  const quotas = product.quotas || {};
  return {
    ...product,
    image: presentation.image,
    priceText: formatPrice(product.price_fen),
    isCurrent: product.plan_code === currentPlanCode,
    quotaItems: FEATURE_ORDER.map((feature) => ({
      feature,
      name: FEATURE_PRESENTATION[feature].name,
      icon: FEATURE_PRESENTATION[feature].icon,
      amount: Number(quotas[feature]) || 0,
    })),
  };
}

function getRequestErrorMessage(response, fallback) {
  const detail = response && response.data && response.data.detail;
  if (detail && typeof detail === 'object' && detail.message) {
    return detail.message;
  }
  if (typeof detail === 'string') {
    return detail;
  }
  return fallback;
}

Page({
  data: {
    statusBarHeight: 24,
    plans: [],
    selectedPlanCode: 'vip_knowing',
    selectedPlan: {},
    currentPlanCode: '',
    agreementChecked: true,
    purchaseLoading: false,
    purchaseDisabled: false,
    purchaseButtonText: '开通',
    agreementModalVisible: false,
    mockPaymentAvailable: false,
  },

  onLoad() {
    this.initLayout();
    this.applyProducts(FALLBACK_PRODUCTS);
    this.fetchVipState();
    this.fetchCatalog();
  },

  onPullDownRefresh() {
    Promise.all([
      this.fetchVipState(),
      this.fetchCatalog(),
    ]).finally(() => {
      wx.stopPullDownRefresh();
    });
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

  fetchCatalog() {
    return new Promise((resolve) => {
      wx.request({
        url: `${VIP_API_BASE_URL}/catalog`,
        method: 'GET',
        success: (res) => {
          if (res.statusCode === 200 && res.data && Array.isArray(res.data.membership_products)) {
            this.setData({
              mockPaymentAvailable: Boolean(res.data.mock_payment_available),
            });
            this.applyProducts(res.data.membership_products);
          }
          resolve();
        },
        fail: (error) => {
          console.error('fetchVipCatalog failed:', error);
          resolve();
        },
      });
    });
  },

  fetchVipState() {
    const token = wx.getStorageSync('token');
    if (!token) {
      this.applyCurrentPlan('');
      return Promise.resolve();
    }

    return new Promise((resolve) => {
      wx.request({
        url: `${VIP_API_BASE_URL}/me`,
        method: 'GET',
        header: { Authorization: `Bearer ${token}` },
        success: (res) => {
          const membership = res.statusCode === 200 && res.data
            ? res.data.membership
            : null;
          const currentPlanCode = membership && membership.status === 'active'
            ? membership.plan_code
            : '';
          this.applyCurrentPlan(currentPlanCode);
          resolve();
        },
        fail: (error) => {
          console.error('fetchVipState failed:', error);
          resolve();
        },
      });
    });
  },

  applyCurrentPlan(currentPlanCode) {
    this.setData({ currentPlanCode: currentPlanCode || '' });
    const products = this.data.plans.length
      ? this.data.plans
      : FALLBACK_PRODUCTS.map((item) => formatProduct(item, currentPlanCode));
    this.applyProducts(products);
  },

  applyProducts(products) {
    const normalized = products
      .filter((item) => item && item.product_type === 'membership')
      .sort((left, right) => (left.rank || 0) - (right.rank || 0))
      .map((item) => formatProduct(item, this.data.currentPlanCode));

    if (!normalized.length) {
      return;
    }

    const currentProduct = normalized.find(
      (item) => item.plan_code === this.data.currentPlanCode
    );
    const existingSelection = normalized.find(
      (item) => item.code === this.data.selectedPlanCode
    );
    const recommended = normalized.find((item) => item.recommended);
    const selectedPlan = currentProduct || existingSelection || recommended || normalized[0];

    this.setData({
      plans: normalized,
      selectedPlanCode: selectedPlan.code,
      selectedPlan,
    });
    this.updatePurchaseState(selectedPlan);
  },

  selectPlan(event) {
    const code = event.currentTarget.dataset.code;
    if (!code || code === this.data.selectedPlanCode) {
      return;
    }
    const selectedPlan = this.data.plans.find((item) => item.code === code);
    if (!selectedPlan) {
      return;
    }
    this.setData({
      selectedPlanCode: code,
      selectedPlan,
    });
    this.updatePurchaseState(selectedPlan);
  },

  updatePurchaseState(selectedPlan) {
    if (!selectedPlan || !selectedPlan.code) {
      return;
    }
    const isChangingActivePlan = Boolean(
      this.data.currentPlanCode
      && selectedPlan.plan_code !== this.data.currentPlanCode
    );
    const isRenewal = selectedPlan.plan_code === this.data.currentPlanCode;
    this.setData({
      purchaseDisabled: isChangingActivePlan,
      purchaseButtonText: isChangingActivePlan
        ? '不可'
        : (isRenewal ? '续费' : '开通'),
    });
  },

  toggleAgreement() {
    this.setData({
      agreementChecked: !this.data.agreementChecked,
    });
  },

  openAgreement() {
    this.setData({
      agreementModalVisible: true,
    });
  },

  closeAgreement() {
    this.setData({
      agreementModalVisible: false,
    });
  },

  noop() {},

  handlePurchase() {
    if (this.data.purchaseLoading) {
      return;
    }
    if (this.data.purchaseDisabled) {
      wx.showToast({
        title: '当前暂不支持更换会员等级',
        icon: 'none',
      });
      return;
    }
    if (!this.data.agreementChecked) {
      wx.showToast({
        title: '请先阅读并同意会员服务协议',
        icon: 'none',
      });
      return;
    }

    const token = wx.getStorageSync('token');
    if (!token) {
      wx.showToast({
        title: '请先返回“我的”页面登录',
        icon: 'none',
      });
      return;
    }

    this.setData({ purchaseLoading: true });
    wx.request({
      url: `${VIP_API_BASE_URL}/orders`,
      method: 'POST',
      header: { Authorization: `Bearer ${token}` },
      data: {
        product_code: this.data.selectedPlan.code,
      },
      success: (res) => {
        if (res.statusCode !== 201 || !res.data) {
          this.finishPurchaseWithError(
            getRequestErrorMessage(res, '订单创建失败，请稍后重试')
          );
          return;
        }

        const payment = res.data.payment || {};
        if (payment.mode === 'mock' && payment.mock_pay_endpoint) {
          this.completeMockPayment(payment.mock_pay_endpoint, token);
          return;
        }
        if (payment.mode === 'wechat' && payment.payload) {
          this.requestWechatPayment(payment.payload);
          return;
        }

        this.setData({ purchaseLoading: false });
        wx.showModal({
          title: '支付暂未开放',
          content: '订单能力已经接通，但微信支付参数尚未配置，本次不会扣款。',
          showCancel: false,
        });
      },
      fail: () => {
        this.finishPurchaseWithError('网络异常，请稍后重试');
      },
    });
  },

  completeMockPayment(endpoint, token) {
    const url = endpoint.startsWith('http')
      ? endpoint
      : `${SERVER_BASE_URL}${endpoint}`;
    wx.request({
      url,
      method: 'POST',
      header: { Authorization: `Bearer ${token}` },
      success: (res) => {
        if (res.statusCode !== 200) {
          this.finishPurchaseWithError(
            getRequestErrorMessage(res, '模拟支付失败，请稍后重试')
          );
          return;
        }
        this.setData({ purchaseLoading: false });
        this.navigateToSuccessPage();
      },
      fail: () => {
        this.finishPurchaseWithError('模拟支付请求失败');
      },
    });
  },

  requestWechatPayment(payload) {
    wx.requestPayment({
      ...payload,
      success: () => {
        this.setData({ purchaseLoading: false });
        this.navigateToSuccessPage();
      },
      fail: (error) => {
        this.setData({ purchaseLoading: false });
        if (error && String(error.errMsg || '').includes('cancel')) {
          wx.showToast({ title: '已取消支付', icon: 'none' });
          return;
        }
        wx.showToast({ title: '支付未完成', icon: 'none' });
      },
    });
  },

  navigateToSuccessPage() {
    const selectedPlan = this.data.selectedPlan || {};
    const params = [
      `plan_code=${encodeURIComponent(selectedPlan.plan_code || 'knowing')}`,
      `name=${encodeURIComponent(selectedPlan.name || '相知会员')}`,
      `price=${encodeURIComponent(selectedPlan.priceText || '13.99')}`,
    ].join('&');

    wx.navigateTo({
      url: `/pkgProfile/vip-success/index?${params}`,
    });
  },

  finishPurchaseWithError(message) {
    this.setData({ purchaseLoading: false });
    wx.showToast({
      title: message,
      icon: 'none',
      duration: 2600,
    });
  },

  handleBack() {
    wx.navigateBack({
      fail: () => {
        wx.switchTab({ url: '/pages/profile/index' });
      },
    });
  },
});
