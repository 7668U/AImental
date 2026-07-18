const {
  PRIVACY_POLICY,
  savePrivacyConsent
} = require('../../utils/privacy.js');

Component({
  properties: {
    visible: {
      type: Boolean,
      value: false,
      observer(isVisible) {
        if (isVisible) {
          this.setData({
            checked: false,
            detailVisible: false
          });
        }
      }
    }
  },

  data: {
    policy: PRIVACY_POLICY,
    checked: false,
    detailVisible: false
  },

  methods: {
    preventTouchMove() {},

    toggleChecked() {
      this.setData({ checked: !this.data.checked });
    },

    openDetails() {
      this.setData({ detailVisible: true });
    },

    closeDetails() {
      this.setData({ detailVisible: false });
    },

    confirmConsent() {
      if (!this.data.checked) {
        return;
      }
      const consent = savePrivacyConsent();
      this.triggerEvent('confirm', consent);
    },

    rejectConsent() {
      this.setData({
        checked: false,
        detailVisible: false
      });
      this.triggerEvent('reject');
    }
  }
});
