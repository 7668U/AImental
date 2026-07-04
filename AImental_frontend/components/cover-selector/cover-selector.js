Component({
  properties: {
    // 让父组件可以传入当前选中的封面，以实现高亮
    selectedCover: {
      type: String,
      value: ''
    }
  },
  data: {
    // 可用的封面列表
    covers: [
      'https://assets.feelyourself.cn/miniprogram/assets/v1/images/background.png',
      'https://assets.feelyourself.cn/miniprogram/assets/v1/images/paper-airplane/background.png?v=202607050210',
      'https://assets.feelyourself.cn/miniprogram/assets/v1/images/ai-therapist/chat-bg-window.png'
    ]
  },
  methods: {
    onCoverTap(e) {
      const selectedCover = e.currentTarget.dataset.cover;
      // 触发"select"事件，通知父页面
      this.triggerEvent('select', { cover: selectedCover });
    }
  }
})
