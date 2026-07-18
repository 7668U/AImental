// pages/daily-checkin/record.js
const { getShareInfo, getTimelineInfo } = require('../utils/share.js');
const {
  uploadPrivateImageDirect,
} = require('../utils/private-media-upload.js');

const API_BASE_URL = 'https://api.feelyourself.cn';
const MAX_PHOTOS = 3;

const MOOD_OPTIONS = [
  { id: 'happy', name: '开心', icon: 'happy', family: '明亮愉悦', valence: 'positive', energy: 'high' },
  { id: 'satisfied', name: '满足', icon: 'satisfied', family: '明亮愉悦', valence: 'positive', energy: 'medium' },
  { id: 'expectant', name: '期待', icon: 'expectant', family: '明亮愉悦', valence: 'positive', energy: 'high' },
  { id: 'grateful', name: '感激', icon: 'grateful', family: '明亮愉悦', valence: 'positive', energy: 'medium' },
  { id: 'calm', name: '平静', icon: 'calm', family: '安稳平静', valence: 'neutral', energy: 'low' },
  { id: 'relaxed', name: '放松', icon: 'relaxed', family: '安稳平静', valence: 'positive', energy: 'low' },
  { id: 'secure', name: '安心', icon: 'secure', family: '安稳平静', valence: 'positive', energy: 'low' },
  { id: 'focused', name: '专注', icon: 'focused', family: '安稳平静', valence: 'neutral', energy: 'medium' },
  { id: 'sad', name: '难过', icon: 'sad', family: '低落难过', valence: 'negative', energy: 'low' },
  { id: 'lost', name: '失落', icon: 'lost', family: '低落难过', valence: 'negative', energy: 'low' },
  { id: 'wronged', name: '委屈', icon: 'wronged', family: '低落难过', valence: 'negative', energy: 'low' },
  { id: 'lonely', name: '孤独', icon: 'lonely', family: '低落难过', valence: 'negative', energy: 'low' },
  { id: 'anxious', name: '焦虑', icon: 'anxious', family: '焦虑紧绷', valence: 'negative', energy: 'high' },
  { id: 'worried', name: '担心', icon: 'worried', family: '焦虑紧绷', valence: 'negative', energy: 'medium' },
  { id: 'irritable', name: '烦躁', icon: 'irritable', family: '焦虑紧绷', valence: 'negative', energy: 'high' },
  { id: 'panicked', name: '慌乱', icon: 'panicked', family: '焦虑紧绷', valence: 'negative', energy: 'high' },
  { id: 'angry', name: '生气', icon: 'angry', family: '生气受伤', valence: 'negative', energy: 'high' },
  { id: 'annoyed', name: '厌烦', icon: 'annoyed', family: '生气受伤', valence: 'negative', energy: 'medium' },
  { id: 'unwilling', name: '不甘', icon: 'unwilling', family: '生气受伤', valence: 'negative', energy: 'high' },
  { id: 'hurt', name: '受伤', icon: 'hurt', family: '生气受伤', valence: 'negative', energy: 'low' },
  { id: 'tired', name: '疲惫', icon: 'tired', family: '疲惫麻木', valence: 'negative', energy: 'low' },
  { id: 'sleepy', name: '困倦', icon: 'sleepy', family: '疲惫麻木', valence: 'neutral', energy: 'low' },
  { id: 'numb', name: '麻木', icon: 'numb', family: '疲惫麻木', valence: 'neutral', energy: 'low' },
  { id: 'confused', name: '迷茫', icon: 'confused', family: '疲惫麻木', valence: 'negative', energy: 'low' },
];

function buildMoodList(selectedName = '平静') {
  return MOOD_OPTIONS.map(item => ({
    ...item,
    selected: item.name === selectedName,
  }));
}

