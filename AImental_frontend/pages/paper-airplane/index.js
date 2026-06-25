// pages/paper-airplane/index.js
const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

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

const { getShareInfo, getTimelineInfo } = require('../../utils/share.js');

Page({
  data: {
    showWriteModal: false,
    showReadModal: false,
    newMessage: '',
    openedMessage: '',
    airplanes: [],
  },

  onLoad() {
    this.fetchAirplanes();
  },

  onShow() {
    if (this.data.airplanes.length === 0) {
      this.fetchAirplanes();
    }
  },

  async fetchAirplanes() {
    wx.showLoading({ title: '加载纸飞机...' });
    try {
      const availableAirplanes = await request({ url: '/airplane/available' });
      wx.hideLoading();

      const positionedAirplanes = availableAirplanes.map(airplane => ({
        ...airplane,
        top: Math.random() * 70 + 5,
        left: Math.random() * 80 + 10,
        rotate: Math.random() * 60 - 30
      }));

      this.setData({
        airplanes: positionedAirplanes
      });
    } catch (error) {
      wx.hideLoading();
      console.error("获取纸飞机失败", error);
    }
  },

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

  hideModals() {
    this.setData({
      showWriteModal: false,
      showReadModal: false
    });
  },

  onThrowClick() {
    this.setData({ showWriteModal: true, newMessage: '' });
  },

  async onAirplaneTap(e) {
    const airplaneId = e.currentTarget.dataset.id;
    wx.showLoading({ title: '正在捡纸飞机...' });
    try {
      const pickedAirplane = await request({
        url: `/airplane/${airplaneId}/pickup`,
        method: 'POST'
      });
      wx.hideLoading();

      const updatedAirplanes = this.data.airplanes.filter(ap => ap.id !== airplaneId);
      this.setData({
        airplanes: updatedAirplanes,
        openedMessage: pickedAirplane.message,
        showReadModal: true,
      });

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
      this.addOneNewAirplane();
    } catch (error) {
      wx.hideLoading();
      console.error("发送失败", error);
    }
  },

  onShareAppMessage() {
    return getShareInfo({
      title: '把心事折成纸飞机，让它轻轻飞出去',
      path: '/pages/paper-airplane/index'
    });
  },

  onShareTimeline() {
    return getTimelineInfo({
      title: '把心事折成纸飞机，让它轻轻飞出去'
    });
  }
});
