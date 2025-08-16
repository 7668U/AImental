// /utils/share.js

// 默认的分享信息
const defaultShareInfo = {
  title: '快来FeelYourself，和自己成为朋友！',
  path: '/pages/daily-checkin/index', // 默认分享到首页
  imageUrl: '/images/share-cover.png' // 一张默认的分享图
};

/**
 * @function getShareInfo
 * @description 生成分享信息，可以传入自定义信息覆盖默认值
 * @param {object} options - 自定义的分享信息，如 { title, path, imageUrl }
 * @returns {object} - 最终用于分享的对象
 */
const getShareInfo = (options = {}) => {
  // 使用传入的 options 覆盖 defaultShareInfo 中的同名属性
  return Object.assign({}, defaultShareInfo, options);
}

// 导出这个函数，让其他页面可以使用
module.exports = {
  getShareInfo: getShareInfo
}