const { getShareInfo, getTimelineInfo } = require('../utils/share.js');

const API_BASE_URL = 'http://127.0.0.1:8000';

const MOOD_OPTIONS = [
  { id: 'happy', name: '开心', icon: 'happy', energy: 'high' },
  { id: 'satisfied', name: '满足', icon: 'satisfied', energy: 'medium' },
  { id: 'expectant', name: '期待', icon: 'expectant', energy: 'high' },
  { id: 'grateful', name: '感激', icon: 'grateful', energy: 'medium' },
  { id: 'calm', name: '平静', icon: 'calm', energy: 'low' },
  { id: 'relaxed', name: '放松', icon: 'relaxed', energy: 'low' },
  { id: 'secure', name: '安心', icon: 'secure', energy: 'low' },
  { id: 'focused', name: '专注', icon: 'focused', energy: 'medium' },
  { id: 'sad', name: '难过', icon: 'sad', energy: 'low' },
  { id: 'lost', name: '失落', icon: 'lost', energy: 'low' },
  { id: 'wronged', name: '委屈', icon: 'wronged', energy: 'low' },
  { id: 'lonely', name: '孤独', icon: 'lonely', energy: 'low' },
  { id: 'anxious', name: '焦虑', icon: 'anxious', energy: 'high' },
  { id: 'worried', name: '担心', icon: 'worried', energy: 'medium' },
  { id: 'irritable', name: '烦躁', icon: 'irritable', energy: 'high' },
  { id: 'panicked', name: '慌乱', icon: 'panicked', energy: 'high' },
  { id: 'angry', name: '生气', icon: 'angry', energy: 'high' },
  { id: 'annoyed', name: '厌烦', icon: 'annoyed', energy: 'medium' },
  { id: 'unwilling', name: '不甘', icon: 'unwilling', energy: 'high' },
  { id: 'hurt', name: '受伤', icon: 'hurt', energy: 'low' },
  { id: 'tired', name: '疲惫', icon: 'tired', energy: 'low' },
  { id: 'sleepy', name: '困倦', icon: 'sleepy', energy: 'low' },
  { id: 'numb', name: '麻木', icon: 'numb', energy: 'low' },
  { id: 'confused', name: '迷茫', icon: 'confused', energy: 'low' },
];

const MOOD_LABEL_TO_ID = MOOD_OPTIONS.reduce((map, item) => {
  map[item.name] = item.id;
  return map;
}, {
  兴奋: 'expectant',
  尴尬: 'confused',
});

const MOOD_SCENE_BASE = '/pkgDailyCheckin/assets/trajectory';

const MOOD_SCENE_MAP = {
  happy: `${MOOD_SCENE_BASE}/happy.jpg`,
  satisfied: `${MOOD_SCENE_BASE}/satisfied.jpg`,
  expectant: `${MOOD_SCENE_BASE}/expectant.jpg`,
  grateful: `${MOOD_SCENE_BASE}/grateful.jpg`,
  calm: `${MOOD_SCENE_BASE}/calm.jpg`,
  relaxed: `${MOOD_SCENE_BASE}/relaxed.jpg`,
  secure: `${MOOD_SCENE_BASE}/secure.jpg`,
  focused: `${MOOD_SCENE_BASE}/focused.jpg`,
  sad: `${MOOD_SCENE_BASE}/sad.jpg`,
  lost: `${MOOD_SCENE_BASE}/lost.jpg`,
  wronged: `${MOOD_SCENE_BASE}/wronged.jpg`,
  lonely: `${MOOD_SCENE_BASE}/lonely.jpg`,
  anxious: `${MOOD_SCENE_BASE}/anxious.jpg`,
  worried: `${MOOD_SCENE_BASE}/worried.jpg`,
  irritable: `${MOOD_SCENE_BASE}/irritable.jpg`,
  panicked: `${MOOD_SCENE_BASE}/panicked.jpg`,
  angry: `${MOOD_SCENE_BASE}/angry.jpg`,
  annoyed: `${MOOD_SCENE_BASE}/annoyed.jpg`,
  unwilling: `${MOOD_SCENE_BASE}/unwilling.jpg`,
  hurt: `${MOOD_SCENE_BASE}/hurt.jpg`,
  tired: `${MOOD_SCENE_BASE}/tired.jpg`,
  sleepy: `${MOOD_SCENE_BASE}/sleepy.jpg`,
  numb: `${MOOD_SCENE_BASE}/numb.jpg`,
  confused: `${MOOD_SCENE_BASE}/confused.jpg`,
};

const MOOD_TONE_MAP = {
  happy: 'sun',
  satisfied: 'sun',
  expectant: 'sun',
  grateful: 'sun',
  calm: 'blue',
  relaxed: 'green',
  secure: 'cream',
  focused: 'green',
  sad: 'blue',
  lost: 'violet',
  wronged: 'violet',
  lonely: 'night',
  anxious: 'amber',
  worried: 'blue',
  irritable: 'amber',
  panicked: 'amber',
  angry: 'rose',
  annoyed: 'rose',
  unwilling: 'violet',
  hurt: 'rose',
  tired: 'violet',
  sleepy: 'night',
  numb: 'gray',
  confused: 'violet',
};

