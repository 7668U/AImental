// pages/paper-airplane/index.js
const API_BASE_URL = 'https://api.feelyourself.cn/api/v1';

function request(options) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token');
    if (!token) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return reject('No token');
    }
    wx.request({
      ...options,
      url: `${API_BASE_URL}${options.url}`,
      header: {
        ...options.header,
        'Authorization': `Bearer ${token}`
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          wx.showToast({ title: res.data.detail || '请求失败', icon: 'none' });
          reject(res);
        }
      },
      fail(err) {
        wx.showToast({ title: '网络错误', icon: 'none' });
        reject(err);
      }
    });
  });
}

const { getShareInfo, getTimelineInfo } = require('../../utils/share.js');
const { loginWithBackend } = require('../../utils/auth.js');

const PAPER_PLANE_ICONS = [
  'paper_plane_01_01.png',
  'paper_plane_01_02.png',
  'paper_plane_01_03.png',
  'paper_plane_01_04.png',
  'paper_plane_02_01.png',
  'paper_plane_02_02.png',
  'paper_plane_02_03.png',
  'paper_plane_02_04.png',
  'paper_plane_03_01.png',
  'paper_plane_03_02.png',
  'paper_plane_03_03.png',
  'paper_plane_03_04.png',
  'paper_plane_04_01.png',
  'paper_plane_04_02.png',
  'paper_plane_04_03.png',
  'paper_plane_04_04.png',
  'paper_plane_05_01.png',
  'paper_plane_05_02.png',
  'paper_plane_05_03.png',
  'paper_plane_05_04.png',
  'paper_plane_06_01.png',
  'paper_plane_06_02.png',
  'paper_plane_06_03.png',
  'paper_plane_06_04.png',
].map((name, index) => ({
  number: `P${String(index + 1).padStart(2, '0')}`,
  path: `https://assets.feelyourself.cn/miniprogram/assets/v1/images/paper-airplane/flying/${name}`
}));

const AIRPLANE_SAFE_SLOTS = [
  { top: 300, left: 620, rotate: -22, size: 84 },
  { top: 460, left: 86, rotate: -14, size: 78 },
  { top: 510, left: 595, rotate: 15, size: 82 },
  { top: 610, left: 126, rotate: -12, size: 76 },
  { top: 650, left: 630, rotate: 12, size: 76 },
  { top: 760, left: 84, rotate: 17, size: 80 },
  { top: 780, left: 590, rotate: -18, size: 78 },
  { top: 890, left: 188, rotate: 13, size: 76 },
  { top: 930, left: 505, rotate: -12, size: 80 },
  { top: 1026, left: 338, rotate: 16, size: 74 },
];

function buildPositionedAirplane(airplane, index) {
  const slot = AIRPLANE_SAFE_SLOTS[index % AIRPLANE_SAFE_SLOTS.length];
  const asset = getAirplaneAsset(airplane, index);
  return {
    ...airplane,
    top: slot.top,
    left: slot.left,
    rotate: slot.rotate,
    size: slot.size,
    assetNumber: asset.number,
    assetPath: asset.path,
    icon: asset.path,
    delay: `${(index % 4) * 0.9}s`,
    duration: `${12 + (index % 3) * 2}s`,
  };
}

function getAirplaneAsset(airplane, index = 0) {
  if (airplane && airplane.asset_path) {
    return {
      number: airplane.asset_number || buildFallbackAssetNumber(airplane.id, index),
      path: airplane.asset_path
    };
  }

  if (airplane && airplane.asset_number) {
    const matchedAsset = PAPER_PLANE_ICONS.find(asset => asset.number === airplane.asset_number);
    if (matchedAsset) {
      return matchedAsset;
    }
  }

  if (airplane && airplane.id) {
    return PAPER_PLANE_ICONS[getStableAssetIndex(airplane.id)];
  }

  return PAPER_PLANE_ICONS[Math.floor(Math.random() * PAPER_PLANE_ICONS.length)];
}

function buildFallbackAssetNumber(airplaneId, index) {
  const source = airplaneId || index + 1;
  return `P${String(getStableAssetIndex(source) + 1).padStart(2, '0')}`;
}

function getStableAssetIndex(source) {
  const numericSource = Math.abs(Number(source));
  if (!numericSource) {
    return 0;
  }

  return (numericSource - 1) % PAPER_PLANE_ICONS.length;
}

function formatBasketTime(value) {
  if (!value) {
    return '刚刚收下';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '悄悄收下';
  }

  const month = date.getMonth() + 1;
  const day = date.getDate();
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  return `${month}月${day}日 ${hours}:${minutes}`;
}

function normalizeCollectedAirplane(airplane, index) {
  const asset = getAirplaneAsset(airplane, index);
  const collectedTime = airplane.collected_time || airplane.create_time;

  return {
    ...airplane,
    assetNumber: asset.number,
    assetPath: asset.path,
    collectedTime,
    collectedTimeLabel: formatBasketTime(collectedTime),
    toneClass: `basket-tone-${index % 4}`
  };
}

