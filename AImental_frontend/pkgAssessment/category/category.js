const { getShareInfo, getTimelineInfo } = require('../../utils/share.js');

const SERVER_BASE_URL = 'http://127.0.0.1:8000';
const DEFAULT_GROUP = '心理健康';
const DEFAULT_ICON_PATH = '/images/assessment/default.png';

const GROUPS = {
  '心理健康': {
    key: 'health',
    title: '心理健康',
    subtitle: '关注情绪状态，关爱内心健康',
    hero: '/images/assessment/category/health-hero.png',
    order: ['SDS', 'BDI-II', 'SAS', 'BRMS', 'SAD', 'IAS', 'Lonely']
  },
  '自我人格': {
    key: 'personality',
    title: '自我人格',
    subtitle: '探索性格特质，认识独特的自己',
    hero: '/images/assessment/category/personality-hero.png',
    order: ['SES', 'APS', 'CLT', 'mbti-93']
  },
  '亲密关系': {
    key: 'relationship',
    title: '亲密关系',
    subtitle: '理解人际关系，建立深度联结',
    hero: '/images/assessment/category/relationship-hero.png',
    order: ['AAS', 'ECR', 'LAMT', 'LDCT']
  },
  '趣味探索': {
    key: 'interest',
    title: '趣味探索',
    subtitle: '轻松有趣，发现更多可能的自己',
    hero: '/images/assessment/category/interest-hero.png',
    order: ['TPS', 'ICI', 'REAL-MAJOR-V1', 'AGLT']
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
};

const SCALE_DISPLAY_META = {
  SDS: {
    title: '抑郁量表',
    description: '了解近期低落与抑郁感受',
    tagTone: 'blue'
  },
  'BDI-II': {
    title: '抑郁量表',
    description: '了解近期低落与抑郁感受',
    tagTone: 'blue',
    iconKey: 'bdi-ii'
  },
  SAS: {
    title: '焦虑量表',
    description: '评估焦虑与紧张水平',
    tagTone: 'purple'
  },
  BRMS: {
    title: '轻躁狂量表',
    description: '识别情绪高涨与冲动倾向',
    tagTone: 'orange'
  },
  SAD: {
    title: '社交回避量表',
    description: '了解回避社交的倾向',
    tagTone: 'green'
  },
  IAS: {
    title: '互动焦虑量表',
    description: '评估人际互动中的焦虑感',
    tagTone: 'rose'
  },
  Lonely: {
    title: '孤独感量表',
    description: '觉察内在孤独与连接需求',
    tagTone: 'blue'
  },
  SES: {
    title: '自尊量表',
    description: '了解自我价值感与接纳程度',
    tagTone: 'rose'
  },
  APS: {
    title: '完美主义量表',
    description: '觉察对标准与成就的期待',
    tagTone: 'purple'
  },
  CLT: {
    title: '创造力水平测试',
    description: '帮助了解个人思维与行为倾向',
    tagTone: 'green'
  },
  'mbti-93': {
    title: '人格类型测评',
    description: '探索你的性格偏好与相处方式',
    tagTone: 'blue'
  },
  AAS: {
    title: '成人依恋量表',
    description: '了解自己在亲密关系中的依恋模式',
    tagTone: 'rose'
  },
  ECR: {
    title: '亲密关系经历量表',
    description: '探索关系中的安全感与焦虑回避倾向',
    tagTone: 'purple'
  },
  LAMT: {
    title: '爱情态度测验',
    description: '帮助理解你对爱情与陪伴的看法',
    tagTone: 'orange'
  },
  LDCT: {
    title: '恋爱沟通测验',
    description: '觉察互动中的表达方式与相处习惯',
    tagTone: 'green'
  },
  TPS: {
    title: '性格类型测试',
    description: '测一测你的性格类型，看看你是哪个小宇宙！',
    subnote: '趣味性格探索',
    tagTone: 'orange'
  },
  ICI: {
    title: '趣味自我概念测试',
    description: '探索你眼中的自己，发现独特的闪光点！',
    subnote: '自我认知小游戏',
    tagTone: 'blue'
  },
  'REAL-MAJOR-V1': {
    title: '理想职业探索',
    description: '如果没有限制，你最想做什么？一起找找你的理想方向！',
    subnote: '职业兴趣探索',
    tagTone: 'orange'
  },
  AGLT: {
    title: '天赋潜能小测验',
    description: '解锁你的隐藏天赋，看看你有哪些超能力！',
    subnote: '趣味天赋发现',
    tagTone: 'orange'
  }
};

function request(options) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token');
    wx.request({
      ...options,
      url: `${SERVER_BASE_URL}/api/v1${options.url}`,
      header: {
        ...options.header,
        'Authorization': `Bearer ${token}`
      },
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
    const systemInfo = wx.getSystemInfoSync();
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
    const displayMeta = SCALE_DISPLAY_META[scale.short_name] || {};

    return {
      ...scale,
      displayGroup,
      displayGroupOrder,
      displayOrder,
      displayTitle: displayMeta.title || scale.name,
      displayDescription: displayMeta.description || scale.description || '',
      displaySubnote: displayMeta.subnote || '',
      tagTone: displayMeta.tagTone || 'orange',
      iconPath: this.getScaleIconPath(displayMeta.iconKey || scale.short_name)
    };
  },

  getScaleIconPath(shortName) {
    const normalizedName = (shortName || 'default').toLowerCase();
    return `/images/assessment/scale-icons/${normalizedName}.png`;
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
    wx.navigateTo({ url: `/pkgAssessment/intro/intro?id=${scaleId}` });
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
