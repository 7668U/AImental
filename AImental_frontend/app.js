// app.js
App({
  onLaunch() {
    // 全局导航栏高度计算
    const windowInfo = wx.getWindowInfo();
    const menuButtonInfo = wx.getMenuButtonBoundingClientRect();
    const extraPadding = 8; // 自定义导航栏与胶囊按钮的间距

    const statusBarHeight = windowInfo.statusBarHeight;
    // 计算导航栏高度：(胶囊上边距 - 状态栏高度) * 2 + 胶囊高度 + 自定义间距
    const navBarHeight = (menuButtonInfo.top - statusBarHeight) * 2 + menuButtonInfo.height + extraPadding;
    const totalNavBarHeight = statusBarHeight + navBarHeight;

    this.globalData = {
      statusBarHeight: statusBarHeight,
      navBarHeight: navBarHeight,
      totalNavBarHeight: totalNavBarHeight
    };
  },

  // 先定义一个空的 globalData 对象，onLaunch 中会填充它
  globalData: {
    statusBarHeight: 0,
    navBarHeight: 0,
    totalNavBarHeight: 0
  }
})

