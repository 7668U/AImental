# Iteration 009 - Checkin Photo Grid

日期：2026-06-25

## 背景

用户反馈每日打卡记录页添加图片后无法继续下滑，看不到已添加图片；同时希望每日打卡最多可添加 3 张照片。

## 前端调整

修改 `AImental_frontend/pkgDailyCheckin/record.js`：

- 将单图状态 `imageUrl/tempFilePath` 改为 `photos` 数组。
- 新增 `MAX_PHOTOS = 3`，限制最多添加 3 张照片。
- 支持一次从相册/相机选择剩余数量内的多张图片。
- 支持点击已有照片后预览、替换或删除。
- 添加照片后设置 `scrollIntoView = "photo-section"`，自动滚到照片区域。
- 兼容后端未来返回的 `image_urls` 数组；如果只有旧字段 `image_url`，仍能显示第一张旧照片。
- 当前后端仍为单图接口，因此保存时只使用旧接口持久化第一张本地新增照片，避免多张连续上传后被 `image_url` 覆盖。

修改 `AImental_frontend/pkgDailyCheckin/record.wxml`：

- 将照片上传区改为三宫格照片墙。
- 增加照片数量提示：`当前张数 / 3`。
- 已添加照片显示缩略图；未满 3 张时显示“添加照片”入口。

修改 `AImental_frontend/pkgDailyCheckin/record.wxss`：

- 为照片墙增加固定 1:1 网格尺寸，避免图片撑乱布局。
- 增加删除按钮、数量提示、上传提示样式。
- 为滚动内容底部增加余量，避免照片区被底部保存按钮遮挡。

## 后端协作

已通过团队群聊向后端工程师发起需求：

- 消息：`msg-20260625-0004`
- 主题：`daily-checkin-photos`
- 需求：将每日打卡图片从单 `image_url` 升级为最多 3 张照片的存储与接口。

建议后端能力：

- 新增 `image_urls` 字段，建议用 TEXT/JSON 数组保存最多 3 个 URL。
- 保留 `image_url` 作为兼容字段或由 `image_urls[0]` 派生。
- 上传接口支持多图追加或指定索引替换。
- 查询返回中包含 `image_urls: string[]`。
- 提供删除或替换指定图片的语义。
- 后端校验最多 3 张，并兼容旧记录。

## 验证

- `node --check AImental_frontend/pkgDailyCheckin/record.js`：通过。
- 前端已无旧的单图页面结构残留。

## 未完成

- 多图持久化依赖后端扩展完成；当前前端页面内可选择和展示最多 3 张，但旧后端只能保存第一张照片。
