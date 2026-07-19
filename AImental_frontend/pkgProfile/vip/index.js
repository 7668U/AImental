const SERVER_BASE_URL = 'http://127.0.0.1:8000';
const VIP_API_BASE_URL = `${SERVER_BASE_URL}/api/v1/vip`;
const VIP_STATE_CACHE_KEY = 'vipStateCache';

const FEATURE_PRESENTATION = {
  tree_hole: {
    name: '心情树洞',
    shortName: '树洞',
    icon: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/images/vip/feature-tree-hole.png',
    color: '#ff8a24',
    description: '陪你倾诉，温暖每一次心事',
  },
  community: {
    name: '心灵社区',
    shortName: '社区',
    icon: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/images/vip/feature-community.png',
    color: '#6fc3a5',
    description: '更多陪伴，更多温柔回应',
  },
  mood_analysis: {
    name: '心情分析',
    shortName: '心情分析',
    icon: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/images/vip/feature-mood-analysis.png',
    color: '#ef7369',
    description: '看见情绪背后的线索',
  },
  assessment_analysis: {
    name: '测评分析',
    shortName: '测评分析',
    icon: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/images/vip/feature-assessment-analysis.png',
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
    image: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/images/vip/member-badge-light.png',
    memberBadge: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/images/vip/member-badge-light.png',
  },
  knowing: {
    name: '相知会员',
    image: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/images/vip/member-badge-knowing.png',
    memberBadge: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/images/vip/member-badge-knowing.png',
  },
  companion: {
    name: '长伴会员',
    image: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/images/vip/member-badge-companion.png',
    memberBadge: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/images/vip/member-badge-companion.png',
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
      tree_hole: 1000,
      community: 1000,
      mood_analysis: 100,
      assessment_analysis: 100,
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
      tree_hole: 2000,
      community: 2000,
      mood_analysis: 200,
      assessment_analysis: 200,
    },
  },
  {
    code: 'vip_companion',
    product_type: 'membership',
    plan_code: 'companion',
    name: '长伴会员',
    price_fen: 1899,
    quotas: {
      tree_hole: 3000,
      community: 3000,
      mood_analysis: 300,
      assessment_analysis: 300,
    },
  },
];

const FALLBACK_ENTITLEMENTS = {
  tree_hole: { total: 2000, remaining: 2000 },
  community: { total: 2000, remaining: 2000 },
  mood_analysis: { total: 200, remaining: 200 },
  assessment_analysis: { total: 200, remaining: 200 },
};

