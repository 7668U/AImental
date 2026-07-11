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
    name: '心情分析',
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
    icon: '/images/vip/plan-light.png',
  },
  knowing: {
    name: '相知会员',
    icon: '/images/vip/plan-knowing.png',
  },
  companion: {
    name: '长伴会员',
    icon: '/images/vip/plan-companion.png',
  },
};

const FALLBACK_MEMBER = {
  planCode: 'knowing',
  name: '相知会员',
  icon: PLAN_PRESENTATION.knowing.icon,
  expiresText: '会员有效期至 2026-08-11',
};

const FALLBACK_ENTITLEMENTS = {
  tree_hole: { total: 600, remaining: 172 },
  community: { total: 1200, remaining: 214 },
  mood_analysis: { total: 80, remaining: 48 },
  assessment_analysis: { total: 100, remaining: 44 },
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

function formatDate(timestamp) {
  if (!timestamp) {
    return '';
  }
  const date = new Date(Number(timestamp) * 1000);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function normalizeMember(membership) {
  if (!membership || membership.status !== 'active') {
    return FALLBACK_MEMBER;
  }
  const presentation = PLAN_PRESENTATION[membership.plan_code] || PLAN_PRESENTATION.knowing;
  return {
    planCode: membership.plan_code,
    name: membership.plan_name || presentation.name,
    icon: presentation.icon,
    expiresText: `会员有效期至 ${formatDate(membership.expires_at) || '--'}`,
  };
}

function normalizeUsage(entitlements) {
  const source = entitlements || FALLBACK_ENTITLEMENTS;
  return FEATURE_ORDER.map((feature) => {
    const presentation = FEATURE_PRESENTATION[feature];
    const item = source[feature] || {};
    const total = Math.max(Number(item.total) || 0, 0);
    const remaining = Math.max(Number(item.remaining) || 0, 0);
    const used = Math.max(total - remaining, 0);
    const percent = total ? Math.min(Math.round((used / total) * 100), 100) : 0;
    return {
      feature,
      name: presentation.name,
      icon: presentation.icon,
      used,
      total,
      countText: `${used} / ${total} 次`,
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
    currentMember: FALLBACK_MEMBER,
    usageItems: normalizeUsage(FALLBACK_ENTITLEMENTS),
    addonProducts: FALLBACK_ADDONS.map(normalizeAddon),
    selectedAddon: null,
    addonQuantity: 1,
    addonTotalText: '3.99',
    addonModalVisible: false,
    addonAgreementChecked: false,
    purchaseLoading: false,
    mockPaymentAvailable: false,
  },

  onLoad() {
    this.initLayout();
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
        currentMember: FALLBACK_MEMBER,
        usageItems: normalizeUsage(FALLBACK_ENTITLEMENTS),
      });
      return Promise.resolve();
    }

    return new Promise((resolve) => {
      wx.request({
        url: `${VIP_API_BASE_URL}/me`,
        method: 'GET',
        header: { Authorization: `Bearer ${token}` },
        success: (res) => {
          if (res.statusCode === 200 && res.data) {
            this.setData({
              currentMember: normalizeMember(res.data.membership),
              usageItems: normalizeUsage(res.data.entitlements),
            });
          }
          resolve();
        },
        fail: (error) => {
          console.error('fetchVipState failed:', error);
          resolve();
        },
      });
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

  openAgreement() {
    wx.showModal({
      title: '会员服务协议',
      content: '会员服务协议页面将在支付系统正式上线前补充。当前会员和加量包均为单次购买，不会自动续费。',
      showCancel: false,
      confirmText: '我知道了',
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
      fail: () => {
        this.finishPurchaseWithError('模拟支付请求失败');
      },
    });
  },

  requestWechatPayment(payload) {
    wx.requestPayment({
      ...payload,
      success: () => {
        this.setData({
          purchaseLoading: false,
          addonModalVisible: false,
          selectedAddon: null,
          addonQuantity: 1,
          addonAgreementChecked: false,
        });
        wx.showModal({
          title: '支付结果确认中',
          content: '支付完成后，加量包权益将以后端订单查询结果为准。',
          showCancel: false,
          success: () => {
            this.fetchVipState();
          },
        });
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
