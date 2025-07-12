// pages/daily-checkin/record.js
Page({
  data: {
    // 1. 心情数据
    moods: [
      { name: '开心', icon: 'happy', selected: false },
      { name: '平静', icon: 'calm', selected: false },
      { name: '难过', icon: 'sad', selected: false },
      { name: '生气', icon: 'angry', selected: false },
      { name: '放松', icon: 'relaxed', selected: false },
      { name: '迷茫', icon: 'confused', selected: false },
      { name: '尴尬', icon: 'embarass', selected: false },
      { name: '疲惫', icon: 'tired', selected: false },
      { name: '兴奋', icon: 'excited', selected: false },
    ],
    // 2. 状态数据 (标签)
    statuses: [
      { name: '工作', icon: 'work', selected: false },
      { name: '学习', icon: 'study', selected: false },
      { name: '美食', icon: 'food', selected: false },
      { name: '生病', icon: 'health', selected: false },
      { name: '远足', icon: 'outdoor', selected: false },
      { name: '娱乐', icon: 'game', selected: false },
      { name: '躺平', icon: 'sleep', selected: false },
      { name: '运动', icon: 'sports', selected: false },
    ],
    // 3. 颜色数据
    colors: [
      // --- 原始色系 ---
      { value: '#FFC107', name: '暖阳橙', selected: false }, // Warm Sun Orange
      { value: '#81D4FA', name: '晴空蓝', selected: false }, // Clear Sky Blue
      { value: '#A5D6A7', name: '薄荷绿', selected: false }, // Mint Green
      { value: '#B0BEC5', name: '静谧灰', selected: false }, // Serene Gray
      { value: '#F48FB1', name: '樱花粉', selected: false }, // Cherry Blossom Pink
      { value: '#C5CAE9', name: '香芋紫', selected: false }, // Taro Purple
      // --- 新增色系 ---
      { value: '#FF8A80', name: '珊瑚红', selected: false }, // Coral Red
      { value: '#FFF59D', name: '柠檬黄', selected: false }, // Lemon Yellow
      { value: '#80CBC4', name: '湖水青', selected: false }, // Lake Cyan
      { value: '#7986CB', name: '深海蓝', selected: false }, // Deep Sea Blue
      { value: '#BCAAA4', name: '奶咖棕', selected: false }, // Latte Brown
      { value: '#F5F5F5', name: '云朵白', selected: false }, // Cloud White
    ],
    // 4. 用户输入数据
    textContent: "",
    imageUrl: "", // 用于存储上传后的图片URL
  },

  /**
   * 统一处理选择的函数（心情、状态、颜色）
   * @param {Object} e - 事件对象
   */
  handleSelect(e) {
    const { type } = e.currentTarget.dataset; // 'moods', 'statuses', 'colors'
    const { index } = e.currentTarget.dataset;

    let list = this.data[type];
    // 如果点击的已经是选中的（第一个），则不作任何操作
    if (list[index].selected) {
      return;
    }

    // 核心逻辑：将选中的项移动到数组最前面
    const selectedItem = list.splice(index, 1)[0];
    list.unshift(selectedItem);

    // 更新所有项的 'selected' 状态（只有第一个是true）
    list.forEach((item, idx) => {
      item.selected = (idx === 0);
    });

    // 更新页面数据
    this.setData({
      [type]: list
    });
  },

  // 监听文本框输入
  onTextInput(e) {
    this.setData({
      textContent: e.detail.value
    });
  },

  // 选择图片
  chooseImage() {
    // 这里先留空，后续实现 wx.chooseMedia 和 wx.uploadFile 的逻辑
    wx.showToast({ title: '功能开发中', icon: 'none' });
  },

  // 最终提交
  submitCheckin() {
    // 1. 数据校验
    const selectedMood = this.data.moods.find(item => item.selected);
    const selectedStatus = this.data.statuses.find(item => item.selected);
    const selectedColor = this.data.colors.find(item => item.selected);

    if (!selectedMood || !selectedStatus || !selectedColor) {
      wx.showToast({
        title: '请完成心情、状态和颜色的选择哦',
        icon: 'none'
      });
      return;
    }

    // 2. 准备提交到后端的数据
    const submissionData = {
      mood: selectedMood.name,
      // 注意：后端的 'tags' 字段我们用来存这里的 'status'
      tags: selectedStatus.name, 
      color: selectedColor.value,
      text_content: this.data.textContent,
      image_url: this.data.imageUrl // 如果实现了图片上传，这里就会有值
    };

    console.log("准备提交的数据:", submissionData);

    // 3. 调用API接口
    const token = wx.getStorageSync('token'); // 从缓存中获取Token
    if (!token) {
        wx.showToast({ title: '请先登录', icon: 'none' });
        // 这里可以加上跳转到登录页的逻辑
        return;
    }

    wx.request({
      url: 'http://127.0.0.1:8000/api/v1/checkin/', // 【重要】请替换为你的后端API地址
      method: 'POST',
      header: {
        'Authorization': `Bearer ${token}`
      },
      data: submissionData,
      success: (res) => {
        if (res.statusCode === 200 || res.statusCode === 201) {
          wx.showToast({
            title: '心情已封存',
            icon: 'success'
          });
          // 打卡成功后，延时1.5秒返回上一页
          setTimeout(() => {
            wx.navigateBack();
          }, 1500);
        } else {
          // 处理后端返回的错误信息，例如重复打卡
          const detail = res.data.detail || '提交失败，请稍后再试';
          wx.showToast({ title: detail, icon: 'none' });
        }
      },
      fail: (err) => {
        wx.showToast({
          title: '网络请求失败',
          icon: 'none'
        });
        console.error("请求失败:", err);
      }
    });
  }
});