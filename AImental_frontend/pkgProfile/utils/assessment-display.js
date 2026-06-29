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

function getScaleDisplayMeta(shortName) {
  return SCALE_DISPLAY_META[shortName] || {};
}

function getScaleDisplayName(shortName, fallbackName = '') {
  return getScaleDisplayMeta(shortName).title || fallbackName || '';
}

function getScaleIconName(shortName) {
  const displayMeta = getScaleDisplayMeta(shortName);
  const iconName = displayMeta.iconKey || shortName || 'default';
  return String(iconName).toLowerCase();
}

module.exports = {
  SCALE_DISPLAY_META,
  getScaleDisplayMeta,
  getScaleDisplayName,
  getScaleIconName
};
