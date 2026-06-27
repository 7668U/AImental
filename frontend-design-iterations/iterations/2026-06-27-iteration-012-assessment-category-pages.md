# Iteration 012 - Assessment Category Pages

日期：2026-06-27

## 背景

用户反馈心理测评首页不应该在最下方展示横幅，也不应该在首页直接展开具体量表内容。正确结构应为：

- 首页只展示四个测评类别入口。
- 点击类别后进入新的 UI 子页面。
- 每个子页面展示该类别下的具体量表。
- 具体量表图标统一替换为用户提供的 `量表图标/` 素材。

## 前端调整

修改 `AImental_frontend/pages/assessment/index.wxml`：

- 移除首页底部横幅。
- 移除首页内展开量表列表。
- 四个分类卡点击后跳转到 `pkgAssessment/category/category`。

修改 `AImental_frontend/pages/assessment/index.js`：

- 保留测评列表请求，仅用于计算四个分类的量表数量。
- `goToCategory` 跳转到分类子页面并传入 `group`。
- 兼容 `SDS` 与 `BDI-II` 的分组统计。

新增 `AImental_frontend/pkgAssessment/category/`：

- `category.json`
- `category.js`
- `category.wxml`
- `category.wxss`

分类子页面能力：

- 根据 `group` 参数渲染心理健康、自我人格、关系亲密、趣味探索四类页面。
- 使用用户提供的分类顶部插画素材。
- 心理健康、自我人格、关系亲密采用大标题 + 插画 + 箭头式量表卡片。
- 趣味探索采用大标题 + 插画 + “去测试”按钮式量表卡片。
- 点击量表卡片进入原有 `pkgAssessment/intro/intro` 页面。

修改 `AImental_frontend/app.json`：

- 将 `category/category` 注册到 `pkgAssessment` 子包。

修改 `AImental_frontend/pkgAssessment/intro/intro.js` 和 `AImental_frontend/pkgProfile/history.js`：

- 具体量表图标路径统一切换到 `/images/assessment/scale-icons/`。
- 兼容 `SDS` 和 `BDI-II` 图标文件名。

## 素材处理

新增量表图标目录：

- `AImental_frontend/images/assessment/scale-icons/`

来源：

- `C:/Users/cxj/Desktop/feelyourself/量表图标`

已复制 18 个量表图标，并额外保留 `bdi-ii.png` 与 `sds.png` 双文件名兼容。

新增分类页顶部插画目录：

- `AImental_frontend/images/assessment/category/`

素材：

- `health-hero.png`
- `personality-hero.png`
- `relationship-hero.png`
- `interest-hero.png`

处理：

- 对用户提供的透明背景素材进行了外部棋盘格透明化处理，避免小程序内露出灰白棋盘格。
- 同步归档到 `frontend-design-iterations/assets/assessment-category/`。

## 验证

- 静态搜索确认首页旧的 `isScaleListOpen`、`switchGroup`、`scale-section` 和 `gentle-banner` 不再存在。
- 已确认 `pkgAssessment/category/category` 注册进 `app.json`。
- 已确认前端具体量表图标引用切换到 `/images/assessment/scale-icons/`。
- 尚未在微信开发者工具中真机预览，后续需要检查子页面首屏高度和卡片间距。

## 2026-06-27 Follow-up

按用户反馈继续调整：

- 首页四个分类卡不再展示量表英文缩写摘要。
- 首页四个分类卡不再展示“x 项”数量。
- 分类子页面的量表卡片不再展示英文简称 tag。
- 趣味探索页面中的量表标题去掉括号内英文名，例如“性格类型测试（TPS）”改为“性格类型测试”。
- 首页不再为了统计数量请求测评列表，进入分类子页面后再加载对应量表。
