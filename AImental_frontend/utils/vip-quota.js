const VIP_PAGE_URL = '/pkgProfile/vip/index';

const FEATURE_ACTION_TEXT = {
  tree_hole: '继续发送消息',
  community: '继续发送消息',
  mood_analysis: '继续生成心情分析',
  assessment_analysis: '继续生成测评分析',
};

function getErrorDetail(error) {
  const data = error && error.data;
  if (data && data.detail !== undefined) {
    return data.detail;
  }
  return error && error.detail !== undefined ? error.detail : null;
}

function getErrorCode(error) {
  const detail = getErrorDetail(error);
  if (detail && typeof detail === 'object' && detail.code) {
    return detail.code;
  }
  const data = error && error.data;
  return data && data.code ? data.code : '';
}

function getQuotaFeature(error, fallbackFeature = '') {
  const detail = getErrorDetail(error);
  if (detail && typeof detail === 'object' && detail.feature) {
    return detail.feature;
  }
  return fallbackFeature;
}

function getVipState(error) {
  const detail = getErrorDetail(error);
  if (detail && typeof detail === 'object' && detail.vip_state) {
    return detail.vip_state;
  }
  return null;
}

function isVipQuotaExhaustedError(error) {
  return Number(error && error.statusCode) === 402
    && getErrorCode(error) === 'quota_exhausted';
}

function navigateToVipPage() {
  wx.navigateTo({
    url: VIP_PAGE_URL,
    fail: () => {
      wx.switchTab({ url: '/pages/profile/index' });
    },
  });
}

function showVipQuotaModal(options = {}) {
  const feature = getQuotaFeature(options.error, options.feature);
  const actionText = FEATURE_ACTION_TEXT[feature] || '继续使用';
  const vipState = getVipState(options.error);
  const isMember = vipState && vipState.user_type === 'member';
  const content = isMember
    ? `感谢您的使用！您当前的会员额度已经用完啦～\n\n如果还想${actionText}，可以了解一下加量包或会员套餐。`
    : `感谢您的使用！您的免费额度已经用完啦～\n\n如果还想${actionText}，可以了解一下我们的会员套餐，解锁更多陪伴和分析次数。`;

  wx.showModal({
    title: '感谢您的使用',
    content,
    confirmText: '去看看',
    cancelText: '返回',
    confirmColor: '#ff6f17',
    success: (res) => {
      if (res.confirm) {
        navigateToVipPage();
      }
    },
  });
}

module.exports = {
  isVipQuotaExhaustedError,
  showVipQuotaModal,
};
