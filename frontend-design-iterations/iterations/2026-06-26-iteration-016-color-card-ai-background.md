# Iteration 016 - 情绪色卡 AI 背景接入

日期：2026-06-26

## 目标

把 `emotion-color-palette-lab` 的混色、生图与缓存思路接入主小程序的每日打卡颜色分析流程。第一版不新增颜色维度，沿用现有 24 色。

## 最小接法

- 后端新增情绪色卡背景缓存表，按周期内颜色分布生成 palette signature。
- 如果同一综合色板已生成过 AI 背景图，直接返回数据库中的静态图 URL。
- 如果没有缓存，则基于周期内颜色混合结果生成无字 3:4 背景图，保存到 `static/emotion-color-cards/` 并写入缓存表。
- 小程序 `情绪色卡` 分析结果保留原颜色饼图，并在其下方展示 AI 颜色背景图。

## 实现文件

- `AImental_backend/model/emotion_color_card.py`
- `AImental_backend/router/analysis.py`
- `AImental_backend/main.py`
- `AImental_frontend/pkgDailyCheckin/analysis.js`
- `AImental_frontend/pkgDailyCheckin/analysis.wxml`
- `AImental_frontend/pkgDailyCheckin/analysis.wxss`

## 验证

- `python -m compileall` 通过。
- `node --check AImental_frontend/pkgDailyCheckin/analysis.js` 通过。
- 使用后端 `.venv` 导入 `main` 成功。
- 用内存数据库验证同一 palette signature 会命中缓存并返回 `cached: true`。

## 备注

本次没有主动触发真实生图请求，避免在开发验证阶段消耗图片额度。

## 追加调整

- 删除「AI 颜色背景图」标题和「新生成/已复用」状态标签。
- 色卡图上只覆盖颜色名，不再显示副标题。
- 颜色名改为居中、白色、宋体系艺术字效果，更接近实验页导出色卡的观感。

## 分析门槛调整

- 分析页点击任一分析维度前，先检查当前月/季/年的打卡天数。
- 不大于 5 天时弹出提示，不再请求图表、AI 报告或 AI 色卡背景。
- 新增本地开发种子能力，可为当前用户补 5 天测试打卡数据。
