// components/login-prompt/login-prompt.js
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
    // 组件内部数据
  },

  /**
   * 组件的方法列表
   */
  methods: {
    // 当用户点击 "微信授权登录" 按钮时触发
    onLoginTap() {
      // 触发一个自定义事件，通知使用该组件的页面：“用户要登录了！”
      this.triggerEvent('loginevent'); 
    }
  }
})