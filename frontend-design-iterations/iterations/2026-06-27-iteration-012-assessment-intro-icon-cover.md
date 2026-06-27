# Iteration 012 - Assessment Intro Icon Cover

日期：2026-06-27

## 背景

用户提供参考图，希望每个问卷封面按该风格重新设计。随后用户明确说明：项目已经提供量表图标素材库，路径为 `C:\Users\cxj\Desktop\feelyourself\量表图标`，不需要重新生成图片；封面图直接使用量表图标即可。

因此本轮不走 fhl imagegen，也不生成新封面插画，而是把问卷介绍页改成参考图风格，并直接使用现有量表图标作为封面主体。

## 素材确认

- 源素材库：`量表图标/`，共 18 张 PNG。
- 前端可访问目录：`AImental_frontend/images/assessment/scale-icons/`。
- 当前前端目录已有 19 张 PNG，其中额外 `bdi-ii.png` 是 `SDS/BDI-II` 兼容别名。
- 本轮未新增或替换量表图标。

## 前端调整

修改 `AImental_frontend/pkgAssessment/intro/intro.js`：

- 问卷介绍页图标路径统一指向 `/images/assessment/scale-icons/{short_name}.png`。
- 保留 `BDI-II` 和 `SDS` 的图标别名兼容。
- 清理旧注释，保留加载失败兜底。

修改 `AImental_frontend/pkgAssessment/intro/intro.wxml`：

- 从旧版“标题 + 小图标 + 文本 + 按钮”改为参考图式结构。
- 顶部为统一标题区，保留星光点缀，按用户反馈去掉标题下方横线。
- 中部直接展示量表图标，不再给量表图标增加外层封面框。
- 下方使用两张放大后的玻璃感信息卡展示简短问卷介绍和答题说明。
- 底部固定橙色胶囊按钮。
- 增加加载态和错误态。

修改 `AImental_frontend/pkgAssessment/intro/intro.wxss`：

- 使用奶油白暖色渐变背景。
- 采用固定一屏布局，封面内容不再做可翻动/滚动结构。
- 去掉量表图标外框，仅保留图标本身的尺寸、圆角和居中位置。
- 放大图标下方两张信息卡、卡内图标和文字，让封面各部分面积更接近参考图。
- 固定底部按钮，并保持橙色胶囊按钮的柔和阴影。

## 验证

- `E:\node\node.exe --check AImental_frontend\pkgAssessment\intro\intro.js`：通过。
- 已确认 `intro.wxml/intro.wxss` 中不再存在 `title-underline` 和 `cover-card`。
- PowerShell 确认 `量表图标/` 下有 18 张 PNG。
- PowerShell 确认 `AImental_frontend/images/assessment/scale-icons/` 下有 19 张 PNG，含 `bdi-ii.png` 兼容别名。
- 已确认误生成的 `AImental_frontend/images/assessment/covers/` 和 `frontend-design-iterations/assets/assessment-covers/` 均不存在。
