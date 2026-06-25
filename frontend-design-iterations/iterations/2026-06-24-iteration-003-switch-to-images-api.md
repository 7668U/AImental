# Iteration 003 - Switch Imagegen To Images API

日期：2026-06-24

## 背景

用户指出前一轮 Responses API 生图链路存在重大计费问题：fhl 的 Responses 接口会把 base64 图片输出当作 token 计费，导致单张图片成本异常高。

用户要求改用管理员指定方案：

- 教程地址：`https://docs.qq.com/doc/DRnhCVUVUZ0ZoRnVP`
- 网站后台地址：`https://www.fhl.mom/`
- 生图项目地址：`https://github.com/RoseKhlifa/Image-Studio`
- 使用 Image-2 专用生图分组。
- 上游配置选择 `Images API`。

## 本轮实施

- 重新读取用户更新后的本地技能卡。
- 同步 `tools/imagegen/generate-gpt-image-2.mjs` 为 Images API 版本。
- 同步 `tools/imagegen/run-gpt-image-2.ps1`。
- 同步 `tools/imagegen/README.md` 和技能卡内容。
- 将 `package.json` 脚本改为 `imagegen:images`。
- 将旧的 `generate-responses.mjs` 和 `run-responses.ps1` 改为直接失败，避免误触。
- 更新 `.env` 为 Images API 所需配置，移除 Responses/text model 相关项。
- 重写前端角色卡中的 imagegen 技能说明。

## 无扣费验证

- `Select-String` 检查确认：当前可执行脚本只出现 `/v1/images/generations` 和 `/v1/images/edits`。
- `node --check tools/imagegen/generate-gpt-image-2.mjs`：通过。
- `npm run imagegen:images -- --help`：通过。

## 唯一真实 Smoke Test

用户允许在确认 Images API 后只生成一张测试图片。本轮只执行了一次真实生图：

```powershell
npm run imagegen:images -- --prompt "A tiny cozy cup of tea on a wooden desk, warm light, clean soft illustration, no text, no watermark" --size 1024x1024 --quality low --format png --out output/imagegen/fhl-images-smoke.png --raw-out output/imagegen/raw/fhl-images-smoke.json
```

结果：

- 生成成功。
- 输出图片：`output/imagegen/fhl-images-smoke.png`
- 实际返回：`model=gpt-image-2`，`size=1329x1183`，`quality=low`，`output_format=png`。
- 已查看图片，文件内容正常。

## 风险约束

- 后续 fhl 生图严禁使用 `/v1/responses`。
- 每次真实生图前，优先确认调用入口是 `imagegen:images`。
- 真实 smoke test 只允许生成一张。
