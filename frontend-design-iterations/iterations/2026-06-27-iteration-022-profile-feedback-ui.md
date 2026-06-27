# Iteration 022 - Profile Feedback UI

日期：2026-06-27

## 背景

用户提供“意见反馈”界面参考图，并将背景素材放入 `UI素材/意见反馈背景.png`，希望将“我的”板块中的意见反馈页改成同一套暖橙、白色卡片、轻插画背景的视觉主题。

## 本轮实施

- 将 `UI素材/意见反馈背景.png` 复制为小程序资源 `AImental_frontend/images/profile/feedback-bg.png`。
- 重构 `AImental_frontend/pkgProfile/feedback.wxml`，使用整页背景、自定义导航、反馈类型卡片、建议内容卡片和居中提交按钮。
- 重写 `AImental_frontend/pkgProfile/feedback.wxss`，对齐参考图的暖橙主题、白色圆角卡片、胶囊选项、文本框和按钮阴影。
- 调整 `AImental_frontend/pkgProfile/feedback.js` 的自定义导航尺寸计算，与“个人信息 / 测试历史”页保持一致。
- 修正提交按钮绑定，从不存在的 `submitFeedback` 改为现有 `handleSubmit`，避免点击无响应。

## 验证

- `node --check AImental_frontend/pkgProfile/feedback.js` 通过。
- 已确认 WXML 中使用 `/images/profile/feedback-bg.png`。
- 已确认 `submitFeedback` 旧绑定不再存在。
