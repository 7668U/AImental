const SERVER_BASE_URL = 'http://127.0.0.1:8000';
const VIP_API_BASE_URL = `${SERVER_BASE_URL}/api/v1/vip`;

const FEATURE_PRESENTATION = {
  tree_hole: {
    name: '心情树洞',
    shortName: '树洞',
    icon: '/images/vip/feature-tree-hole.png',
    color: '#ff8a24',
    description: '陪你倾诉，温暖每一次心事',
  },
  community: {
    name: '心灵社区',
    shortName: '社区',
    icon: '/images/vip/feature-community.png',
    color: '#6fc3a5',
    description: '更多陪伴，更多温柔回应',
  },
  mood_analysis: {
    name: '单项心情分析',
    shortName: '心情分析',
    icon: '/images/vip/feature-mood-analysis.png',
    color: '#ef7369',
    description: '看见情绪背后的线索',
  },
  assessment_analysis: {
    name: '测评分析',
    shortName: '测评分析',
    icon: '/images/vip/feature-assessment-analysis.png',
    color: '#77b9e7',
    description: '解读测评，获得更清晰的自己',
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
    name: '轻语会员',
    image: '/images/vip/plan-light.png',
  },
  knowing: {
    name: '相知会员',
    image: '/images/vip/plan-knowing.png',
  },
  companion: {
    name: '长伴会员',
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

const FALLBACK_ENTITLEMENTS = {
  tree_hole: { total: 600, remaining: 600 },
  community: { total: 1200, remaining: 1200 },
  mood_analysis: { total: 80, remaining: 80 },
  assessment_analysis: { total: 100, remaining: 100 },
};

const FALLBACK_ADDONS = [
  {
    code: 'addon_tree_300',
    product_type: 'addon',
    feature: 'tree_hole',
    name: '树洞加量包',
    amount: 300,
    price_fen: 399,
  },
  {
    code: 'addon_community_300',
    product_type: 'addon',
    feature: 'community',
    name: '社区加量包',
    amount: 300,
    price_fen: 799,
  },
  {
    code: 'addon_mood_20',
    product_type: 'addon',
    feature: 'mood_analysis',
    name: '心情分析加量包',
    amount: 20,
    price_fen: 199,
  },
  {
    code: 'addon_assessment_20',
    product_type: 'addon',
    feature: 'assessment_analysis',
    name: '测评分析加量包',
    amount: 20,
    price_fen: 199,
  },
];

function formatPrice(priceFen) {
  const normalized = Number(priceFen) || 0;
  return (normalized / 100).toFixed(2);
}

function formatDate(value) {
  if (!value) {
    return '';
  }
  const normalized = typeof value === 'number' || /^\d+$/.test(String(value))
    ? new Date(Number(value) * 1000)
    : new Date(value);
  if (Number.isNaN(normalized.getTime())) {
    return '';
  }
  const year = normalized.getFullYear();
  const month = String(normalized.getMonth() + 1).padStart(2, '0');
  const day = String(normalized.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function normalizeQuotaItem(rawItem) {
  const item = rawItem || {};
  const total = Math.max(Number(item.total ?? item.limit ?? item.monthly_quota) || 0, 0);
  const remaining = Math.max(Number(item.remaining) || 0, 0);
  return { total, remaining };
}

function formatProduct(product, currentPlanCode) {
  const presentation = PLAN_PRESENTATION[product.plan_code] || PLAN_PRESENTATION.light;
  const quotas = product.quotas || {};
  return {
    ...product,
    name: product.name || presentation.name,
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

function normalizeMember(membership) {
  if (!membership || membership.status !== 'active') {
    return null;
  }
  const presentation = PLAN_PRESENTATION[membership.plan_code] || PLAN_PRESENTATION.knowing;
  const expiresText = formatDate(membership.expires_at || membership.expire_at);
  return {
    planCode: membership.plan_code,
    name: membership.plan_name || presentation.name,
    icon: presentation.image,
    expiresText: expiresText ? `会员有效期至 ${expiresText}` : '会员权益使用中',
  };
}

function normalizeUsage(entitlements) {
  const source = entitlements || FALLBACK_ENTITLEMENTS;
  return FEATURE_ORDER.map((feature) => {
    const presentation = FEATURE_PRESENTATION[feature];
    const item = normalizeQuotaItem(source[feature]);
    const used = Math.max(item.total - item.remaining, 0);
    const percent = item.total ? Math.min(Math.round((used / item.total) * 100), 100) : 0;
    return {
      feature,
      name: presentation.name,
      icon: presentation.icon,
      used,
      total: item.total,
      countText: `${used} / ${item.total} 次`,
      progressStyle: `width: ${percent}%; background: ${presentation.color};`,
    };
  });
}

function normalizeAddon(product) {
  const feature = product.feature || 'tree_hole';
  const presentation = FEATURE_PRESENTATION[feature] || FEATURE_PRESENTATION.tree_hole;
  const nameByFeature = {
    tree_hole: '树洞加量包',
    community: '社区加量包',
    mood_analysis: '心情分析加量包',
    assessment_analysis: '测评分析加量包',
  };
  return {
    ...product,
    name: nameByFeature[feature] || product.name,
    amount: Number(product.amount) || 0,
    icon: presentation.icon,
    featureName: presentation.shortName,
    description: presentation.description,
    priceText: formatPrice(product.price_fen),
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
    isMemberView: false,
    currentMember: null,
    usageItems: normalizeUsage(FALLBACK_ENTITLEMENTS),
    addonProducts: FALLBACK_ADDONS.map(normalizeAddon),
    selectedAddon: null,
    addonQuantity: 1,
    addonTotalText: '3.99',
    addonModalVisible: false,
    addonAgreementChecked: false,
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
    this.fetchCatalog();
    this.fetchVipState();
  },

  onPullDownRefresh() {
    Promise.all([
      this.fetchCatalog(),
      this.fetchVipState(),
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
          if (res.statusCode === 200 && res.data) {
            if (Array.isArray(res.data.membership_products)) {
              this.applyProducts(res.data.membership_products);
            }
            const addonProducts = Array.isArray(res.data.addon_products)
              ? res.data.addon_products.map(normalizeAddon)
              : this.data.addonProducts;
            this.setData({
              addonProducts,
              mockPaymentAvailable: Boolean(res.data.mock_payment_available),
            });
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
      this.setData({
        isMemberView: false,
        currentMember: null,
        usageItems: normalizeUsage(FALLBACK_ENTITLEMENTS),
      });
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
          const currentMember = normalizeMember(membership);
          const currentPlanCode = currentMember ? currentMember.planCode : '';
          this.setData({
            isMemberView: Boolean(currentMember),
            currentMember,
            usageItems: normalizeUsage(res.data && res.data.entitlements),
          });
          this.applyCurrentPlan(currentPlanCode);
          resolve();
        },
        fail: (error) => {
          console.error('fetchVipState failed:', error);
          this.applyCurrentPlan('');
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
          this.completeMockPayment(payment.mock_pay_endpoint, token, 'membership');
          return;
        }
        if (payment.mode === 'wechat' && payment.payload) {
          this.requestWechatPayment(payment.payload, 'membership');
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

  openAddonModal(event) {
    const code = event.currentTarget.dataset.code;
    const selectedAddon = this.data.addonProducts.find((item) => item.code === code);
    if (!selectedAddon) {
      return;
    }
    this.setData({
      selectedAddon,
      addonQuantity: 1,
      addonTotalText: selectedAddon.priceText,
      addonModalVisible: true,
      addonAgreementChecked: false,
    });
  },

  closeAddonModal() {
    if (this.data.purchaseLoading) {
      return;
    }
    this.setData({
      addonModalVisible: false,
      selectedAddon: null,
      addonQuantity: 1,
      addonAgreementChecked: false,
    });
  },

  decreaseQuantity() {
    if (this.data.purchaseLoading) {
      return;
    }
    this.updateAddonQuantity(Math.max(this.data.addonQuantity - 1, 1));
  },

  increaseQuantity() {
    if (this.data.purchaseLoading) {
      return;
    }
    this.updateAddonQuantity(Math.min(this.data.addonQuantity + 1, 99));
  },

  updateAddonQuantity(quantity) {
    const selectedAddon = this.data.selectedAddon;
    if (!selectedAddon) {
      return;
    }
    this.setData({
      addonQuantity: quantity,
      addonTotalText: formatPrice((Number(selectedAddon.price_fen) || 0) * quantity),
    });
  },

  toggleAddonAgreement() {
    if (this.data.purchaseLoading) {
      return;
    }
    this.setData({
      addonAgreementChecked: !this.data.addonAgreementChecked,
    });
  },

  openPurchaseRecords() {
    wx.showToast({
      title: '购买记录页面建设中',
      icon: 'none',
    });
  },

  handleAddonPay() {
    if (this.data.purchaseLoading || !this.data.selectedAddon) {
      return;
    }
    if (!this.data.addonAgreementChecked) {
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
        product_code: this.data.selectedAddon.code,
        quantity: this.data.addonQuantity,
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
          this.completeMockPayment(payment.mock_pay_endpoint, token, 'addon');
          return;
        }
        if (payment.mode === 'wechat' && payment.payload) {
          this.requestWechatPayment(payment.payload, 'addon');
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

  completeMockPayment(endpoint, token, purchaseType) {
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
        if (purchaseType === 'addon') {
          this.finishAddonPurchaseSuccess();
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

  requestWechatPayment(payload, purchaseType) {
    wx.requestPayment({
      ...payload,
      success: () => {
        if (purchaseType === 'addon') {
          this.finishAddonPurchaseSuccess();
          return;
        }
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

  finishAddonPurchaseSuccess() {
    this.setData({
      purchaseLoading: false,
      addonModalVisible: false,
      selectedAddon: null,
      addonQuantity: 1,
      addonAgreementChecked: false,
    });
    wx.showModal({
      title: '购买成功',
      content: '加量包权益已到账。',
      showCancel: false,
      confirmText: '完成',
      success: () => {
        this.fetchVipState();
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
