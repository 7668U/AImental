# Iteration 007 - Checkin 24-Dimension Icons

日期：2026-06-25

## 背景

产品经理在群聊中定版每日打卡三维度 V1：

- 心情：24 项，单选。
- 状态：24 项，至少 1 个、最多 3 个。
- 颜色：24 项，单选，按 6 组 × 4 色呈现。

本轮用户已提供心情和状态两张高清图标总图，希望前端裁切并应用到每日打卡记录页。

## 素材处理

心情总图：

- 输入为 4 列 6 行、无文字高清图。
- 裁切为 24 个 `256x256 RGBA PNG`。
- 输出目录：`AImental_frontend/images/daily-checkin/record/mood24/`。
- 归档目录：`frontend-design-iterations/assets/daily-checkin-record/mood-24-crops/`。

状态总图：

- 输入为 6 列 4 行高清图。
- 裁切为 24 个 `256x256 RGBA PNG`。
- 输出目录：`AImental_frontend/images/daily-checkin/record/status24/`。
- 归档目录：`frontend-design-iterations/assets/daily-checkin-record/status-24-crops/`。

## 页面实现

修改 `AImental_frontend/pkgDailyCheckin/record.js`：

- 新增 `MOOD_OPTIONS`，包含 24 个心情项及情绪族、倾向、能量元信息。
- 新增 `handleMoodSelect`，心情保持单选。
- 新增 `STATUS_OPTIONS`，按产品 Iteration 008 的顺序写入 24 个状态。
- 状态选择限制为最多 3 个。
- 为旧状态标签补兼容映射，例如“工作”映射为“搬砖”，“出游/出行/远足”映射为“旅行”。

修改 `AImental_frontend/pkgDailyCheckin/record.wxml`：

- 心情区改为直接展示 24 项 6x4 网格。
- 状态区改为 24 项 6x4 网格，并显示“最多选 3 个”提示。
- 颜色区改为 24 项 4 列 6 行色盘，选中后只居中展示颜色名。
- 移除关键词输入区；将天气标签替换为可点击刷新的 GPS 定位标签；底部保存按钮改为 flex 居中。
- 图标路径切换为：
  - `/images/daily-checkin/record/mood24/{{item.icon}}.png`
  - `/images/daily-checkin/record/status24/{{item.icon}}.png`

修改 `AImental_frontend/pkgDailyCheckin/record.wxss`：

- 新增心情/状态 6 列网格样式。
- 新增选中态、图标尺寸、状态提示、定位标签和底部按钮居中样式。
- 保持与当前记录页一致的奶白卡片、暖橙选中态和柔和阴影。

## 验证

- `node --check AImental_frontend/pkgDailyCheckin/record.js`：通过。
- 心情动态图标：24 个数据项均找到对应 PNG。
- 状态动态图标：24 个数据项均找到对应 PNG。
- 所有心情/状态裁切图均为 `256x256 RGBA`。
- `node -e "JSON.parse(require('fs').readFileSync('AImental_frontend/app.json','utf8'))"`：通过。
- 关键词和天气旧字段无前端展示残留。

## 后续

- 当前定位只在前端展示 GPS 坐标，后端打卡模型尚未保存 location 字段；如需沉淀位置，需要后端扩展字段后再随打卡提交。
- 状态区当前直接展示 24 项；如果真机高度显得拥挤，可进一步优化卡片高度或分组视觉。
