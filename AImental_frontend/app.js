// app.js
const { hasCurrentPrivacyConsent } = require('./utils/privacy.js');
const { HOME_TITLE_FONT_FAMILY, HOME_TITLE_FONT_SOURCE } = require('./utils/home-title-font.js');

App({
  onLaunch() {
    if (wx.getStorageSync('token') && !hasCurrentPrivacyConsent()) {
      wx.removeStorageSync('token');
      wx.removeStorageSync('userInfo');
    }
    this.calculateNavBarDimensions();
    this.loadHomeTitleFont();
  },

  globalData: {
    statusBarHeight: 0,
    navBarHeight: 0,
    totalNavBarHeight: 0,
    compactNavBarHeight: 44,
    compactTotalNavBarHeight: 64,
    homeTitleFontLoaded: false
  },

  loadHomeTitleFont() {
    if (!wx.loadFontFace) {
      return;
    }

    wx.loadFontFace({
      family: HOME_TITLE_FONT_FAMILY,
      source: HOME_TITLE_FONT_SOURCE,
      global: true,
      success: () => {
        this.globalData.homeTitleFontLoaded = true;
      },
      fail: (error) => {
        this.globalData.homeTitleFontLoaded = false;
        console.warn('load home title font failed', error);
      }
    });
  },

  calculateNavBarDimensions() {
    try {
      const windowInfo = wx.getWindowInfo();
      const menuButtonInfo = wx.getMenuButtonBoundingClientRect();
      const extraPadding = 40;

      const statusBarHeight = windowInfo.statusBarHeight;
      const navBarHeight = (menuButtonInfo.top - statusBarHeight) * 2 + menuButtonInfo.height + extraPadding;
      const totalNavBarHeight = statusBarHeight + navBarHeight;

      const compactNavBarHeight = (menuButtonInfo.top - statusBarHeight) * 2 + menuButtonInfo.height + 10;
      const compactTotalNavBarHeight = statusBarHeight + compactNavBarHeight;

      this.globalData.statusBarHeight = statusBarHeight;
      this.globalData.navBarHeight = navBarHeight;
      this.globalData.totalNavBarHeight = totalNavBarHeight;
      this.globalData.compactNavBarHeight = compactNavBarHeight;
      this.globalData.compactTotalNavBarHeight = compactTotalNavBarHeight;
    } catch (e) {
      this.globalData.statusBarHeight = 20;
      this.globalData.navBarHeight = 84;
      this.globalData.totalNavBarHeight = 104;
      this.globalData.compactNavBarHeight = 44;
      this.globalData.compactTotalNavBarHeight = 64;
    }
  }
});