function formatReadMessage(message) {
  const text = String(message || '').trim();
  if (!text) {
    return '';
  }

  return text
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .split('\n')
    .map(paragraph => {
      const lines = [];
      let line = '';
      paragraph.split('').forEach(char => {
        line += char;
        if (line.length >= 10 || /[，。！？；、,.!?;]/.test(char)) {
          lines.push(line);
          line = '';
        }
      });
      if (line) {
        lines.push(line);
      }
      return lines.join('\n');
    })
    .join('\n');
}

Page({
  data: {
    isLoggedIn: false,
    showWriteModal: false,
    showReadModal: false,
    showBasketModal: false,
    newMessage: '',
    openedMessage: '',
    openedAirplaneId: null,
    openedAirplaneCollected: false,
    openedFromBasket: false,
    openedAirplaneAssetNumber: '',
    openedAirplaneAssetPath: '',
    airplanes: [],
    collectedAirplanes: [],
  },

  onLoad() {
    this.checkLoginStatus();
  },

  onShow() {
    this.checkLoginStatus();
  },

  checkLoginStatus() {
    const token = wx.getStorageSync('token');

    if (!token) {
      this.setData({
        isLoggedIn: false,
        showWriteModal: false,
        showReadModal: false,
        showBasketModal: false,
        airplanes: [],
        collectedAirplanes: [],
      });
      return;
    }

    this.setData({ isLoggedIn: true });
    if (this.data.airplanes.length === 0) {
      this.fetchAirplanes();
    }
  },

  handleLogin() {
    wx.showLoading({ title: '登录中...' });
    loginWithBackend(API_BASE_URL)
      .then((tokenRes) => {
        if (!tokenRes || !tokenRes.access_token) {
          throw new Error('登录接口未返回 token');
        }
        wx.setStorageSync('token', tokenRes.access_token);
        wx.hideLoading();
        wx.showToast({ title: '登录成功', icon: 'success' });
        this.checkLoginStatus();
      })
      .catch((error) => {
        wx.hideLoading();
        console.error('纸飞机登录失败:', error);
        wx.showToast({ title: '登录失败，请重试', icon: 'none' });
      });
  },

  async fetchAirplanes() {
    wx.showLoading({ title: '加载纸飞机...' });
    try {
      const availableAirplanes = await request({ url: '/airplane/available?limit=10' });
      wx.hideLoading();

      const positionedAirplanes = availableAirplanes
        .slice(0, AIRPLANE_SAFE_SLOTS.length)
        .map(buildPositionedAirplane);

      this.setData({
        airplanes: positionedAirplanes
      });
    } catch (error) {
      wx.hideLoading();
      console.error("获取纸飞机失败", error);
    }
  },

  async addOneNewAirplane() {
    try {
      const newAirplanes = await request({ url: '/airplane/available?limit=1' });
      if (newAirplanes && newAirplanes.length > 0) {
        const newAirplane = newAirplanes[0];
        const positionedNewAirplane = buildPositionedAirplane(newAirplane, this.data.airplanes.length);
        this.setData({
          airplanes: [...this.data.airplanes, positionedNewAirplane]
        });
      } else {
        console.log("No new airplanes available to add.");
      }
    } catch (error) {
      console.error("添加新纸飞机失败", error);
    }
  },

  hideModals() {
    this.setData({
      showWriteModal: false,
      showReadModal: false,
      showBasketModal: false,
    });
  },

  onThrowClick() {
    this.setData({ showWriteModal: true, newMessage: '' });
  },

  async onAirplaneTap(e) {
    const airplaneId = e.currentTarget.dataset.id;
    const currentAirplane = this.data.airplanes.find(ap => String(ap.id) === String(airplaneId));
    wx.showLoading({ title: '正在捡纸飞机...' });
    try {
      const pickedAirplane = await request({
        url: `/airplane/${airplaneId}/pickup`,
        method: 'POST'
      });
      wx.hideLoading();

      const updatedAirplanes = this.data.airplanes.filter(ap => String(ap.id) !== String(airplaneId));
      this.setData({
        airplanes: updatedAirplanes,
        openedMessage: formatReadMessage(pickedAirplane.message),
        openedAirplaneId: pickedAirplane.id,
        openedAirplaneCollected: false,
        openedFromBasket: false,
        openedAirplaneAssetNumber: currentAirplane ? currentAirplane.assetNumber : '',
        openedAirplaneAssetPath: currentAirplane ? currentAirplane.assetPath : '',
        showReadModal: true,
      });

    } catch (error) {
      wx.hideLoading();
      console.error("捡纸飞机失败", error);
    }
  },

  onMessageInput(e) {
    this.setData({ newMessage: e.detail.value });
  },

  releaseOpenedAirplane() {
    const shouldRefresh = !!this.data.openedAirplaneId;
    this.setData({
      showReadModal: false,
      openedAirplaneId: null,
      openedAirplaneCollected: false,
      openedFromBasket: false,
      openedAirplaneAssetNumber: '',
      openedAirplaneAssetPath: '',
    });
    if (shouldRefresh) {
      this.addOneNewAirplane();
    }
  },

  async sendAirplane() {
    const message = this.data.newMessage.trim();
    if (!message) {
      wx.showToast({ title: '内容不能为空哦', icon: 'none' });
      return;
    }

    wx.showLoading({ title: '正在放飞...' });
    try {
      await request({
        url: '/airplane/throw',
        method: 'POST',
        data: { message: message },
      });
      wx.hideLoading();
      this.hideModals();
      wx.showToast({ title: '放飞成功！', icon: 'success' });
      this.addOneNewAirplane();
    } catch (error) {
      wx.hideLoading();
      console.error("发送失败", error);
    }
  },

  async collectOpenedAirplane() {
    if (!this.data.openedAirplaneId || this.data.openedAirplaneCollected) {
      this.hideModals();
      return;
    }

    wx.showLoading({ title: '正在收起...' });
    try {
      await request({
        url: `/airplane/${this.data.openedAirplaneId}/collect`,
        method: 'POST',
        data: {
          asset_number: this.data.openedAirplaneAssetNumber,
          asset_path: this.data.openedAirplaneAssetPath
        }
      });
      wx.hideLoading();
      wx.showToast({ title: '已收进飞机篓', icon: 'success' });
      this.setData({
        openedAirplaneCollected: true,
        openedAirplaneId: null,
        openedFromBasket: false,
        openedAirplaneAssetNumber: '',
        openedAirplaneAssetPath: '',
        showReadModal: false,
      });
      this.addOneNewAirplane();
    } catch (error) {
      wx.hideLoading();
      console.error("收起纸飞机失败", error);
    }
  },

  async openBasket() {
    this.setData({ showBasketModal: true });
    wx.showLoading({ title: '打开飞机篓...' });
    try {
      const collectedAirplanes = await request({ url: '/airplane/collected' });
      wx.hideLoading();
      const normalizedAirplanes = collectedAirplanes.map(normalizeCollectedAirplane);
      this.setData({
        collectedAirplanes: normalizedAirplanes
      });
    } catch (error) {
      wx.hideLoading();
      console.error("获取飞机篓失败", error);
    }
  },

  openCollectedAirplane(e) {
    const index = e.currentTarget.dataset.index;
    const selectedAirplane = this.data.collectedAirplanes[index];
    if (!selectedAirplane) {
      return;
    }

    this.setData({
      showBasketModal: false,
      showReadModal: true,
      openedMessage: formatReadMessage(selectedAirplane.message),
      openedAirplaneId: selectedAirplane.id,
      openedAirplaneCollected: true,
      openedFromBasket: true,
      openedAirplaneAssetNumber: selectedAirplane.assetNumber,
      openedAirplaneAssetPath: selectedAirplane.assetPath
    });
  },

  closeReadModal() {
    if (this.data.openedFromBasket) {
      this.returnOpenedAirplaneToBasket();
      return;
    }

    this.releaseOpenedAirplane();
  },

  returnOpenedAirplaneToBasket() {
    this.setData({
      showReadModal: false,
      showBasketModal: true,
      openedAirplaneId: null,
      openedAirplaneCollected: false,
      openedFromBasket: false,
      openedAirplaneAssetNumber: '',
      openedAirplaneAssetPath: '',
    });
  },

  async discardCollectedAirplane() {
    if (!this.data.openedAirplaneId) {
      this.returnOpenedAirplaneToBasket();
      return;
    }

    wx.showLoading({ title: '正在丢弃...' });
    try {
      await request({
        url: `/airplane/${this.data.openedAirplaneId}/collect`,
        method: 'DELETE'
      });
      wx.hideLoading();
      wx.showToast({ title: '已从纸篓丢弃', icon: 'success' });
      const discardedId = this.data.openedAirplaneId;
      this.setData({
        showReadModal: false,
        showBasketModal: true,
        openedAirplaneId: null,
        openedAirplaneCollected: false,
        openedFromBasket: false,
        openedAirplaneAssetNumber: '',
        openedAirplaneAssetPath: '',
        collectedAirplanes: this.data.collectedAirplanes.filter(item => String(item.id) !== String(discardedId))
      });
    } catch (error) {
      wx.hideLoading();
      console.error("丢弃纸飞机失败", error);
    }
  },

  onShareAppMessage() {
    return getShareInfo({
      title: '把心事折成纸飞机，让它轻轻飞出去',
      path: '/pages/paper-airplane/index'
    });
  },

  onShareTimeline() {
    return getTimelineInfo({
      title: '把心事折成纸飞机，让它轻轻飞出去'
    });
  }
});
