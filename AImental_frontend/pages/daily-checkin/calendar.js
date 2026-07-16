// components/calendar/calendar.js
Component({
  properties: {
    show: { // 控制组件显示/隐藏
      type: Boolean,
      value: false,
      observer: function(newVal) {
        if (newVal) {
          this.init();
        }
      }
    }
  },

  data: {
    currentYear: 2025,
    currentMonth: 7,
    days: [],
    hasCheckinsThisMonth: true,
  },

  methods: {
    // 1. 初始化
    init() {
      const now = new Date();
      const year = now.getFullYear();
      const month = now.getMonth() + 1;
      this.setData({
        currentYear: year,
        currentMonth: month,
      });
      this.generateCalendar(year, month);
    },

    // 2. 生成日历网格
    generateCalendar(year, month) {
      this.setData({ hasCheckinsThisMonth: true });
      const daysInMonth = new Date(year, month, 0).getDate();
      const firstDayOfWeek = new Date(year, month - 1, 1).getDay();
      const today = new Date();
      const todayDate = today.getDate();
      const isCurrentMonth = year === today.getFullYear() && month === today.getMonth() + 1;

      let days = [];
      // 填充上个月的空白
      for (let i = 0; i < firstDayOfWeek; i++) {
        days.push({ day: 0 }); // 0 表示占位
      }
      // 填充当月日期
      for (let i = 1; i <= daysInMonth; i++) {
        days.push({
          day: i,
          isToday: isCurrentMonth && i === todayDate,
          checkin: null,
          hasMoments: false,
          momentCount: 0,
        });
      }
      this.setData({ days });
      this.fetchCheckinData(year, month);
    },

    // 3. 获取当月打卡数据
    fetchCheckinData(year, month) {
      const token = wx.getStorageSync('token');
      if (!token) return;

      wx.request({
        url: `http://127.0.0.1:8000/api/v1/checkin/month/${year}/${month}`,
        method: 'GET',
        header: { 'Authorization': `Bearer ${token}` },
        success: (res) => {
          if (res.statusCode === 200) {
            const checkinData = res.data; // { "1": {...summary}, "15": {...summary} }
            this.mergeData(checkinData);
            this.setData({
              hasCheckinsThisMonth: Object.keys(checkinData).length > 0
            });
          }
        }
      });
    },

    // 4. 合并打卡数据到日历网格
    mergeData(checkinData) {
      let { days } = this.data;
      days.forEach(dayObj => {
        if (dayObj.day > 0) { // 只处理有效日期
          if (checkinData[dayObj.day]) {
            const summary = checkinData[dayObj.day];
            dayObj.checkin = summary;
            dayObj.hasMoments = !!summary.has_moments;
            dayObj.momentCount = summary.moment_count || 0;
          }
        }
      });
      this.setData({ days });
    },

    // 5. 月份切换
    handleMonthChange(e) {
      const direction = e.currentTarget.dataset.direction;
      let { currentYear, currentMonth } = this.data;
      currentMonth += parseInt(direction);
      if (currentMonth > 12) {
        currentMonth = 1;
        currentYear++;
      } else if (currentMonth < 1) {
        currentMonth = 12;
        currentYear--;
      }
      this.setData({ currentYear, currentMonth });
      this.generateCalendar(currentYear, currentMonth);
    },

    // 6. 点击日期
    handleDayTap(e) {
      const { day } = e.currentTarget.dataset;
      if (day.day === 0) return; // 点击了占位符

      // 将年月日格式化为 YYYY-MM-DD
      const dateStr = `${this.data.currentYear}-${String(this.data.currentMonth).padStart(2, '0')}-${String(day.day).padStart(2, '0')}`;
      
      this.triggerEvent('daytap', {
        date: dateStr,
        hasCheckin: !!day.checkin,
        hasTimeline: !!day.hasMoments,
      });
      this.hide(); // 点击后自动隐藏日历
    },

    // 7. 隐藏组件
    hide() {
      this.setData({ show: false });
    }
  }
})
