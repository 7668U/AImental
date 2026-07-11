const DEFAULT_LOCAL_USER_ID = 'local-dev-user';
const {
  clearPrivacyConsent,
  createPrivacyConsentRequiredError,
  getPrivacyLoginPayload,
  hasCurrentPrivacyConsent
} = require('./privacy.js');

function isLocalApi(apiBaseUrl) {
  return apiBaseUrl.includes('127.0.0.1') || apiBaseUrl.includes('localhost');
}

function getDevUserId() {
  return wx.getStorageSync('devUserId') || DEFAULT_LOCAL_USER_ID;
}

function loginWithBackend(apiBaseUrl) {
  return new Promise((resolve, reject) => {
    const privacyPayload = getPrivacyLoginPayload();
    if (!privacyPayload) {
      reject(createPrivacyConsentRequiredError());
      return;
    }

    const handleResponse = (res) => {
      if (res.statusCode >= 200 && res.statusCode < 300) {
        resolve(res.data);
        return;
      }
      if (
        res.statusCode === 428 &&
        res.data &&
        res.data.detail &&
        res.data.detail.code === 'privacy_consent_required'
      ) {
        clearPrivacyConsent();
        reject(createPrivacyConsentRequiredError(res.data.detail.message));
        return;
      }
      reject(res);
    };

    if (isLocalApi(apiBaseUrl)) {
      wx.request({
        url: `${apiBaseUrl}/users/login/test`,
        method: 'POST',
        data: {
          user_id: getDevUserId(),
          ...privacyPayload
        },
        success: handleResponse,
        fail: reject
      });
      return;
    }

    wx.login({
      success(loginRes) {
        if (!loginRes.code) {
          reject(new Error('Failed to get WeChat login code'));
          return;
        }
        wx.request({
          url: `${apiBaseUrl}/users/login`,
          method: 'POST',
          data: {
            code: loginRes.code,
            ...privacyPayload
          },
          success: handleResponse,
          fail: reject
        });
      },
      fail: reject
    });
  });
}

function requestPrivacyAwareLogin(page, loginAction) {
  if (hasCurrentPrivacyConsent()) {
    return Promise.resolve().then(() => loginAction.call(page));
  }

  page._pendingPrivacyLogin = loginAction;
  page.setData({ privacyVisible: true });
  return Promise.resolve(null);
}

function confirmPrivacyAwareLogin(page) {
  const loginAction = page._pendingPrivacyLogin;
  page._pendingPrivacyLogin = null;
  page.setData({ privacyVisible: false });

  if (!loginAction) {
    return Promise.resolve(null);
  }

  return Promise.resolve().then(() => loginAction.call(page));
}

function rejectPrivacyAwareLogin(page) {
  page._pendingPrivacyLogin = null;
  page.setData({ privacyVisible: false });
  wx.showToast({
    title: '同意隐私协议后才能登录',
    icon: 'none'
  });
}

module.exports = {
  confirmPrivacyAwareLogin,
  loginWithBackend,
  rejectPrivacyAwareLogin,
  requestPrivacyAwareLogin
};