function request(options) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token');
    wx.request({
      ...options,
      url: `${API_BASE_URL}/api/v1${options.url}`,
      header: {
        ...options.header,
        Authorization: `Bearer ${token}`,
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) resolve(res.data);
        else reject(res);
      },
      fail: reject,
    });
  });
}

function normalizeImageUrl(url) {
  if (!url) return '';
  if (/^https?:\/\//.test(url) || url.startsWith('wxfile://') || url.startsWith('cloud://')) return url;
  return `${API_BASE_URL}${url}`;
}

function normalizeMoodId(item) {
  const raw = item.mood_id || item.mood_icon || item.mood || '';
  if (MOOD_SCENE_MAP[raw]) return raw;
  return MOOD_LABEL_TO_ID[item.mood] || MOOD_LABEL_TO_ID[raw] || 'calm';
}

Page({
  data: {
    statusBarHeight: 0,
    navBarHeight: 44,
    totalNavBarHeight: 44,
    targetDate: '',
    dateLabel: '',
    isToday: false,
    moments: [],
    trendText: '今天的心情并不是固定的一种，它在不同时间里轻轻变化。',
  },

  onLoad(options) {
    this.updateNavMetrics();
    const targetDate = options.date || this.getTodayString();
    this.setData({
      targetDate,
      dateLabel: this.formatDateLabel(targetDate),
      isToday: targetDate === this.getTodayString(),
    });
    this.loadTimeline();
  },

  onShow() {
    this.updateNavMetrics();
  },

  updateNavMetrics() {
    try {
      const windowInfo = wx.getWindowInfo();
      const menuButtonInfo = wx.getMenuButtonBoundingClientRect();
      const statusBarHeight = windowInfo.statusBarHeight || 0;
      const navBarHeight = (menuButtonInfo.top - statusBarHeight) * 2 + menuButtonInfo.height;
      this.setData({
        statusBarHeight,
        navBarHeight,
        totalNavBarHeight: statusBarHeight + navBarHeight,
      });
    } catch (error) {
      this.setData({ statusBarHeight: 24, navBarHeight: 48, totalNavBarHeight: 72 });
    }
  },

  goBack() {
    wx.navigateBack({ delta: 1 });
  },

  goToRecord() {
    if (!this.data.isToday) return;
    wx.navigateTo({ url: '/pkgDailyCheckin/record' });
  },

  async loadTimeline() {
    wx.showLoading({ title: '加载中...' });
    try {
      const data = await request({ url: `/checkin/date/${this.data.targetDate}/timeline` });
      const moments = (data.moments || []).map(item => this.normalizeMoment(item));
      this.setData({
        moments,
        trendText: this.buildTrendText(moments),
      });
    } catch (error) {
      wx.showToast({ title: '加载轨迹失败', icon: 'none' });
    } finally {
      wx.hideLoading();
    }
  },

  normalizeMoment(item) {
    const tags = item.status_items && item.status_items.length
      ? item.status_items.map(status => status.label || status.name).filter(Boolean)
      : String(item.tags || '').split(',').filter(Boolean);
    const moodId = normalizeMoodId(item);
    return {
      ...item,
      moodIcon: item.mood_icon || moodId,
      moodScene: MOOD_SCENE_MAP[moodId] || MOOD_SCENE_MAP.calm,
      moodTone: MOOD_TONE_MAP[moodId] || 'blue',
      localTime: item.local_time || this.formatTimeFromTimestamp(item.recorded_at || item.timestamp),
      tags,
      imageUrls: (item.image_urls || []).map(normalizeImageUrl),
    };
  },

  buildTrendText(moments) {
    if (moments.length < 2) {
      return '今天的心情并不是固定的一种，它在不同时间里轻轻变化。';
    }
    const first = this.energyScore(moments[0]);
    const last = this.energyScore(moments[moments.length - 1]);
    const max = Math.max(...moments.map(item => this.energyScore(item)));
    const min = Math.min(...moments.map(item => this.energyScore(item)));
    if (last - first >= 1) return '今天像是慢慢亮起来了。';
    if (first - last >= 1) return '今天后半段可能有些消耗。';
    if (max - min >= 2) return '今天的情绪有一些波动。';
    return '今天的状态整体比较稳定。';
  },

  energyScore(moment) {
    const energy = moment.mood_energy || (MOOD_OPTIONS.find(item => item.id === moment.mood_id || item.name === moment.mood) || {}).energy;
    if (energy === 'high') return 3;
    if (energy === 'medium') return 2;
    return 1;
  },

  previewImage(e) {
    const { urls, current } = e.currentTarget.dataset;
    if (!urls || !urls.length) return;
    wx.previewImage({ urls, current });
  },

  getTodayString() {
    const today = new Date();
    return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
  },

  formatDateLabel(dateStr) {
    const date = new Date(`${dateStr}T00:00:00`);
    if (Number.isNaN(date.getTime())) return dateStr;
    const weekNames = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    return `${date.getMonth() + 1}月${date.getDate()}日 ${weekNames[date.getDay()]}`;
  },

  formatTimeFromTimestamp(timestamp) {
    if (!timestamp) return '';
    const date = new Date(Number(timestamp) * 1000);
    if (Number.isNaN(date.getTime())) return '';
    return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
  },

  onShareAppMessage() {
    return getShareInfo();
  },

  onShareTimeline() {
    return getTimelineInfo();
  },
});
