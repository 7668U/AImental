# Iteration 002 - Deprecated FHL Responses Imagegen Setup

日期：2026-06-24

## 状态

已废弃。2026-06-24 晚用户指出 fhl Responses API 生图链路会把 base64 图片输出按 token 计费，造成异常高成本。后续不得再使用本轮 Responses API 配置。

新的正确方案见：

`frontend-design-iterations/iterations/2026-06-24-iteration-003-switch-to-images-api.md`

## 背景

用户提供了本地生图技能文档：

`C:/Users/29537/OneDrive/Desktop/漫画/tools/imagegen/FHL_RESPONSES_IMAGEGEN_SKILL.md`

用户要求：

- 学习并配置该技能。
- 为前端角色写一份角色卡。
- 角色卡必须包含该技能的完整安装事项。
- 明确说明我可以正常使用该技能为前端生成所需图片素材。

## 本轮实施

- 迁移 `tools/imagegen` 到当前项目。
- 迁移 `tools/image-studio/shared` 到当前项目，提供 Responses payload 构造逻辑。
- 创建根目录 `package.json`，加入 `imagegen:responses` 脚本。
- 创建根目录 `.env`，写入 fhl Responses API 所需配置。
- 更新 `.gitignore`，避免 `.env` 和 raw 响应进入版本库。
- 新增前端角色卡：`frontend-design-iterations/frontend-ui-designer-role-card.md`。

## 安全处理

- API key 只写入本地 `.env`。
- 迭代文档和角色卡只记录 `sk-REDACTED`。
- 不在前端文档里保存完整密钥。

## 验证结果

- `npm install`：通过。
- `node --check tools/imagegen/generate-responses.mjs`：通过。
- smoke test：通过，已生成 `output/imagegen/fhl-responses-smoke.png`。
- 实际调用参数确认：`baseURL=https://www.fhl.mom`，`textModelID=gpt-image-2`，`imageTool=gpt-image-2`，`quality=low`。

## 后续使用约定

- 本轮 Responses API 约定全部作废。
- 后续只允许使用 Images API：`npm run imagegen:images`。
