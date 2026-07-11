const PRIVACY_POLICY_VERSION = '2026-07-11';
const PRIVACY_CONSENT_STORAGE_KEY = 'privacyConsent';

const PRIVACY_POLICY = {
  version: PRIVACY_POLICY_VERSION,
  effectiveDate: '2026年7月11日',
  title: '用户隐私保护协议',
  summary: '为了提供登录、情绪记录、心理测评和 AI 陪伴等功能，我们会在你明确同意后处理必要信息，并采用加密、访问控制和最小必要原则保护数据。',
  sections: [
    {
      title: '我们会处理哪些信息',
      content: '登录时处理微信提供的用户标识；在你主动填写或上传时处理昵称、头像、生日、性别、情绪日记、定位、照片、测评答案与结果、聊天内容、笔记和反馈。未使用对应功能时，我们不会主动收集该类内容。'
    },
    {
      title: '这些信息如何使用',
      content: '用于账号识别、保存和同步你的记录、生成测评与趋势分析、提供你主动选择的个性化 AI 互动、处理反馈，以及保障服务稳定与安全。我们不会把你的个人信息用于与上述目的无关的用途。'
    },
    {
      title: '我们如何保护数据',
      content: '敏感数据库字段和用户上传文件使用行业通行的认证加密保护；查询标识采用不可逆盲索引；访问需要身份校验，密钥与业务数据分离并支持轮换。同时我们会限制内部访问、减少日志中的个人信息，并持续改进安全措施。'
    },
    {
      title: 'AI 功能与必要说明',
      content: '只有在你开启相应功能时，系统才会读取为完成该次服务所必要的记录并生成回复或分析。AI 内容仅用于陪伴和自我观察，不替代医生、心理咨询师或其他专业意见。'
    },
    {
      title: '保存、删除与撤回同意',
      content: '我们仅在实现服务目的所需期限内保存信息。你可以通过产品内相关功能删除记录，也可以撤回隐私同意；撤回后我们将停止继续处理依赖同意的个人信息，但不影响撤回前已经合法进行的处理。'
    },
    {
      title: '你的权利与联系我们',
      content: '你可以查询、更正或删除个人信息，也可以撤回同意或注销账号。如需帮助，请通过小程序内「我的 - 意见反馈」联系我们。运营者以微信小程序主体信息为准。'
    }
  ],
  notice: '互联网服务无法承诺绝对零风险，但我们会采用与数据敏感程度相匹配的措施，认真保护你的隐私，并在发生安全事件时依法采取处置和通知措施。'
};

function getStoredPrivacyConsent() {
  const stored = wx.getStorageSync(PRIVACY_CONSENT_STORAGE_KEY);
  return stored && typeof stored === 'object' ? stored : null;
}

function hasCurrentPrivacyConsent() {
  const stored = getStoredPrivacyConsent();
  return Boolean(
    stored &&
    stored.agreed === true &&
    stored.version === PRIVACY_POLICY_VERSION
  );
}

function savePrivacyConsent() {
  const consent = {
    agreed: true,
    version: PRIVACY_POLICY_VERSION,
    agreedAt: new Date().toISOString()
  };
  wx.setStorageSync(PRIVACY_CONSENT_STORAGE_KEY, consent);
  return consent;
}

function clearPrivacyConsent() {
  wx.removeStorageSync(PRIVACY_CONSENT_STORAGE_KEY);
}

function getPrivacyLoginPayload() {
  if (!hasCurrentPrivacyConsent()) {
    return null;
  }
  return {
    privacy_consent_agreed: true,
    privacy_policy_version: PRIVACY_POLICY_VERSION
  };
}

function createPrivacyConsentRequiredError(message) {
  const error = new Error(message || '请先阅读并同意用户隐私保护协议');
  error.code = 'privacy_consent_required';
  return error;
}

module.exports = {
  PRIVACY_POLICY,
  PRIVACY_POLICY_VERSION,
  clearPrivacyConsent,
  createPrivacyConsentRequiredError,
  getPrivacyLoginPayload,
  getStoredPrivacyConsent,
  hasCurrentPrivacyConsent,
  savePrivacyConsent
};
