const SERVER_BASE_URL = 'https://api.feelyourself.cn';
const VIP_API_BASE_URL = `${SERVER_BASE_URL}/api/v1/vip`;

const TABS = [
  { key: 'all', label: '全部' },
  { key: 'addon', label: '加量包' },
  { key: 'membership', label: '会员' },
];

const PRODUCT_PRESENTATION = {
  vip_light: {
    type: 'membership',
    name: '轻语会员',
    icon: 'https://assets.feelyourself.cn/miniprogram/assets/v1/images/vip/plan-light.png',
    detail: '30 天',
  },
  vip_knowing: {
    type: 'membership',
    name: '相知会员',
    icon: 'https://assets.feelyourself.cn/miniprogram/assets/v1/images/vip/plan-knowing.png',
    detail: '30 天',
  },
  vip_companion: {
    type: 'membership',
    name: '长伴会员',
    icon: 'https://assets.feelyourself.cn/miniprogram/assets/v1/images/vip/plan-companion.png',
    detail: '30 天',
  },
  addon_tree_500: {
    type: 'addon',
    name: '树洞加量包',
    icon: 'https://assets.feelyourself.cn/miniprogram/assets/v1/images/vip/feature-tree-hole.png',
    detail: '+ 500 次',
  },
  addon_community_500: {
    type: 'addon',
    name: '社区加量包',
    icon: 'https://assets.feelyourself.cn/miniprogram/assets/v1/images/vip/feature-community.png',
    detail: '+ 500 次',
  },
  addon_mood_50: {
    type: 'addon',
    name: '心情分析加量包',
    icon: 'https://assets.feelyourself.cn/miniprogram/assets/v1/images/vip/feature-mood-analysis.png',
    detail: '+ 50 次',
  },
  addon_assessment_50: {
    type: 'addon',
    name: '测评分析加量包',
    icon: 'https://assets.feelyourself.cn/miniprogram/assets/v1/images/vip/feature-assessment-analysis.png',
    detail: '+ 50 次',
  },
};

const STATUS_TEXT = {
  pending: '待支付',
  paid: '处理中',
  fulfillment_pending: '到账中',
  fulfilled: '已完成',
  closed: '已关闭',
  refunded: '已退款',
};

function formatPrice(amountFen) {
  return `¥${((Number(amountFen) || 0) / 100).toFixed(2)}`;
}

function formatDateTime(timestamp) {
  if (!timestamp) {
    return '';
  }
  const date = new Date(Number(timestamp) * 1000);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hour = String(date.getHours()).padStart(2, '0');
  const minute = String(date.getMinutes()).padStart(2, '0');
  const second = String(date.getSeconds()).padStart(2, '0');
  return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
}

function normalizeOrder(order) {
  const snapshot = order.product_snapshot || {};
  const presentation = PRODUCT_PRESENTATION[order.product_code] || {};
  const quantity = Math.max(Number(snapshot.quantity) || 1, 1);
  const type = presentation.type || order.product_type || 'addon';
  const amount = Number(snapshot.amount || snapshot.unit_amount || 0);
  const detail = type === 'addon' && amount
    ? `+ ${amount} 次`
    : (presentation.detail || '30 天');
  const name = presentation.name || snapshot.name || order.product_code;

  return {
    id: order.id,
    type,
    icon: presentation.icon || 'https://assets.feelyourself.cn/miniprogram/assets/v1/images/vip/plan-knowing.png',
    title: type === 'membership' ? `${name}（30天）` : `${name} × ${quantity}`,
    detail,
    priceText: formatPrice(order.amount_fen),
    statusText: STATUS_TEXT[order.status] || order.status || '',
    statusClass: order.status === 'fulfilled' ? 'done' : 'pending',
    timeText: formatDateTime(order.paid_at || order.created_at),
    createdAt: Number(order.created_at) || 0,
  };
}

Page({
  data: {
    statusBarHeight: 24,
    tabs: TABS,
    activeTab: 'all',
    records: [],
    filteredRecords: [],
    loading: false,
    emptyText: '还没有购买记录',
  },

  onLoad() {
    this.initLayout();
    this.fetchRecords();
  },

  onPullDownRefresh() {
    this.fetchRecords().finally(() => {
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

  fetchRecords() {
    const token = wx.getStorageSync('token');
    if (!token) {
      this.setData({
        records: [],
        filteredRecords: [],
        emptyText: '登录后查看购买记录',
      });
      return Promise.resolve();
    }

    this.setData({ loading: true });
    return new Promise((resolve) => {
      wx.request({
        url: `${VIP_API_BASE_URL}/records`,
        method: 'GET',
        header: { Authorization: `Bearer ${token}` },
        success: (res) => {
          if (res.statusCode === 200 && res.data && Array.isArray(res.data.orders)) {
            const records = res.data.orders
              .map(normalizeOrder)
              .sort((left, right) => right.createdAt - left.createdAt);
            this.setData({ records, loading: false });
            this.applyFilter(this.data.activeTab, records);
            resolve();
            return;
          }
          this.setData({
            records: [],
            filteredRecords: [],
            loading: false,
            emptyText: '购买记录暂时加载失败',
          });
          resolve();
        },
        fail: () => {
          this.setData({
            loading: false,
            emptyText: '网络异常，请稍后重试',
          });
          resolve();
        },
      });
    });
  },

  switchTab(event) {
    const key = event.currentTarget.dataset.key;
    if (!key || key === this.data.activeTab) {
      return;
    }
    this.applyFilter(key, this.data.records);
  },

  applyFilter(activeTab, records = this.data.records) {
    const filteredRecords = activeTab === 'all'
      ? records
      : records.filter((item) => item.type === activeTab);
    const emptyTextMap = {
      all: '还没有购买记录',
      addon: '还没有加量包购买记录',
      membership: '还没有会员购买记录',
    };
    this.setData({
      activeTab,
      filteredRecords,
      emptyText: emptyTextMap[activeTab] || '还没有购买记录',
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
