Component({
  properties: {
    show: {
      type: Boolean,
      value: false
    },
    mode: { // 'monthly', 'quarterly', 'yearly'
      type: String,
      value: 'monthly',
      observer: 'updatePicker'
    }
  },

  data: {
    title: '选择月份',
    columns: {
      years: [],
      periods: [] // For months or quarters
    },
    pickerValue: [0, 0], // [yearIndex, periodIndex]
    // 【新增】季度中英文映射表
    quarterMap: [
      { label: '春季', value: 'Q1' },
      { label: '夏季', value: 'Q2' },
      { label: '秋季', value: 'Q3' },
      { label: '冬季', value: 'Q4' }
    ]
  },

  lifetimes: {
    attached() {
      this.updatePicker();
    }
  },

  methods: {
    // Update picker columns based on mode
    updatePicker() {
      const now = new Date();
      const currentYear = now.getFullYear();
      const currentMonth = now.getMonth(); // 0-11
      const currentQuarter = Math.floor(currentMonth / 3); // 0-3

      const years = [];
      for (let i = 2020; i <= currentYear; i++) {
        years.push(i);
      }
      years.reverse();

      let periods = [];
      let title = '';
      let periodIndex = 0;

      switch (this.data.mode) {
        case 'quarterly':
          title = '选择季度';
          // 【修改】使用 quarterMap 生成显示的中文标签
          periods = this.data.quarterMap.map(q => q.label);
          periodIndex = currentQuarter;
          break;
        case 'yearly':
          title = '选择年度';
          break;
        case 'monthly':
        default:
          title = '选择月份';
          for (let i = 1; i <= 12; i++) {
            periods.push(i);
          }
          periodIndex = currentMonth;
          break;
      }

      this.setData({
        title,
        'columns.years': years,
        'columns.periods': periods,
        pickerValue: [0, periodIndex]
      });
    },

    // Handle picker value change
    bindChange(e) {
      this.setData({
        pickerValue: e.detail.value
      });
    },

    // Confirm selection
    handleConfirm() {
      const { years, periods } = this.data.columns;
      const [yearIndex, periodIndex] = this.data.pickerValue;
      
      const selectedYear = years[yearIndex];
      let result = {
        value: selectedYear,
        label: `${selectedYear}年`
      };

      if (this.data.mode === 'monthly') {
        const selectedMonth = periods[periodIndex];
        result.value = `${selectedYear}-${String(selectedMonth).padStart(2, '0')}`;
        result.label = `${selectedYear}年 ${selectedMonth}月`;
      } else if (this.data.mode === 'quarterly') {
        // 【修改】根据索引从映射表中获取正确的标签和值
        const selectedQuarterLabel = this.data.quarterMap[periodIndex].label;
        const selectedQuarterValue = this.data.quarterMap[periodIndex].value;
        result.value = `${selectedYear}-${selectedQuarterValue}`; // API 仍然接收 Q1, Q2...
        result.label = `${selectedYear}年 ${selectedQuarterLabel}`; // 页面显示 春季, 夏季...
      }
      
      this.triggerEvent('confirm', result);
      this.hide();
    },

    hide() {
      this.triggerEvent('close');
    },

    preventScroll() {
      // Empty function to prevent background scroll
    }
  }
});
