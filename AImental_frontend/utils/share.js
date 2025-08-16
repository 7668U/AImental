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

// --- 【新增】分享到朋友圈 ---
// 1. 定义朋友圈分享的默认信息
const defaultTimelineInfo = {
  title: '这个AI社区太好玩了，你也来看看吧！',
  // 注意：这里没有 path！
  query: 'from=timeline', // query 用于传递参数
  imageUrl: '/images/share-cover.png' // 强烈建议提供，否则会是很难看的页面截图
};

// 2. 创建一个生成朋友圈分享信息的函数
const getTimelineInfo = (options = {}) => {
  return Object.assign({}, defaultTimelineInfo, options);
}


// --- 导出模块 ---
// 3. 在导出对象中，加上我们新的函数
module.exports = {
  getShareInfo: getShareInfo,
  getTimelineInfo: getTimelineInfo // 导出新函数
}