const STATUS_OPTIONS = [
  { id: 'sunny', name: '元气满满', icon: 'sunny', family: '能量气场', selected: false },
  { id: 'charge', name: '充电', icon: 'charge', family: '能量气场', selected: false },
  { id: 'low_battery', name: '低电量', icon: 'low_battery', family: '能量气场', selected: false },
  { id: 'cloud', name: '放空', icon: 'cloud', family: '能量气场', selected: false },
  { id: 'brick', name: '搬砖', icon: 'brick', family: '工作学习', selected: false },
  { id: 'book', name: '学习', icon: 'book', family: '工作学习', selected: true },
  { id: 'meeting', name: '开会', icon: 'meeting', family: '工作学习', selected: false },
  { id: 'overtime', name: '加班', icon: 'overtime', family: '工作学习', selected: false },
  { id: 'commute', name: '通勤', icon: 'commute', family: '出行移动', selected: false },
  { id: 'business_trip', name: '出差', icon: 'business_trip', family: '出行移动', selected: false },
  { id: 'travel', name: '旅行', icon: 'travel', family: '出行移动', selected: false },
  { id: 'home', name: '回家', icon: 'home', family: '出行移动', selected: false },
  { id: 'food', name: '美食', icon: 'food', family: '生活日常', selected: false },
  { id: 'sleep', name: '睡觉', icon: 'sleep', family: '生活日常', selected: false },
  { id: 'housework', name: '家务', icon: 'housework', family: '生活日常', selected: false },
  { id: 'shopping', name: '购物', icon: 'shopping', family: '生活日常', selected: false },
  { id: 'sports', name: '运动', icon: 'sports', family: '运动健康', selected: false },
  { id: 'fitness', name: '健身', icon: 'fitness', family: '运动健康', selected: false },
  { id: 'outdoor', name: '户外', icon: 'outdoor', family: '运动健康', selected: false },
  { id: 'wellness', name: '养生', icon: 'wellness', family: '运动健康', selected: false },
  { id: 'stay_home', name: '宅家', icon: 'stay_home', family: '休闲社交', selected: false },
  { id: 'entertainment', name: '娱乐', icon: 'entertainment', family: '休闲社交', selected: false },
  { id: 'party', name: '聚会', icon: 'party', family: '休闲社交', selected: false },
  { id: 'no_disturb', name: '勿扰', icon: 'no_disturb', family: '休闲社交', selected: false },
];

const STATUS_LABEL_ALIAS = {
  '工作': '搬砖',
  '学习': '学习',
  '美食': '美食',
  '生病': '养生',
  '运动': '运动',
  '出游': '旅行',
  '出行': '旅行',
  '远足': '旅行',
  '吃饭': '美食',
  '喝咖啡': '美食',
  '做饭': '美食',
  '散步': '户外',
  '拉伸': '健身',
  '独处': '放空',
};

function buildStatusList(selectedNames = ['学习']) {
  const selectedName = selectedNames
    .map(normalizeStatusLabel)
    .find(name => STATUS_OPTIONS.some(item => item.name === name));

  return STATUS_OPTIONS.map(item => ({
    ...item,
    selected: item.name === selectedName,
  }));
}

function normalizeStatusLabel(label) {
  return STATUS_LABEL_ALIAS[label] || label;
}

