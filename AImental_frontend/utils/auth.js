const DEFAULT_LOCAL_USER_ID = 'local-dev-user';

function isLocalApi(apiBaseUrl) {
  return apiBaseUrl.includes('127.0.0.1') || apiBaseUrl.includes('localhost');
}

function getDevUserId() {
  return wx.getStorageSync('devUserId') || DEFAULT_LOCAL_USER_ID;
}

function loginWithBackend(apiBaseUrl) {
  return new Promise((resolve, reject) => {
    if (isLocalApi(apiBaseUrl)) {
      wx.request({
        url: `${apiBaseUrl}/users/login/test`,
        method: 'POST',
        data: { user_id: getDevUserId() },
        success(res) {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(res.data);
          } else {
            reject(res);
          }
        },
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
          data: { code: loginRes.code },
          success(res) {
            if (res.statusCode >= 200 && res.statusCode < 300) {
              resolve(res.data);
            } else {
              reject(res);
            }
          },
          fail: reject
        });
      },
      fail: reject
    });
  });
}

module.exports = {
  loginWithBackend
};
