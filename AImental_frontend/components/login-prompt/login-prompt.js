// components/login-prompt/login-prompt.js
const {
  hasCurrentPrivacyConsent
} = require('../../utils/privacy.js');

Component({
  /**
   * 组件的属性列表
   * 用于接收父页面传递过来的数据
   */
  properties: {
    title: {
      type: String, // 类型
      value: '欢迎' // 默认值
    },
    subtitle: {
      type: String,
      value: '请先登录，以继续操作'
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    privacyVisible: false
  },

  /**
   * 组件的方法列表
   */
  methods: {
    // 当用户点击 "微信授权登录" 按钮时触发
    onLoginTap() {
      if (hasCurrentPrivacyConsent()) {
        this.triggerEvent('loginevent');
        return;
      }
      this.setData({ privacyVisible: true });
    },

    onPrivacyConfirm() {
      this.setData({ privacyVisible: false });
      this.triggerEvent('loginevent');
    },

    onPrivacyReject() {
      this.setData({ privacyVisible: false });
      wx.showToast({
        title: '同意隐私协议后才能登录',
        icon: 'none'
      });
    }
  }
})