const COLOR_OPTIONS = [
  { id: 'warm_sun_orange', name: '暖阳橙', value: '#FFB35C', group: '暖光明亮', description: '开心、被鼓励、有活力', selected: false },
  { id: 'cream_yellow', name: '奶油黄', value: '#FFE08A', group: '暖光明亮', description: '轻松、满足、治愈', selected: false },
  { id: 'peach_pink', name: '蜜桃粉', value: '#FF9FB2', group: '暖光明亮', description: '温柔、亲近、被照顾', selected: false },
  { id: 'coral_red', name: '珊瑚红', value: '#FF7A70', group: '暖光明亮', description: '热烈、兴奋、行动感', selected: false },
  { id: 'mint_green', name: '薄荷绿', value: '#8FD7A5', group: '清透自然', description: '安心、恢复、舒服', selected: false },
  { id: 'lake_blue', name: '湖水蓝', value: '#6EC6D9', group: '清透自然', description: '平静、清醒、流动', selected: false },
  { id: 'sky_blue', name: '晴空蓝', value: '#8BB8FF', group: '清透自然', description: '开阔、自由、专注', selected: true },
  { id: 'lime_green', name: '青柠绿', value: '#B7E36D', group: '清透自然', description: '新鲜、轻快、元气', selected: false },
  { id: 'lavender_purple', name: '薰衣紫', value: '#B9A7F0', group: '柔和梦感', description: '敏感、柔软、想象', selected: false },
  { id: 'cherry_mist_pink', name: '樱雾粉', value: '#F6B6C8', group: '柔和梦感', description: '细腻、浪漫、松弛', selected: false },
  { id: 'berry_red', name: '浅莓红', value: '#D96C8A', group: '柔和梦感', description: '心动、委屈、情绪浓', selected: false },
  { id: 'moonlight_white', name: '月光白', value: '#F5F1E8', group: '柔和梦感', description: '空白、安静、轻盈', selected: false },
  { id: 'fog_blue_gray', name: '雾灰蓝', value: '#91A7B4', group: '阴雨安静', description: '疲惫、缓慢、低能量', selected: false },
  { id: 'raindrop_blue', name: '雨滴蓝', value: '#6F8FBF', group: '阴雨安静', description: '难过、失落、想安静', selected: false },
  { id: 'cloud_gray', name: '云朵灰', value: '#C7CDD1', group: '阴雨安静', description: '麻木、平淡、无力', selected: false },
  { id: 'deep_sea_blue', name: '深海蓝', value: '#4B6584', group: '阴雨安静', description: '沉重、孤独、压抑', selected: false },
  { id: 'flame_red', name: '火焰红', value: '#E85D5D', group: '紧绷浓郁', description: '生气、冲突、不甘', selected: false },
  { id: 'caramel_brown', name: '焦糖棕', value: '#B9794A', group: '紧绷浓郁', description: '烦躁、消耗、压力', selected: false },
  { id: 'midnight_purple', name: '午夜紫', value: '#665C99', group: '紧绷浓郁', description: '焦虑、混乱、难眠', selected: false },
  { id: 'ink_green', name: '墨绿', value: '#557C70', group: '紧绷浓郁', description: '克制、防御、自我保护', selected: false },
  { id: 'wood_tan', name: '木色', value: '#C8A27A', group: '沉稳大地', description: '稳定、生活感、真实', selected: false },
  { id: 'cocoa_brown', name: '可可棕', value: '#8B6A5A', group: '沉稳大地', description: '疲惫、踏实、厚重', selected: false },
  { id: 'turquoise_green', name: '松石绿', value: '#4FA39A', group: '沉稳大地', description: '平衡、恢复、慢慢变好', selected: false },
  { id: 'charcoal_black', name: '炭黑', value: '#3F3F46', group: '沉稳大地', description: '沉默、封闭、很累', selected: false },
];

function buildColorList(selectedValue = '#8BB8FF') {
  const alias = {
    '#FF8A80': '#FF7A70',
    '#FFB74D': '#FFB35C',
    '#FFC107': '#FFE08A',
    '#81D4FA': '#8BB8FF',
    '#A5D6A7': '#8FD7A5',
    '#B39DDB': '#B9A7F0',
    '#F48FB1': '#F6B6C8',
    '#BCAAA4': '#C8A27A',
  };
  const normalizedValue = alias[selectedValue] || selectedValue;
  const colors = COLOR_OPTIONS.map(item => ({
    ...item,
    selected: item.value.toLowerCase() === normalizedValue.toLowerCase(),
  }));
  if (!colors.some(item => item.selected)) {
    colors.forEach(item => item.selected = item.value === '#8BB8FF');
  }
  return colors;
}

function getSelectedColorInfo(colors) {
  return colors.find(item => item.selected) || colors[0];
}

function normalizeImageUrl(url) {
  if (!url) return '';
  if (/^https?:\/\//.test(url) || url.startsWith('wxfile://') || url.startsWith('cloud://')) {
    return url;
  }
  return `${API_BASE_URL}${url}`;
}

function toServerImageUrl(url) {
  if (!url) return '';
  if (url.startsWith(API_BASE_URL)) {
    return url.slice(API_BASE_URL.length);
  }
  return url;
}

function parseImageUrls(data) {
  const urls = [];
  const rawImageUrls = data.image_urls;

  if (Array.isArray(rawImageUrls)) {
    urls.push(...rawImageUrls);
  } else if (typeof rawImageUrls === 'string' && rawImageUrls.trim()) {
    try {
      const parsed = JSON.parse(rawImageUrls);
      if (Array.isArray(parsed)) urls.push(...parsed);
    } catch (error) {
      urls.push(rawImageUrls);
    }
  }

  if (data.image_url) urls.push(data.image_url);

  return Array.from(new Set(urls.filter(Boolean))).slice(0, MAX_PHOTOS);
}

