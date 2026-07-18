const CONTENT_TYPE_BY_IMAGE_TYPE = {
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  png: 'image/png',
  gif: 'image/gif',
  webp: 'image/webp',
};

function request(options) {
  return new Promise((resolve, reject) => {
    wx.request({
      ...options,
      success: resolve,
      fail: reject,
    });
  });
}

function getImageInfo(filePath) {
  return new Promise((resolve, reject) => {
    wx.getImageInfo({
      src: filePath,
      success: resolve,
      fail: reject,
    });
  });
}

function getFileInfo(filePath) {
  return new Promise((resolve, reject) => {
    wx.getFileInfo({
      filePath,
      success: resolve,
      fail: reject,
    });
  });
}

function readFile(filePath) {
  return new Promise((resolve, reject) => {
    wx.getFileSystemManager().readFile({
      filePath,
      success: (res) => resolve(res.data),
      fail: reject,
    });
  });
}

function responseDetail(res, fallback) {
  const detail = res && res.data && res.data.detail;
  if (typeof detail === 'string') return detail;
  if (detail && detail.message) return detail.message;
  return fallback;
}

function directUploadError(message, options = {}) {
  const error = new Error(message);
  Object.assign(error, options);
  return error;
}

function isDirectUploadUnavailable(error) {
  return Boolean(error && error.directUploadUnavailable);
}

async function uploadPrivateImageDirect({
  apiBaseUrl,
  token,
  mediaType,
  filePath,
  bindUrl,
  bindMethod = 'PUT',
}) {
  const [imageInfo, fileInfo] = await Promise.all([
    getImageInfo(filePath),
    getFileInfo(filePath),
  ]);
  const contentType = CONTENT_TYPE_BY_IMAGE_TYPE[
    String(imageInfo.type || '').toLowerCase()
  ];
  if (!contentType) {
    throw directUploadError('暂不支持这种图片格式');
  }

  const prepareRes = await request({
    url: `${apiBaseUrl}/api/v1/private-media/uploads`,
    method: 'POST',
    data: {
      media_type: mediaType,
      content_type: contentType,
      size: fileInfo.size,
    },
    header: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (prepareRes.statusCode < 200 || prepareRes.statusCode >= 300) {
    const unavailable = [404, 405, 503].includes(prepareRes.statusCode);
    throw directUploadError(
      responseDetail(prepareRes, '无法申请图片直传地址'),
      {
        directUploadUnavailable: unavailable,
        response: prepareRes,
      }
    );
  }

  const uploadData = prepareRes.data || {};
  const fileData = await readFile(filePath);
  const cosRes = await request({
    url: uploadData.upload_url,
    method: 'PUT',
    data: fileData,
    header: uploadData.headers || {
      'Content-Type': contentType,
      'x-cos-server-side-encryption': 'AES256',
    },
    timeout: 120000,
    dataType: 'text',
    responseType: 'text',
  });
  if (cosRes.statusCode < 200 || cosRes.statusCode >= 300) {
    throw directUploadError('图片上传到 COS 失败', { response: cosRes });
  }

  const bindRes = await request({
    url: bindUrl,
    method: bindMethod,
    data: {
      upload_token: uploadData.upload_token,
    },
    header: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (bindRes.statusCode < 200 || bindRes.statusCode >= 300) {
    throw directUploadError(
      responseDetail(bindRes, '图片确认失败'),
      { response: bindRes }
    );
  }
  return bindRes.data;
}

module.exports = {
  isDirectUploadUnavailable,
  uploadPrivateImageDirect,
};
