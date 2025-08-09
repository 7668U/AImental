// pages/daily-checkin/paper-airplane/index.js
const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

// 封装的网络请求函数
function request(options) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token');
    if (!token) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return reject('No token');
    }
    wx.request({
      ...options,
      url: `${API_BASE_URL}${options.url}`,
      header: {
        ...options.header,
        'Authorization': `Bearer ${token}`
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          wx.showToast({ title: res.data.detail || '请求失败', icon: 'none' });
          reject(res);
        }
      },
      fail(err) {
        wx.showToast({ title: '网络错误', icon: 'none' });
        reject(err);
      }
    });
  });
}

Page({
  data: {
    showWriteModal: false,
    showReadModal: false,
    newMessage: '',
    openedMessage: '',
    airplanes: [], // 用于存放动态生成的纸飞机数据
  },

  onLoad(options) {
    // 页面加载时获取纸飞机列表
    this.fetchAirplanes();
  },

  onShow() {
    // 页面显示时也刷新纸飞机列表，确保数据最新
    // 仅在第一次加载时完全刷新，后续由onAirplaneTap控制
    if (this.data.airplanes.length === 0) {
      this.fetchAirplanes();
    }
  },

  // 获取纸飞机列表
  async fetchAirplanes() {
    wx.showLoading({ title: '加载纸飞机...' });
    try {
      const availableAirplanes = await request({ url: '/airplane/available' });
      wx.hideLoading();

      // 为每个纸飞机生成随机位置和旋转角度
      const positionedAirplanes = availableAirplanes.map(airplane => {
        return {
          ...airplane,
          top: Math.random() * 70 + 5, // 5% 到 75% 的垂直位置
          left: Math.random() * 80 + 10, // 10% 到 90% 的水平位置
          rotate: Math.random() * 60 - 30 // -30度到30度
        };
      });

      this.setData({
        airplanes: positionedAirplanes
      });

    } catch (error) {
      wx.hideLoading();
      console.error("获取纸飞机失败", error);
    }
  },

  // 【新增】获取并添加一个新纸飞机
  async addOneNewAirplane() {
    try {
      const newAirplanes = await request({ url: '/airplane/available?limit=1' });
      if (newAirplanes && newAirplanes.length > 0) {
        const newAirplane = newAirplanes[0];
        const positionedNewAirplane = {
          ...newAirplane,
          top: Math.random() * 70 + 5,
          left: Math.random() * 80 + 10,
          rotate: Math.random() * 60 - 30
        };
        this.setData({
          airplanes: [...this.data.airplanes, positionedNewAirplane]
        });
      } else {
        console.log("No new airplanes available to add.");
      }
    } catch (error) {
      console.error("添加新纸飞机失败", error);
    }
  },

  // --- 弹窗控制 ---
  hideModals() {
    this.setData({ 
      showWriteModal: false, 
      showReadModal: false 
    });
    // 弹窗关闭后不再全部刷新纸飞机列表，由onAirplaneTap控制
  },

  // --- 事件处理 ---
  onThrowClick() {
    this.setData({ showWriteModal: true, newMessage: '' });
  },

  // 点击纸飞机事件
  async onAirplaneTap(e) {
    const airplaneId = e.currentTarget.dataset.id;
    wx.showLoading({ title: '正在捡纸飞机...' });
    try {
      const pickedAirplane = await request({ 
        url: `/airplane/${airplaneId}/pickup`,
        method: 'POST'
      });
      wx.hideLoading();

      // 移除被捡走的纸飞机
      const updatedAirplanes = this.data.airplanes.filter(ap => ap.id !== airplaneId);
      this.setData({
        airplanes: updatedAirplanes,
        openedMessage: pickedAirplane.message,
        showReadModal: true,
      });

      // 尝试添加一个新纸飞机来补充空位
      this.addOneNewAirplane();

    } catch (error) {
      wx.hideLoading();
      console.error("捡纸飞机失败", error);
    }
  },

  onMessageInput(e) {
    this.setData({ newMessage: e.detail.value });
  },

  async sendAirplane() {
    const message = this.data.newMessage.trim();
    if (!message) {
      wx.showToast({ title: '内容不能为空哦', icon: 'none' });
      return;
    }

    wx.showLoading({ title: '正在放飞...' });
    try {
      await request({
        url: '/airplane/throw',
        method: 'POST',
        data: { message: message },
      });
      wx.hideLoading();
      this.hideModals();
      wx.showToast({ title: '放飞成功！', icon: 'success' });
      // 成功放飞后，尝试添加一个新纸飞机到列表中（如果列表未满）
      this.addOneNewAirplane(); 
    } catch (error) {
      wx.hideLoading();
      console.error("发送失败", error);
    }
  },
});