function buildServerPhotos(data) {
  return parseImageUrls(data).map((url, index) => ({
    id: `server_${index}`,
    url: normalizeImageUrl(url),
    serverUrl: toServerImageUrl(url),
    tempFilePath: '',
    source: 'server',
  }));
}

Page({
  data: {
    navTitle: '记录此刻心情',
    statusBarHeight: 0,
    navBarHeight: 44,
    totalNavBarHeight: 44,
    dateLabel: '',
    locationText: '选择位置',
    locationAddress: '',
    locationLatitude: null,
    locationLongitude: null,

    moods: buildMoodList(),

    statuses: buildStatusList(),

    colors: buildColorList(),
    selectedColorInfo: getSelectedColorInfo(buildColorList()),

    textContent: '',
    textCount: 0,
    maxPhotos: MAX_PHOTOS,
    photos: [],
    scrollIntoView: '',

    isEditMode: false,
    isLocked: false,
    checkinId: null,
    pageDate: null,

    recordTime: '',      // 当前选择的时刻 HH:MM
    maxTime: '23:59',    // 允许选择的最晚时刻（今天当前时刻）
    canPickTime: true,   // 是否允许点击微调时间（仅今天可编辑时为 true）
  },

  onLoad(options) {
    this.updateNavMetrics();

    if (options.mode === 'edit' || options.mode === 'view') {
      const dateStr = options.date || this.getTodayString();
      this.setData({
        isEditMode: true,
        pageDate: dateStr,
        maxTime: this.getCurrentTimeString(),
        dateLabel: this.formatDateLabel(dateStr),
      });
      this.loadCheckinData(dateStr, options.id);
    } else {
      const today = this.getTodayString();
      const nowTime = this.getCurrentTimeString();
      this.setData({
        isEditMode: false,
        isLocked: false,
        canPickTime: true,
        pageDate: today,
        recordTime: nowTime,
        maxTime: nowTime,
        dateLabel: this.formatMomentLabelWithTime(nowTime),
        navTitle: '记录此刻心情',
      });
      wx.setNavigationBarTitle({ title: '记录此刻心情' });
    }
  },

  onShow() {
    this.updateNavMetrics();
  },

  updateNavMetrics() {
    try {
      const windowInfo = wx.getWindowInfo();
      const menuButtonInfo = wx.getMenuButtonBoundingClientRect();
      const statusBarHeight = windowInfo.statusBarHeight || 0;
      const navBarHeight = (menuButtonInfo.top - statusBarHeight) * 2 + menuButtonInfo.height;
      this.setData({
        statusBarHeight,
        navBarHeight,
        totalNavBarHeight: statusBarHeight + navBarHeight,
      });
    } catch (error) {
      this.setData({
        statusBarHeight: 24,
        navBarHeight: 48,
        totalNavBarHeight: 72,
      });
    }
  },

  chooseRecordLocation() {
    if (this.data.isLocked) return;

    const options = {
      success: (location) => {
        const locationText = location.name || location.address || '已选择位置';
        this.setData({
          locationText,
          locationAddress: location.address || '',
          locationLatitude: location.latitude || null,
          locationLongitude: location.longitude || null,
        });
      },
      fail: () => {
        wx.showToast({ title: '没有选择位置', icon: 'none' });
      }
    };

    if (this.data.locationLatitude && this.data.locationLongitude) {
      options.latitude = this.data.locationLatitude;
      options.longitude = this.data.locationLongitude;
    }

    wx.chooseLocation(options);
  },

  goBack() {
    wx.navigateBack({ delta: 1 });
  },

  loadCheckinData(dateToFetch, momentId) {
    // 只允许修改今天的记录，过去的记录只读回看。
    const canEdit = dateToFetch === this.getTodayString();
    this.setData({
      isLocked: !canEdit,
      canPickTime: canEdit,
      navTitle: canEdit ? '修改此刻心情' : '回看此刻心情',
      dateLabel: this.formatDateLabel(dateToFetch),
    });

    wx.setNavigationBarTitle({ title: canEdit ? '修改此刻心情' : '回看此刻心情' });

    const token = wx.getStorageSync('token');
    if (!token) return;

    // 优先按具体 moment 的 id 加载（心情轨迹点击进入）；否则回退到按日期取当天最新一条。
    const url = momentId
      ? `https://api.feelyourself.cn/api/v1/checkin/moment/${momentId}`
      : `https://api.feelyourself.cn/api/v1/checkin/date/${dateToFetch}`;

    wx.showLoading({ title: '加载中...' });
    wx.request({
      url,
      method: 'GET',
      header: { 'Authorization': `Bearer ${token}` },
      success: (res) => {
        if (res.statusCode === 200) {
          const checkinData = res.data;
          this.setData({ checkinId: checkinData.id });
          this.populateForm(checkinData);
          const loadedTime = checkinData.local_time || this.getCurrentTimeString();
          this.setData({
            recordTime: loadedTime,
            dateLabel: canEdit
              ? this.formatMomentLabelWithTime(loadedTime)
              : `${this.formatDateLabel(dateToFetch)} ${loadedTime}`,
          });
        } else {
          wx.showToast({ title: '加载记录失败', icon: 'none' });
        }
      },
      fail: () => {
        wx.showToast({ title: '网络请求失败', icon: 'none' });
      },
      complete: () => {
        wx.hideLoading();
      }
    });
  },

  onTimeChange(e) {
    if (this.data.isLocked || !this.data.canPickTime) return;
    let picked = e.detail.value || this.data.recordTime;
    // 不允许超过当前时刻。
    if (picked > this.data.maxTime) {
      picked = this.data.maxTime;
      wx.showToast({ title: '不能选择未来的时间哦', icon: 'none' });
    }
    this.setData({
      recordTime: picked,
      dateLabel: this.formatMomentLabelWithTime(picked),
    });
  },

  populateForm(data) {
    const newMoods = JSON.parse(JSON.stringify(this.data.moods));
    const moodIndex = newMoods.findIndex(item => item.name === data.mood);
    if (moodIndex > -1) {
      newMoods.forEach(item => item.selected = false);
      newMoods[moodIndex].selected = true;
    }

    const selectedTags = data.tags ? data.tags.split(',').map(normalizeStatusLabel) : [];
    const newStatuses = buildStatusList(selectedTags);

    const newColors = buildColorList(data.color || '#8BB8FF');

    const textContent = data.text_content || '';
    this.setData({
      moods: newMoods,
      statuses: newStatuses,
      colors: newColors,
      selectedColorInfo: getSelectedColorInfo(newColors),
      textContent,
      textCount: textContent.length,
      photos: buildServerPhotos(data),
    });
  },

  handleMoodSelect(e) {
    if (this.data.isLocked) return;
    const { id } = e.currentTarget.dataset;
    const moods = this.data.moods.map(item => ({
      ...item,
      selected: item.id === id,
    }));

    this.setData({
      moods,
    });
  },

  handleSelect(e) {
    if (this.data.isLocked) return;
    const { type, index } = e.currentTarget.dataset;
    const list = this.data[type];

    if (type === 'statuses') {
      if (list[index].selected) return;
      list.forEach(item => item.selected = false);
      list[index].selected = true;
    } else {
      if (list[index].selected) return;
      list.forEach(item => item.selected = false);
      list[index].selected = true;
    }

    const nextData = { [type]: list };
    if (type === 'colors') {
      nextData.selectedColorInfo = getSelectedColorInfo(list);
    }
    this.setData(nextData);
  },

  onTextInput(e) {
    if (this.data.isLocked) return;
    const textContent = e.detail.value || '';
    this.setData({
      textContent,
      textCount: textContent.length,
    });
  },


  chooseImage(e) {
    if (this.data.isLocked) return;

    const { index } = e.currentTarget.dataset;
    if (index === undefined || index === null || index === '') {
      this.selectNewImages();
      return;
    }

    const photoIndex = Number(index);
    const photo = this.data.photos[photoIndex];
    if (!photo) return;

    const itemList = ['预览照片', '更换照片', '删除照片'];

    wx.showActionSheet({
      itemList,
      success: (res) => {
        const action = itemList[res.tapIndex];
        if (action === '预览照片') this.previewPhoto(photoIndex);
        if (action === '更换照片') this.replacePhoto(photoIndex);
        if (action === '删除照片') this.removePhoto(photoIndex);
      }
    });
  },

  selectNewImages() {
    const remainingCount = MAX_PHOTOS - this.data.photos.length;
    if (remainingCount <= 0) {
      wx.showToast({ title: `最多添加 ${MAX_PHOTOS} 张照片`, icon: 'none' });
      return;
    }

    wx.chooseMedia({
      count: remainingCount,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const newPhotos = (res.tempFiles || []).slice(0, remainingCount).map((file, index) => ({
          id: `local_${Date.now()}_${index}`,
          url: file.tempFilePath,
          tempFilePath: file.tempFilePath,
          source: 'local',
        }));

        if (newPhotos.length === 0) return;

        this.setData({
          photos: this.data.photos.concat(newPhotos).slice(0, MAX_PHOTOS),
          scrollIntoView: 'photo-section',
        });
      }
    });
  },

  replacePhoto(index) {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFile = (res.tempFiles || [])[0];
        if (!tempFile) return;

        const photos = this.data.photos.slice();
        photos[index] = {
          id: `local_${Date.now()}_${index}`,
          url: tempFile.tempFilePath,
          tempFilePath: tempFile.tempFilePath,
          source: 'local',
        };
        this.setData({ photos, scrollIntoView: 'photo-section' });
      }
    });
  },

  removePhoto(indexOrEvent) {
    const index = typeof indexOrEvent === 'number'
      ? indexOrEvent
      : Number(indexOrEvent.currentTarget.dataset.index);
    const photos = this.data.photos.slice();
    photos.splice(index, 1);
    this.setData({ photos, scrollIntoView: 'photo-section' });
  },

  previewPhoto(index) {
    const urls = this.data.photos.map(photo => photo.url).filter(Boolean);
    const current = urls[index] || urls[0];
    if (!current) return;
    wx.previewImage({ current, urls });
  },

  submitCheckin() {
    if (this.data.isLocked) {
      wx.showToast({ title: '不能修改历史记录哦', icon: 'none' });
      return;
    }

    const selectedMood = this.data.moods.find(item => item.selected);
    const selectedStatuses = this.data.statuses.filter(item => item.selected);
    const selectedColor = this.data.colors.find(item => item.selected);

    if (!selectedMood || selectedStatuses.length !== 1 || !selectedColor) {
      wx.showToast({ title: '请完成所有选择', icon: 'none' });
      return;
    }

    const token = wx.getStorageSync('token');
    if (!token) return;

    const textData = {
      mood: selectedMood.name,
      tags: selectedStatuses.map(item => item.name).join(','),
      color: selectedColor.value,
      text_content: this.data.textContent,
      local_time: this.data.recordTime || this.getCurrentTimeString(),
    };

    wx.showLoading({ title: '正在保存...' });

    if (this.data.isEditMode) {
      this.updateCheckinRecord(textData);
    } else {
      this.createCheckinRecord(textData);
    }
  },

  createCheckinRecord(data) {
    this.sendRequest({
      url: 'https://api.feelyourself.cn/api/v1/checkin/moments',
      method: 'POST',
      data,
      successCallback: (res) => {
        const checkinId = res.data.id;
        this.syncPhotosForCheckin(checkinId, () => {
          this.handleSubmitSuccess('保存成功');
        });
      },
      failTitle: '提交失败'
    });
  },

  updateCheckinRecord(data) {
    this.sendRequest({
      url: `https://api.feelyourself.cn/api/v1/checkin/${this.data.checkinId}`,
      method: 'PUT',
      data,
      successCallback: () => {
        this.syncPhotosForCheckin(this.data.checkinId, () => {
          this.handleSubmitSuccess('修改成功');
        });
      },
      failTitle: '修改失败'
    });
  },

  uploadImageForCheckin(checkinId, filePath, imageIndex) {
    const token = wx.getStorageSync('token');
    return new Promise((resolve, reject) => {
      this.uploadCheckinImageFile({
        url: `${API_BASE_URL}/api/v1/checkin/${checkinId}/images/${imageIndex}`,
        filePath,
        name: 'image',
        header: { 'Authorization': `Bearer ${token}` },
        success: (res) => {
          if (res.statusCode === 200) {
            try {
              const data = typeof res.data === 'string' ? JSON.parse(res.data) : res.data;
              const urls = parseImageUrls(data);
              resolve(urls[imageIndex] || urls[urls.length - 1] || '');
            } catch (error) {
              reject(res);
            }
          } else {
            reject(res);
          }
        },
        fail: reject
      });
    });
  },

  uploadCheckinImageFile(options) {
    const token = wx.getStorageSync('token');
    uploadPrivateImageDirect({
      apiBaseUrl: API_BASE_URL,
      token,
      mediaType: 'checkin',
      filePath: options.filePath,
      bindUrl: `${options.url}/direct`,
      bindMethod: 'PUT',
    })
      .then((data) => {
        options.success({
          statusCode: 200,
          data: JSON.stringify(data),
        });
      })
      .catch((error) => {
        console.warn('Direct COS upload failed, falling back to backend upload.', error);
        wx.uploadFile(options);
      });
  },

  syncPhotosForCheckin(checkinId, successCallback) {
    const photos = this.data.photos.slice(0, MAX_PHOTOS);
    const finalUrls = [];
    const uploadNext = (index) => {
      if (index >= photos.length) {
        this.setCheckinImages(checkinId, finalUrls, successCallback);
        return;
      }

      const photo = photos[index];
      if (photo.tempFilePath) {
        this.uploadImageForCheckin(checkinId, photo.tempFilePath, index)
          .then((uploadedUrl) => {
            if (uploadedUrl) finalUrls.push(uploadedUrl);
            uploadNext(index + 1);
          })
          .catch((error) => this.handleApiError(error, '图片上传失败'));
        return;
      }

      const serverUrl = photo.serverUrl || toServerImageUrl(photo.url);
      if (serverUrl) finalUrls.push(serverUrl);
      uploadNext(index + 1);
    };

    uploadNext(0);
  },

  setCheckinImages(checkinId, imageUrls, successCallback) {
    this.sendRequest({
      url: `${API_BASE_URL}/api/v1/checkin/${checkinId}/images`,
      method: 'PUT',
      data: { image_urls: imageUrls.slice(0, MAX_PHOTOS) },
      successCallback,
      failTitle: '图片保存失败'
    });
  },

  sendRequest({ url, method, data, successCallback, failTitle }) {
    const token = wx.getStorageSync('token');
    wx.request({
      url,
      method,
      data,
      header: { 'Authorization': `Bearer ${token}` },
      success: (res) => {
        if (res.statusCode === 200 || res.statusCode === 201) {
          successCallback(res);
        } else {
          this.handleApiError(res, failTitle);
        }
      },
      fail: () => this.handleSubmitFail('网络请求失败')
    });
  },

  handleSubmitSuccess(title) {
    wx.hideLoading();
    wx.showToast({ title, icon: 'success' });
    setTimeout(() => { wx.navigateBack(); }, 1500);
  },

  handleSubmitFail(title) {
    wx.hideLoading();
    wx.showToast({ title, icon: 'none' });
  },

  handleApiError(res, defaultTitle) {
    let detail = defaultTitle;
    if (res && res.data) {
      if (typeof res.data === 'string') {
        try {
          detail = JSON.parse(res.data).detail || defaultTitle;
        } catch (error) {
          detail = defaultTitle;
        }
      } else {
        detail = res.data.detail || defaultTitle;
      }
    }
    this.handleSubmitFail(detail);
  },

  getTodayString() {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  },

  isWithinRecentDays(dateStr, days) {
    const target = new Date(`${dateStr}T00:00:00`);
    if (Number.isNaN(target.getTime())) return false;

    const today = new Date();
    const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    const diffDays = Math.floor((todayStart.getTime() - target.getTime()) / (24 * 60 * 60 * 1000));
    return diffDays >= 0 && diffDays < days;
  },

  formatDateLabel(dateStr) {
    const date = new Date(`${dateStr}T00:00:00`);
    if (Number.isNaN(date.getTime())) return '';
    const weekNames = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    return `${date.getMonth() + 1}月${date.getDate()}日 ${weekNames[date.getDay()]}`;
  },

  formatCurrentMomentLabel() {
    const now = new Date();
    return `今天 ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  },

  getCurrentTimeString() {
    const now = new Date();
    return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  },

  formatMomentLabelWithTime(timeStr) {
    return `今天 ${timeStr || this.getCurrentTimeString()}`;
  },

  onShareAppMessage() {
    return getShareInfo();
  },

  onShareTimeline() {
    return getTimelineInfo();
  }
});
