# Iteration 021 - Profile Test History UI

日期：2026-06-27

## 背景

用户提供“测试历史”页面参考图，希望修改“我的”板块中的测试历史界面，并要求：

- 页面标题改成“测试历史”。
- 标题字体、颜色与“我的信息”界面标题一致。
- “拖延程度评估量表”前面的图标不要，量表标题和日期左侧对齐。

## 本轮实施

- 重构 `AImental_frontend/pkgProfile/history.wxml`，改为自定义导航、背景图、滚动内容和白色历史记录卡片布局。
- 重写 `AImental_frontend/pkgProfile/history.wxss`，复用“我的信息”页的导航标题样式：`38rpx`、`900`、`#70472f`。
- 移除历史卡片中的量表图标渲染，使量表标题、日期、得分从同一左边距开始。
- 将 `AImental_frontend/pkgProfile/history.json` 设置为 `navigationStyle: custom`，避免系统导航和自定义导航叠加。
- 在 `AImental_frontend/pkgProfile/history.js` 中增加自定义导航高度计算、返回方法、请求超时，并将历史分组默认展开。
- 清理已不再使用的量表图标路径与图标加载失败兜底逻辑。

## 验证

- `node --check AImental_frontend/pkgProfile/history.js` 通过。
- 已确认 WXML/WXSS/JS 中不再出现 `scale-icon`、`iconPath`、`DEFAULT_ICON`。
- 已确认页面标题为“测试历史”，未再出现“您的历史测试记录”。
- 已确认 `history.wxss` 与 `inform.wxss` 的 `.nav-title` 关键字号、字重和颜色一致。
