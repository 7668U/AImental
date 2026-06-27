# 2026-06-26 Iteration 004 - AI Therapist Interface Redesign

## Trigger

用户要求调整前端“心理咨询界面”，参考两张截图：

- 默认进入后展示“AI陪伴”聊天界面。
- 点击左上角“项目”后，左侧弹出项目栏/历史对话栏。

## Scope

本轮修改集中在：

- `AImental_frontend/pages/ai-therapist/index.wxml`
- `AImental_frontend/pages/ai-therapist/index.wxss`
- `AImental_frontend/pages/ai-therapist/index.js`

## Design And Interaction

- 顶部从原菜单图标改为“项目”胶囊按钮，右侧改为三点设置入口。
- 根据用户反馈，移除顶部“AI陪伴 / 温暖倾听 · 理解你的每一刻”标题区域，让顶部只保留功能入口。
- 使用用户提供的背景素材作为整屏底图：`AImental_frontend/images/ai-therapist/chat-bg-window.png`。
- 使用用户提供的小盆栽素材作为顶部提示左侧装饰：`AImental_frontend/images/ai-therapist/plant-buddy.png`。
- 使用用户提供的纸飞机素材作为用户消息旁的轻量装饰：`AImental_frontend/images/ai-therapist/paper-plane.png`。
- 顶部陪伴提示条改为白色透明圆角卡片，并加入柔和阴影。
- AI 消息使用白色半透明气泡，用户消息使用浅橙气泡，并保留消息时间展示。
- 气泡加入阴影、圆角和尖角，贴近参考图的悬浮卡片质感。
- 用户气泡改为纯浅橘色，不使用渐变色。
- 底部输入区改为透明悬浮圆角矩形，内部保留白色输入框 + 橙色“发送”按钮。
- 发送按钮增加小纸飞机形状符号。
- 点击“项目”后，主内容右移，左侧项目栏显示“历史对话”、新建入口、设置入口和历史会话列表。

## Implementation Notes

- 保留原有后端接口：`/chats/`、`/chats/{id}`、`/chats/{id}/respond` 等。
- 历史会话列表先使用 `/chats/` 返回的 id/title 做基础展示，再异步读取前 12 条详情补充日期和摘要。
- 如果后端摘要字段不足，前端会从会话 message 中提取最近一条用户消息作为预览。
- 新建聊天欢迎语统一为更贴近“AI伙伴”的口吻。

## Verification

- 已执行 `node --check AImental_frontend/pages/ai-therapist/index.js`，语法检查通过。
- 已扫描目标页面文件，未发现冲突标记或明显样式拼写残留。

## 2026-06-27 Refinement

- 将入口与侧栏标题中的“项目”改为“历史”。
- 调整欢迎气泡、小盆栽、用户气泡和纸飞机素材的边界距离，让元素不再贴边。
- 小盆栽素材适当放大，并继续使用透明抠图资源。
- 移除发送按钮内的白色纸飞机三角，只保留“发送”文字。
- 为表情按钮增加可点击表情面板，选择后会追加到输入框。
- 在输入栏右上方增加置顶按钮，长聊天记录可快速回到顶部。

## Follow Up

- 需要在微信开发者工具中预览真机尺寸，微调左侧项目栏宽度、气泡行高和底部 tabBar 上方安全距离。
- 如果后端后续能直接在 `/chats/` 返回 timestamp / last_message_snippet，可移除前端逐条 enrich 请求。