const FALLBACK_ADDONS = [
  {
    code: 'addon_tree_500',
    product_type: 'addon',
    feature: 'tree_hole',
    name: '树洞加量包',
    amount: 500,
    price_fen: 199,
  },
  {
    code: 'addon_community_500',
    product_type: 'addon',
    feature: 'community',
    name: '社区加量包',
    amount: 500,
    price_fen: 299,
  },
  {
    code: 'addon_mood_50',
    product_type: 'addon',
    feature: 'mood_analysis',
    name: '心情分析加量包',
    amount: 50,
    price_fen: 99,
  },
  {
    code: 'addon_assessment_50',
    product_type: 'addon',
    feature: 'assessment_analysis',
    name: '测评分析加量包',
    amount: 50,
    price_fen: 99,
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
    badgeIcon: presentation.memberBadge || presentation.image,
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

function getPurchaseState(selectedPlan, currentPlanCode) {
  if (!selectedPlan || !selectedPlan.code) {
    return {};
  }
  const isChangingActivePlan = Boolean(
    currentPlanCode
    && selectedPlan.plan_code !== currentPlanCode
  );
  const isRenewal = selectedPlan.plan_code === currentPlanCode;
  return {
    purchaseDisabled: isChangingActivePlan,
    purchaseButtonText: isChangingActivePlan
      ? '不可'
      : (isRenewal ? '续费' : '开通'),
  };
}

function compareVersion(left, right) {
  const leftParts = String(left || '').split('.');
  const rightParts = String(right || '').split('.');
  const length = Math.max(leftParts.length, rightParts.length);
  for (let index = 0; index < length; index += 1) {
    const leftValue = parseInt(leftParts[index] || '0', 10);
    const rightValue = parseInt(rightParts[index] || '0', 10);
    if (leftValue > rightValue) {
      return 1;
    }
    if (leftValue < rightValue) {
      return -1;
    }
  }
  return 0;
}

function canUseVirtualPayment() {
  if (!wx.requestVirtualPayment) {
    return false;
  }
  try {
    const info = wx.getSystemInfoSync ? wx.getSystemInfoSync() : {};
    return (
      compareVersion(info.SDKVersion, '2.19.2') >= 0
      || (wx.canIUse && wx.canIUse('requestVirtualPayment'))
    );
  } catch (error) {
    return Boolean(wx.canIUse && wx.canIUse('requestVirtualPayment'));
  }
}

Page({
  data: {
    statusBarHeight: 24,
    vipStateReady: false,
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
  },

  onLoad() {
    this.initLayout();
    this.applyProducts(FALLBACK_PRODUCTS);
    this.restoreVipStateCache();
    this.fetchCatalog();
    this.fetchVipState();
  },

  onShow() {
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
            this.setData({ addonProducts });
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
      wx.removeStorageSync(VIP_STATE_CACHE_KEY);
      this.applyVipSummary({}, false);
      return Promise.resolve();
    }

    return new Promise((resolve) => {
      wx.request({
        url: `${VIP_API_BASE_URL}/me`,
        method: 'GET',
        header: { Authorization: `Bearer ${token}` },
        success: (res) => {
          if (res.statusCode === 200 && res.data) {
            this.applyVipSummary(res.data, true);
          } else if (!this.data.vipStateReady) {
            this.applyVipSummary({}, false);
          }
          resolve();
        },
        fail: (error) => {
          console.error('fetchVipState failed:', error);
          if (!this.data.vipStateReady) {
            this.applyVipSummary({}, false);
          }
          resolve();
        },
      });
    });
  },

  restoreVipStateCache() {
    try {
      const cached = wx.getStorageSync(VIP_STATE_CACHE_KEY);
      const summary = cached && cached.summary ? cached.summary : cached;
      if (summary && typeof summary === 'object' && summary.user_type) {
        this.applyVipSummary(summary, false);
      }
    } catch (error) {
      console.warn('restoreVipStateCache failed:', error);
    }
  },

  applyVipSummary(summary, persist) {
    const source = summary || {};
    const currentMember = normalizeMember(source.membership);
    const currentPlanCode = currentMember ? currentMember.planCode : '';
    this.setData({
      vipStateReady: true,
      isMemberView: Boolean(currentMember),
      currentMember,
      usageItems: normalizeUsage(source.entitlements),
    });
    this.applyCurrentPlan(currentPlanCode);
    if (persist) {
      try {
        wx.setStorageSync(VIP_STATE_CACHE_KEY, {
          summary: source,
          cachedAt: Date.now(),
        });
      } catch (error) {
        console.warn('cacheVipState failed:', error);
      }
    }
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
      ...getPurchaseState(selectedPlan, this.data.currentPlanCode),
    });
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
      ...getPurchaseState(selectedPlan, this.data.currentPlanCode),
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
        this.handleVirtualPayment(payment, token, 'membership', res.data.order);
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
      addonAgreementChecked: true,
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
    wx.navigateTo({
      url: '/pkgProfile/vip-records/index',
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
        this.handleVirtualPayment(payment, token, 'addon', res.data.order);
      },
      fail: () => {
        this.finishPurchaseWithError('网络异常，请稍后重试');
      },
    });
  },

  handleVirtualPayment(payment, token, purchaseType, order) {
    const orderId = order && order.id;
    if (payment.mode === 'wechat_virtual' && payment.payload) {
      this.requestVirtualPayment(
        payment.payload,
        token,
        purchaseType,
        orderId
      );
      return;
    }
    this.cancelPendingOrder(orderId, token);
    this.setData({ purchaseLoading: false });
    wx.showModal({
      title: '\u652f\u4ed8\u672a\u914d\u7f6e',
      content: '\u5fae\u4fe1\u5b98\u65b9\u865a\u62df\u652f\u4ed8\u53c2\u6570\u5c1a\u672a\u5c31\u7eea\u3002',
      showCancel: false,
    });
  },

  requestVirtualPayment(payload, token, purchaseType, orderId) {
    if (!canUseVirtualPayment()) {
      this.finishPurchaseWithError('\u5f53\u524d\u5fae\u4fe1\u7248\u672c\u4e0d\u652f\u6301\u865a\u62df\u652f\u4ed8');
      return;
    }
    const deviceInfo = wx.getDeviceInfo
      ? wx.getDeviceInfo()
      : wx.getSystemInfoSync();
    if (deviceInfo.platform === 'devtools') {
      this.setData({ purchaseLoading: false });
      wx.showModal({
        title: '\u8bf7\u4f7f\u7528\u771f\u673a\u8c03\u8bd5',
        content: '\u5f00\u53d1\u8005\u5de5\u5177\u6a21\u62df\u5668\u65e0\u6cd5\u7a33\u5b9a\u52a0\u8f7d\u5fae\u4fe1\u5b98\u65b9\u865a\u62df\u652f\u4ed8\u3002\u8bf7\u4f7f\u7528\u771f\u673a\u5fae\u4fe1\u5b8c\u6210\u6d4b\u8bd5\u3002',
        showCancel: false,
      });
      return;
    }
    wx.requestVirtualPayment({
      ...payload,
      success: () => {
        this.reconcileVirtualOrder(orderId, token, purchaseType);
      },
      fail: (error) => {
        console.error('requestVirtualPayment failed', error);
        this.setData({ purchaseLoading: false });
        const errCode = error && Number(error.errCode);
        if (errCode === -2 || String((error && error.errMsg) || '').includes('cancel')) {
          this.cancelPendingOrder(orderId, token);
          wx.showToast({ title: '\u5df2\u53d6\u6d88\u652f\u4ed8', icon: 'none' });
          return;
        }
        wx.showToast({ title: '\u652f\u4ed8\u672a\u5b8c\u6210', icon: 'none' });
      },
    });
  },

  cancelPendingOrder(orderId, token) {
    if (!orderId || !token) {
      return;
    }
    wx.request({
      url: `${VIP_API_BASE_URL}/orders/${orderId}/cancel`,
      method: 'POST',
      header: { Authorization: `Bearer ${token}` },
      fail: (error) => {
        console.warn('cancelPendingOrder failed:', error);
      },
    });
  },

  reconcileVirtualOrder(orderId, token, purchaseType, retries = 10) {
    if (!orderId) {
      this.finishPurchaseWithError('\u8ba2\u5355\u72b6\u6001\u786e\u8ba4\u5931\u8d25');
      return;
    }
    wx.request({
      url: `${VIP_API_BASE_URL}/orders/${orderId}/reconcile`,
      method: 'POST',
      header: { Authorization: `Bearer ${token}` },
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          if (res.data.paid || (res.data.order && res.data.order.status === 'fulfilled')) {
            this.finishPurchaseSuccess(purchaseType);
            return;
          }
          if (retries > 0) {
            setTimeout(() => {
              this.reconcileVirtualOrder(orderId, token, purchaseType, retries - 1);
            }, 1500);
            return;
          }
          this.setData({ purchaseLoading: false });
          this.fetchVipState();
          wx.showModal({
            title: '\u652f\u4ed8\u786e\u8ba4\u4e2d',
            content: '\u652f\u4ed8\u5df2\u5b8c\u6210\uff0c\u4f1a\u5458\u6743\u76ca\u6b63\u5728\u540c\u6b65\u3002\u8bf7\u7a0d\u540e\u8fd4\u56de\u4f1a\u5458\u4e2d\u5fc3\u67e5\u770b\u3002',
            showCancel: false,
          });
          return;
        }
        this.pollOrderFulfilled(orderId, token, purchaseType);
      },
      fail: () => {
        this.pollOrderFulfilled(orderId, token, purchaseType);
      },
    });
  },

  pollOrderFulfilled(orderId, token, purchaseType, retries = 20) {
    if (!orderId) {
      this.finishPurchaseWithError('\u8ba2\u5355\u72b6\u6001\u786e\u8ba4\u5931\u8d25');
      return;
    }
    wx.request({
      url: `${VIP_API_BASE_URL}/orders/${orderId}`,
      method: 'GET',
      header: { Authorization: `Bearer ${token}` },
      success: (res) => {
        if (res.statusCode === 200 && res.data && res.data.status === 'fulfilled') {
          this.finishPurchaseSuccess(purchaseType);
          return;
        }
        if (retries > 0) {
          setTimeout(() => {
            this.pollOrderFulfilled(orderId, token, purchaseType, retries - 1);
          }, 1000);
          return;
        }
        this.setData({ purchaseLoading: false });
        wx.showModal({
          title: '\u652f\u4ed8\u786e\u8ba4\u4e2d',
          content: '\u652f\u4ed8\u7ed3\u679c\u5df2\u63d0\u4ea4\uff0c\u6743\u76ca\u5230\u8d26\u4ecd\u5728\u786e\u8ba4\u3002\u8bf7\u7a0d\u540e\u5237\u65b0\u4f1a\u5458\u4e2d\u5fc3\u3002',
          showCancel: false,
        });
      },
      fail: () => {
        this.finishPurchaseWithError('\u8ba2\u5355\u72b6\u6001\u786e\u8ba4\u5931\u8d25');
      },
    });
  },

  finishPurchaseSuccess(purchaseType) {
    if (purchaseType === 'addon') {
      this.finishAddonPurchaseSuccess();
      return;
    }
    this.fetchVipState().finally(() => {
      this.setData({ purchaseLoading: false });
      this.navigateToSuccessPage();
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
    this.fetchVipState().finally(() => {
      wx.showModal({
        title: '购买成功',
        content: '加量包权益已到账。',
        showCancel: false,
        confirmText: '完成',
      });
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
