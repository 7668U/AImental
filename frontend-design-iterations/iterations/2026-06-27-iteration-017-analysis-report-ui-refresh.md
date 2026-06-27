# Iteration 017 - 心情分析报告 UI 刷新

## 背景

用户希望重做 `心情分析报告` 页面，使其更接近提供的参考稿：

- 顶部标题、周期选择器、四个分析入口卡片更圆润、饱满、暖色。
- 四个分析入口换成用户提供的水彩插画。
- 下方 `心情解读` 卡片按模板图接入爱心和太阳云朵小图案。
- 饼图内部如果不好加背景，先不加，只优化外层卡片。

## 素材处理

从用户提供的四宫格插画中裁切并去底，新增：

- `AImental_frontend/images/daily-checkin/analysis/report-mood-distribution.png`
- `AImental_frontend/images/daily-checkin/analysis/report-status-correlation.png`
- `AImental_frontend/images/daily-checkin/analysis/report-text-analysis.png`
- `AImental_frontend/images/daily-checkin/analysis/report-color-card.png`

从用户提供的心情解读装饰图中去掉棋盘格底并裁切，新增：

- `AImental_frontend/images/daily-checkin/analysis/report-heart.png`
- `AImental_frontend/images/daily-checkin/analysis/report-sun-cloud.png`

从用户提供的 AI 报告装饰图中去掉棋盘格底并裁切，新增：

- `AImental_frontend/images/daily-checkin/analysis/report-ai-deco.png`

从用户提供的小星星和绿叶图中去掉棋盘格底并裁切，新增：

- `AImental_frontend/images/daily-checkin/analysis/report-star.png`
- `AImental_frontend/images/daily-checkin/analysis/report-leaf.png`

## 页面实现

修改 `AImental_frontend/pkgDailyCheckin/analysis.wxml`：

- 标题区增加轻装饰。
- 四个分析入口改为图标 + 标题 + 副文案的横向卡片。
- 图表卡增加标题行，但不向饼图内部添加背景。
- 图表卡标题行使用真实绿叶和小星星素材，替换此前临时 CSS 图形。
- 情绪分布、文字分析、情绪色卡三个饼图统一为文字分析同款样式：顶部图例、无外侧标签、白色分隔和柔和阴影。
- `心情解读` 卡片接入爱心标题图标和太阳云朵右上角装饰。
- `心情解读` 文案改为读取后端 AI 返回的 `summary_text`，只展示最明显的 1-2 句短总结。
- `AI 分析报告` 卡片接入右上角 AI 小机器人装饰图，降低透明度，避免压住正文。
- 缩小并上移 `AI 分析报告` 右上角装饰图，正文恢复满宽，避免第二行以后出现大块留白。

修改 `AImental_frontend/pkgDailyCheckin/analysis.wxss`：

- 页面背景改为暖白到奶油色渐变。
- 周期选择器改为胶囊分段控件，选中态使用暖橙渐变。
- 四个入口卡片使用大圆角、轻边线、柔和阴影和差异化浅色底。
- 内容卡片统一为 30rpx 圆角、暖白玻璃感、轻阴影。
- 心情解读卡增加虚线分隔和右上角装饰层级。
- 修正自定义导航栏占位导致的顶部空白，将报告内容整体上移，避免滑动时标题上方出现大段留白。

## 验证

- 已确认 WXML 引用的新素材路径均存在。
- 已执行 `git diff --check`，未发现空白错误。
- 未运行微信开发者工具真机/模拟器预览；后续建议在小程序环境中查看不同机型下四宫格文字是否仍舒展。
