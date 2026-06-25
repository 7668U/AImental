# Iteration 005 - Daily Checkin Layout Draft

日期：2026-06-24

## 背景

用户希望重排“心情日记 / 每日打卡”页面：

- 纸飞机已经独立为底栏模块，不再出现在本页。
- 心灵记事簿暂时隐藏。
- 页面只保留三个核心模块：
  - 大正方形：今日打卡
  - 小正方形：心情日历
  - 小正方形：心情分析

## 本轮产物

- 第一版结构设计稿：
  - `frontend-design-iterations/assets/daily-checkin-layout/daily-checkin-layout-v1.png`
- 第二版结构设计稿：
  - `frontend-design-iterations/assets/daily-checkin-layout/daily-checkin-layout-v2.png`

## 设计方向

- 维持当前小程序的奶白背景、白色圆角卡片、橙色图标与柔和阴影。
- 将“今日打卡”提升为页面主行动，用大面积正方形卡片承载。
- 下方两个入口等宽并排，形成清晰的 1 + 2 网格。
- 底栏沿用上一轮调整后的结构：心理咨询 / 心理测评 / 心情日记 / 纸飞机 / 我的。

## V2 修正

- 将大卡图标改为居中圆形徽章，弱化第一版的大插画感。
- 将两个小卡图标统一为同尺寸圆形图标区，确保居中。
- 将小卡标题和副标题改为居中排布，提升整体协调性。
- 调整主卡内标题、副标题、按钮的垂直节奏，让大卡更像可点击主入口。

## 工具情况

- 内置 imagegen 返回服务端错误。
- 项目 fhl Images API 返回 `No available compatible accounts`。
- 本轮先用本地渲染方式生成候选结构稿，待用户确认方向后再进入前端实现。

## 页面实现

用户确认采用第二版方向后，本轮已进入前端落地：

- 生成并保存模块素材：
  - `AImental_frontend/images/daily-checkin/layout/checkin-hero.png`：大卡主插画，1024x768。
  - `AImental_frontend/images/daily-checkin/layout/calendar-card.png`：心情日历图标，512x512。
  - `AImental_frontend/images/daily-checkin/layout/analysis-card.png`：心情分析图标，512x512。
- 修改 `AImental_frontend/pages/daily-checkin/index.wxml`：
  - 保留顶部问候语。
  - 大卡绑定 `goToRecord`。
  - 两个小卡分别绑定 `openCalendar` 和 `goToStatistics`。
  - 移除心灵记事簿入口。
- 修改 `AImental_frontend/pages/daily-checkin/index.wxss`：
  - 大卡固定为 670rpx 高度，接近内容宽度，形成主方卡。
  - 小卡固定为 321rpx x 321rpx，左右并排。
  - 使用固定图片尺寸和 `aspectFit`，避免图标加载导致布局跳动。

## 实现验证

- `node --check AImental_frontend/pages/daily-checkin/index.js`：通过。
- 三张素材尺寸检查通过：
  - `checkin-hero.png`：1024x768 RGBA。
  - `calendar-card.png`：512x512 RGBA。
  - `analysis-card.png`：512x512 RGBA。
- `rg` 检查确认页面内不再残留“心灵记事簿”和“纸飞机”旧入口。

## 主卡素材替换

用户提供了更满意的“每日打卡”参考图，希望用 fhl 重新生成一次，并尽量只做尺寸和格式适配。

执行情况：

- 已发起一次 fhl Images API 编辑请求。
- fhl 返回 `No available compatible accounts`，未生成成功。
- 当前先将用户参考图本地适配成 `1024x608` PNG，替换：
  - `AImental_frontend/images/daily-checkin/layout/checkin-hero.png`
- 旧本地绘制版本备份为：
  - `AImental_frontend/images/daily-checkin/layout/checkin-hero-local-generated.png`

说明：

- 当前前端仍引用同名 `checkin-hero.png`，无需额外改代码。
- 后续 fhl 可用后，可以直接用 fhl 成功产物覆盖同名文件。

## 心情日历素材替换

用户提供了新的心情日历素材图，要求直接替换。

执行情况：

- 原图为 RGB，棋盘格背景是烘焙背景，不是真透明。
- 已通过本地处理抠除浅色棋盘格背景，输出为 `512x512 RGBA PNG`。
- 已替换：
  - `AImental_frontend/images/daily-checkin/layout/calendar-card.png`
- 旧本地绘制版本备份为：
  - `AImental_frontend/images/daily-checkin/layout/calendar-card-local-generated.png`

验证：

- `calendar-card.png` 尺寸为 `512x512`，RGBA，alpha 范围 `0-255`。
- `AImental_frontend/pages/daily-checkin/index.wxml` 已引用该同名素材。

## 心情分析素材替换

用户提供了新的心情分析素材图，要求直接替换。

执行情况：

- 原图为 RGB，棋盘格背景是烘焙背景，不是真透明。
- 已通过本地处理抠除浅色棋盘格背景，输出为 `512x512 RGBA PNG`。
- 已替换：
  - `AImental_frontend/images/daily-checkin/layout/analysis-card.png`
- 旧本地绘制版本备份为：
  - `AImental_frontend/images/daily-checkin/layout/analysis-card-local-generated.png`

验证：

- `analysis-card.png` 尺寸为 `512x512`，RGBA，alpha 范围 `0-255`。
- `AImental_frontend/pages/daily-checkin/index.wxml` 已引用该同名素材。

## 小卡箭头移除

用户认为“心情日历”和“心情分析”小卡底部的小右箭头多余。

执行情况：

- 移除 `AImental_frontend/pages/daily-checkin/index.wxml` 中两个 `.secondary-arrow` 节点。
- 删除 `AImental_frontend/pages/daily-checkin/index.wxss` 中 `.secondary-arrow` 样式。
- 将 `.secondary-card` 调整为 `justify-content: center`，使图片、标题和说明在小卡中整体居中。

验证：

- `rg` 检查确认页面中不再残留 `secondary-arrow` 或 `›`。
- `node --check AImental_frontend/pages/daily-checkin/index.js`：通过。
