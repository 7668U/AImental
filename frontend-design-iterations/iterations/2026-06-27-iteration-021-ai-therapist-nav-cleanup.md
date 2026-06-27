# Iteration 021 - AI Therapist Nav Cleanup

## 背景

用户反馈心理咨询界面右上角的三点按钮多余，希望去掉；同时希望底部 tab 中“心理咨询”改名为“心情树洞”。

## 页面实现

- 移除 `AImental_frontend/pages/ai-therapist/index.wxml` 顶部导航右侧自定义三点按钮。
- 删除 `AImental_frontend/pages/ai-therapist/index.wxss` 中不再使用的 `.more-button` 和 `.more-dot` 样式。
- 设置入口仍保留在左侧历史抽屉顶部的齿轮按钮中。
- 更新 `AImental_frontend/app.json` tabBar 文案：`心理咨询` -> `心情树洞`。

## 验证

- 已搜索 `more-button` / `more-dot`，确认无残留引用。
- 已搜索 `心理咨询`，仅剩报告免责声明中的普通语义文本，不属于 tab 文案。
- `node --check AImental_frontend/pages/ai-therapist/index.js`：通过。

## 说明

截图右上角微信原生胶囊按钮属于小程序系统控件，不能由页面代码真正删除；本轮删除的是页面内自定义的三点设置按钮。
