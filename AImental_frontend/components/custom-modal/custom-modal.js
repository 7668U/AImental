Component({
  properties: {
    show: {
      type: Boolean,
      value: false
    },
    title: {
      type: String,
      value: '提示'
    },
    content: {
      type: String,
      value: ''
    }
  },
  methods: {
    onConfirm() {
      // 隐藏弹窗
      this.setData({
        show: false
      });
      // 通知页面：用户点击了确定按钮
      this.triggerEvent('confirm');
    }
  }
})