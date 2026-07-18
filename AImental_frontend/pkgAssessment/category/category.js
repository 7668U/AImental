const { getShareInfo, getTimelineInfo } = require('../../utils/share.js');
const { getScaleDisplayMeta, getScaleDisplayName, getScaleIconName } = require('../../utils/assessment-display.js');

const SERVER_BASE_URL = 'https://api.feelyourself.cn';
const DEFAULT_GROUP = '心理健康';
const DEFAULT_ICON_PATH = 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/images/assessment/default.png';

const GROUPS = {
  '心理健康': {
    key: 'health',
    title: '心理健康',
    subtitle: '关注情绪状态，关爱内心健康',
    hero: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgAssessment/images/category/health-hero.png',
    order: ['SDS', 'BDI-II', 'SAS', 'BRMS', 'SAD', 'IAS', 'Lonely']
  },
  '自我人格': {
    key: 'personality',
    title: '自我人格',
    subtitle: '探索性格特质，认识独特的自己',
    hero: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgAssessment/images/category/personality-hero.png',
    order: ['SES', 'APS', 'CLT', 'mbti-93']
  },
  '亲密关系': {
    key: 'relationship',
    title: '亲密关系',
    subtitle: '理解人际关系，建立深度联结',
    hero: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgAssessment/images/category/relationship-hero.png',
    order: ['AAS', 'ECR', 'LAMT', 'LDCT']
  },
  '趣味探索': {
    key: 'interest',
    title: '趣味探索',
    subtitle: '轻松有趣，发现更多可能的自己',
    hero: 'https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgAssessment/images/category/interest-hero.png',
    order: ['TPS', 'ICI', 'REAL-MAJOR-V1', 'AGLT', 'RFLT']
  }
};

const GROUP_ORDER = Object.keys(GROUPS).reduce((result, groupName, index) => {
  result[groupName] = index + 1;
  return result;
}, {});

const LOCAL_ASSESSMENT_GROUPS = {
  SDS: ['心理健康', 1],
  'BDI-II': ['心理健康', 1],
  SAS: ['心理健康', 2],
  BRMS: ['心理健康', 3],
  SAD: ['心理健康', 4],
  IAS: ['心理健康', 5],
  Lonely: ['心理健康', 6],
  SES: ['自我人格', 1],
  APS: ['自我人格', 2],
  CLT: ['自我人格', 3],
  'mbti-93': ['自我人格', 4],
  AAS: ['亲密关系', 1],
  ECR: ['亲密关系', 2],
  LAMT: ['亲密关系', 3],
  LDCT: ['亲密关系', 4],
  TPS: ['趣味探索', 1],
  ICI: ['趣味探索', 2],
  'REAL-MAJOR-V1': ['趣味探索', 3],
  AGLT: ['趣味探索', 4],
  RFLT: ['趣味探索', 5],
};

function request(options) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token');
    const header = { ...options.header };
    if (token) {
      header.Authorization = `Bearer ${token}`;
    }

    wx.request({
      ...options,
      url: `${SERVER_BASE_URL}/api/v1${options.url}`,
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

Page({
  data: {
    statusBarHeight: 0,
    groupName: DEFAULT_GROUP,
    groupMeta: GROUPS[DEFAULT_GROUP],
    scaleList: [],
    isLoading: true,
    isError: false
  },

  onLoad(options) {
    const systemInfo = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
    const decodedGroup = options.group ? decodeURIComponent(options.group) : DEFAULT_GROUP;
    const groupName = GROUPS[decodedGroup] ? decodedGroup : DEFAULT_GROUP;
    this.setData({
      statusBarHeight: systemInfo.statusBarHeight,
      groupName,
      groupMeta: GROUPS[groupName]
    });
    this.fetchScaleList();
  },

  async fetchScaleList() {
    this.setData({ isLoading: true, isError: false });
    try {
      const data = await request({ url: '/assessments/' });
      const processedList = (data || [])
        .map(scale => this.normalizeScaleForDisplay(scale))
        .filter(scale => scale.displayGroup === this.data.groupName)
        .sort((a, b) => a.displayOrder - b.displayOrder || (a.name || '').localeCompare(b.name || '', 'zh-Hans-CN'));

      this.setData({
        scaleList: processedList,
        isLoading: false
      });
    } catch (error) {
      console.error('fetch category scales failed:', error);
      this.setData({ isLoading: false, isError: true });
    } finally {
      wx.stopPullDownRefresh();
    }
  },

  onPullDownRefresh() {
    this.fetchScaleList();
  },

  normalizeScaleForDisplay(scale) {
    const localMeta = LOCAL_ASSESSMENT_GROUPS[scale.short_name] || [];
    const displayGroup = scale.display_group || localMeta[0] || scale.category || '其他';
    const displayGroupOrder = scale.display_group_order || GROUP_ORDER[displayGroup] || 99;
    const displayOrder = scale.display_order || localMeta[1] || 99;
    const displayMeta = getScaleDisplayMeta(scale.short_name);
    const displayTitle = getScaleDisplayName(scale.short_name, scale.name);

    return {
      ...scale,
      displayGroup,
      displayGroupOrder,
      displayOrder,
      displayTitle,
      displayDescription: displayMeta.description || scale.description || '',
      displaySubnote: displayMeta.subnote || '',
      tagTone: displayMeta.tagTone || 'orange',
      iconPath: this.getScaleIconPath(scale.short_name)
    };
  },

  getScaleIconPath(shortName) {
    return `https://assets.feelyourself.cn/miniprogram/assets/releases/20260718-1/pkgAssessment/images/scale-icons/${getScaleIconName(shortName)}.png`;
  },

  goBack() {
    wx.navigateBack({
      fail() {
        wx.switchTab({ url: '/pages/assessment/index' });
      }
    });
  },

  goToTest(e) {
    const scaleId = e.currentTarget.dataset.id;
    const displayTitle = encodeURIComponent(e.currentTarget.dataset.title || '');
    wx.navigateTo({ url: `/pkgAssessment/intro/intro?id=${scaleId}&title=${displayTitle}` });
  },

  handleIconError(e) {
    const errorIndex = e.currentTarget.dataset.index;
    const updatedPath = `scaleList[${errorIndex}].iconPath`;
    this.setData({ [updatedPath]: DEFAULT_ICON_PATH });
  },

  onShareAppMessage() {
    return getShareInfo();
  },

  onShareTimeline() {
    return getTimelineInfo();
  }
});
