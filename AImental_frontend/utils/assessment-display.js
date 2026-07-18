const SCALE_DISPLAY_META = {
  SDS: {
    title: '抑郁量表',
    description: '了解近期低落与抑郁感受',
    tagTone: 'blue',
    resultSectionTitles: {
      interpretation: '情绪状态解读',
      recommendation: '自我照护建议'
    }
  },
  'BDI-II': {
    title: '抑郁量表',
    description: '了解近期低落与抑郁感受',
    tagTone: 'blue',
    iconKey: 'bdi-ii',
    resultSectionTitles: {
      interpretation: '情绪状态解读',
      recommendation: '自我照护建议'
    }
  },
  SAS: {
    title: '焦虑量表',
    description: '评估焦虑与紧张水平',
    tagTone: 'purple',
    resultSectionTitles: {
      interpretation: '焦虑状态解读',
      recommendation: '情绪调节建议'
    }
  },
  BRMS: {
    title: '轻躁狂量表',
    description: '识别情绪高涨与冲动倾向',
    tagTone: 'orange',
    resultSectionTitles: {
      interpretation: '情绪能量解读',
      recommendation: '自我照护建议'
    }
  },
  SAD: {
    title: '社交回避量表',
    description: '了解回避社交的倾向',
    tagTone: 'green',
    resultSectionTitles: {
      interpretation: '社交回避解读',
      recommendation: '社交调节建议'
    }
  },
  IAS: {
    title: '互动焦虑量表',
    description: '评估人际互动中的焦虑感',
    tagTone: 'rose',
    resultSectionTitles: {
      interpretation: '社交互动解读',
      recommendation: '互动调节建议'
    }
  },
  Lonely: {
    title: '孤独感量表',
    description: '觉察内在孤独与连接需求',
    tagTone: 'blue',
    resultSectionTitles: {
      interpretation: '连接感受解读',
      recommendation: '关系联结建议'
    }
  },
  DLS: {
    resultSectionTitles: {
      interpretation: '连接感受解读',
      recommendation: '关系联结建议'
    }
  },
  SES: {
    title: '自尊量表',
    description: '了解自我价值感与接纳程度',
    tagTone: 'rose',
    resultSectionTitles: {
      interpretation: '自我价值感解读',
      recommendation: '自我支持建议'
    }
  },
  SEI: {
    resultSectionTitles: {
      interpretation: '自我价值感解读',
      recommendation: '自我支持建议'
    }
  },
  APS: {
    title: '拖延倾向测评',
    description: '理解任务启动阻力与行动节奏',
    tagTone: 'purple',
    resultSectionTitles: {
      interpretation: '拖延模式解读',
      recommendation: '行动调整建议'
    }
  },
  CLT: {
    title: '创造力倾向测试',
    description: '探索好奇心、联想力与创意落地方式',
    tagTone: 'green',
    resultSectionTitles: {
      interpretation: '创造力画像',
      recommendation: '创意落地建议'
    }
  },
  'mbti-93': {
    title: '人格类型测评',
    description: '探索你的性格偏好与相处方式',
    tagTone: 'blue',
    resultSectionTitles: {
      interpretation: '人格画像',
      recommendation: '发展方向建议'
    }
  },
  AAS: {
    title: '成人依恋量表',
    description: '了解自己在亲密关系中的依恋模式',
    tagTone: 'rose',
    resultSectionTitles: {
      interpretation: '依恋模式解读',
      recommendation: '关系成长建议'
    }
  },
  ECR: {
    title: '亲密关系经历量表',
    description: '探索关系中的安全感与焦虑回避倾向',
    tagTone: 'purple',
    resultSectionTitles: {
      interpretation: '依恋模式解读',
      recommendation: '关系成长建议'
    }
  },
  LAMT: {
    title: '爱情态度测验',
    description: '帮助理解你对爱情与陪伴的看法',
    tagTone: 'orange',
    resultSectionTitles: {
      interpretation: '爱情态度解读',
      recommendation: '关系相处建议'
    }
  },
  'LAMT-V1': {
    resultSectionTitles: {
      interpretation: '爱情态度解读',
      recommendation: '关系相处建议'
    }
  },
  LDCT: {
    title: '恋爱沟通测验',
    description: '觉察互动中的表达方式与相处习惯',
    tagTone: 'green',
    resultSectionTitles: {
      interpretation: '恋爱沟通画像',
      recommendation: '沟通练习建议'
    }
  },
  'LDCT-FUN': {
    resultSectionTitles: {
      interpretation: '恋爱沟通画像',
      recommendation: '沟通练习建议'
    }
  },
  TPS: {
    title: '潜意识测试',
    description: '从第一反应的意象选择里，看见你的内在倾向',
    subnote: '潜意识联想探索',
    tagTone: 'orange',
    resultSectionTitles: {
      interpretation: '潜意识画像',
      recommendation: '给你的提醒'
    }
  },
  ICI: {
    title: '趣味自我概念测试',
    description: '探索你眼中的自己，发现独特的闪光点！',
    subnote: '自我认知小游戏',
    tagTone: 'blue',
    resultSectionTitles: {
      interpretation: '自我概念画像',
      recommendation: '自我探索建议'
    }
  },
  'REAL-MAJOR-V1': {
    title: '理想职业探索',
    description: '从任务偏好与工作风格里，看见更适合你的职业方向',
    subnote: '职业方向测试',
    tagTone: 'orange',
    resultSectionTitles: {
      interpretation: '职业倾向解读',
      recommendation: '职业探索建议'
    }
  },
  AGLT: {
    title: '天赋雷达：天赋与潜能测试',
    description: '探索你身上的天赋信号，发现还没完全亮起来的潜能！',
    subnote: '天赋扫描',
    tagTone: 'orange',
    resultSectionTitles: {
      interpretation: '天赋画像',
      recommendation: '天赋发展建议'
    }
  },
  RFLT: {
    title: '近期运势预测',
    description: '测测你的近期好运，抽一张专属好运签！',
    subnote: '近期好运签',
    tagTone: 'orange',
    iconKey: 'rflt',
    resultSectionTitles: {
      interpretation: '好运签解读',
      recommendation: '接好运提示'
    }
  },
  'SOUL-DRINK': {
    iconKey: 'soul-drink-v2',
    resultSectionTitles: {
      interpretation: '灵魂风味画像',
      recommendation: '生活提示'
    }
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

function getResultSectionTitles(shortName, assessmentType = '') {
  const resultSectionTitles = getScaleDisplayMeta(shortName).resultSectionTitles || {};
  const defaults = assessmentType === 'scoring'
    ? {
        interpretation: '结果解读',
        recommendation: '行动建议'
      }
    : {
        interpretation: '结果画像',
        recommendation: '给你的提示'
      };

  return {
    interpretation: resultSectionTitles.interpretation || defaults.interpretation,
    recommendation: resultSectionTitles.recommendation || defaults.recommendation
  };
}

module.exports = {
  SCALE_DISPLAY_META,
  getScaleDisplayMeta,
  getScaleDisplayName,
  getScaleIconName,
  getResultSectionTitles
};
