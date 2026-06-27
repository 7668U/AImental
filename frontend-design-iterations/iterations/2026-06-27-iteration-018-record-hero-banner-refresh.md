# Iteration 018 - 每日打卡记录页顶部 Banner 替换

## 背景

用户认为 `记录今日心情` 顶部卡片原有插画较粗糙，希望替换为新的太阳云朵背景图，并调整文案排版，避免副标题碰到右侧图案。

## 素材处理

从用户提供的新图中去掉棋盘格底，裁切为透明横向 banner：

- `AImental_frontend/images/daily-checkin/record/banner-art-sun.png`

保留旧素材 `banner-art.png`，不覆盖，便于回退。

## 页面实现

修改 `AImental_frontend/pkgDailyCheckin/record.wxml`：

- 顶部 hero 图从 `banner-art.png` 替换为 `banner-art-sun.png`。
- 移除导航栏右上角报告按钮和更多按钮。

修改 `AImental_frontend/pkgDailyCheckin/record.wxss`：

- 调整 hero 文案区域最大宽度。
- 标题字号从 58rpx 收为 54rpx。
- 副标题字号从 27rpx 收为 25rpx，并限制最大宽度，让文本提前折行。
- 右侧插画尺寸和位置调整为更适合新太阳云朵素材。
- 删除右上角导航按钮相关样式。

修改 `AImental_frontend/pkgDailyCheckin/record.js`：

- 删除右上角报告按钮和更多按钮对应的点击方法。

## 验证

- 已确认新图片路径存在。
- 已执行 `git diff --check`，未发现空白错误。
- 未运行微信开发者工具预览，建议在模拟器中确认不同机型的标题与副标题折行效果。
