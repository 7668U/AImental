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
    title: '拖延倾向测评',
    description: '理解任务启动阻力与行动节奏',
    tagTone: 'purple'
  },
  CLT: {
    title: '创造力倾向测试',
    description: '探索好奇心、联想力与创意落地方式',
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
    title: '潜意识测试',
    description: '从第一反应的意象选择里，看见你的内在倾向',
    subnote: '潜意识联想探索',
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
    description: '从任务偏好与工作风格里，看见更适合你的职业方向',
    subnote: '职业方向测试',
    tagTone: 'orange'
  },
  AGLT: {
    title: '天赋雷达：天赋与潜能测试',
    description: '探索你身上的天赋信号，发现还没完全亮起来的潜能！',
    subnote: '天赋扫描',
    tagTone: 'orange'
  },
  RFLT: {
    title: '近期运势预测',
    description: '测测你的近期好运，抽一张专属好运签！',
    subnote: '近期好运签',
    tagTone: 'orange',
    iconKey: 'rflt'
  },
  'SOUL-DRINK': {
    iconKey: 'soul-drink-v2'
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
