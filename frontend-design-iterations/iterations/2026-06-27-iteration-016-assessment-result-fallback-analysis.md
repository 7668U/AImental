# 2026-06-27 Iteration 016 - Assessment Result Fallback Analysis

## 背景

用户反馈成人依恋类型测评结果页只显示“焦虑型”，分析区域显示空状态提示，并且页面中间出现大块空白。

## 问题定位

- 后端当前只为 SDS/BDI-II 类测评生成 `ai_analysis`。
- AAS 成人依恋这类分类测评返回的是 `result_interpretation`、`result_recommendation` 和 `result_details`。
- 结果页上一轮改为主要渲染 AI 分析板块后，非 AI 测评没有展示原始解读内容，因此出现空分析卡。
- 页面使用了 `.container` 类名，继承了 `app.wxss` 中的 `height: 100%` 和 `justify-content: space-between`，导致结果卡与分析卡之间被拉开。

## 前端调整

修改 `AImental_frontend/pkgAssessment/result.js`：

- 增加 `analysisTitle` 和 `analysisIsFallback` 状态。
- 保持优先展示后端 `ai_analysis`。
- 当没有 `ai_analysis` 时，使用 `result_details`、`result_interpretation`、`result_recommendation` 构建“结果分析”板块。
- 分类测评的维度得分优先展示在解读和建议前。
- 过滤图片、院校名、AI 原始字段等不适合展示在维度列表里的详情字段。

修改 `AImental_frontend/pkgAssessment/result.wxml`：

- 分析卡标题由固定 `AI 分析` 改为动态 `{{analysisTitle}}`。
- 增加 `details` 类型板块，用于渲染维度得分键值列表。
- 空状态文案改为通用表达，不再把所有无内容情况都归因为 AI 未返回。

修改 `AImental_frontend/pkgAssessment/result.wxss`：

- 结果页 `.container` 增加 `height: auto` 和 `justify-content: flex-start`，覆盖全局布局干扰。
- 增加维度得分列表样式。
- 兜底结果分析板块继续使用前一轮的背景图标素材。

## 验证

- `E:\node\node.exe --check AImental_frontend\pkgAssessment\result.js`：通过。
- `git diff --check -- AImental_frontend\pkgAssessment\result.js AImental_frontend\pkgAssessment\result.wxml AImental_frontend\pkgAssessment\result.wxss`：通过，仅有 Git 的 CRLF 提示。

## 注意

- 本轮只修前端展示逻辑，不改变后端 AI 分析生成范围。
- 之后如果后端为更多测评补齐 `ai_analysis`，结果页会自动优先展示 AI 分析。
