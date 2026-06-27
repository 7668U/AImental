# 2026-06-27 Iteration 015 - Assessment Result Section Icons

## 背景

用户希望在测评结果分析界面的其他板块中添加背景图标，并提供两张候选素材：太阳云朵图、AI 小机器人分析图。

## 素材判断

两张素材整体风格与当前结果页暖色背景一致，适合使用。

- 太阳云朵图更适合表达陪伴、恢复、行动建议和持续记录。
- AI 小机器人分析图更适合表达 AI 分析、维度拆解、原因分析和专业支持。
- 原始素材带烘焙棋盘格背景，不能直接进入前端使用，已处理为透明 PNG。

## 素材

- 原始太阳云朵：`frontend-design-iterations/assets/assessment-result-section-icons/sun-source.png`
- 原始 AI 图标：`frontend-design-iterations/assets/assessment-result-section-icons/ai-source.png`
- 当前页面参考截图：`frontend-design-iterations/assets/assessment-result-section-icons/result-page-icon-reference.png`
- 前端太阳云朵：`AImental_frontend/images/assessment/result/section-sun.png`
- 前端 AI 图标：`AImental_frontend/images/assessment/result/section-ai.png`

## 前端调整

修改 `AImental_frontend/pkgAssessment/result.js`：

- 为 AI 分析 sections 增加 `bgIcon` 字段。
- 当前状态、可以先试试、持续记录使用太阳云朵图。
- 主要影响维度、可能相关原因、专业支持使用 AI 小机器人图。
- 安全提醒不设置背景图标，避免影响风险提示的严肃性。

修改 `AImental_frontend/pkgAssessment/result.wxml`：

- 在每个 AI 分析板块内按 `bgIcon` 渲染背景图标。
- 空分析卡增加 AI 小机器人背景图标。

修改 `AImental_frontend/pkgAssessment/result.wxss`：

- 背景图标以低透明度水印形式展示。
- 内容区域单独设置层级，保证文字在背景图标上方。
- 维度卡片保持浅暖色底，避免背景图标干扰阅读。

## 验证

- `E:\node\node.exe --check AImental_frontend\pkgAssessment\result.js`：通过。
- `section-sun.png` 和 `section-ai.png` 均已确认左上角透明，尺寸分别为 `420x390` 和 `420x298`。

## 注意

- 本轮只调整结果分析板块视觉，不改变结果计算、AI 分析结构和后端接口。
- 未在微信开发者工具中截图验收，后续可按真实机型截图微调图标透明度和位置。

## 后续修正

用户反馈素材没有在结果分析板块中明显体现。已调整：

- 为带背景图标的分析板块增加 `has-section-icon` 标记。
- 将图标从极淡水印改为右侧明确可见的背景图标。
- 提高图标透明度，普通文字板块约 `0.58`，分析类板块约 `0.5`。
- 为文字内容增加右侧留白，避免图标遮挡阅读。
