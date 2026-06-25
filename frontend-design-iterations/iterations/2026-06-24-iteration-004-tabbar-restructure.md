# Iteration 004 - Bottom TabBar Restructure

日期：2026-06-24

## 背景

用户希望先重排小程序底部菜单栏：

- 去掉“心灵社区”按钮，前端暂时不展示。
- “每日打卡”放到底部中间，替代原“心灵社区”位置。
- “纸飞机”模块独立成底栏第四个按钮，占用原“每日打卡”位置。

## 本轮实施

- 修改 `AImental_frontend/app.json` 的 `tabBar.list`。
- 将底部入口调整为：
  - 心理咨询
  - 心理测评
  - 心情日记
  - 纸飞机
  - 我的
- 新增主包页面 `AImental_frontend/pages/paper-airplane/index.*`，让纸飞机可以作为真正的 tabBar 页面打开。
- 移除 `AImental_frontend/pages/daily-checkin/index.wxml` 中原有的纸飞机卡片入口，让纸飞机作为独立底栏模块呈现。
- 从现有纸飞机视觉风格出发，生成了一对 200x200 的 tabBar 图标：
  - `AImental_frontend/images/tabbar/paper_airplane_default.png`
  - `AImental_frontend/images/tabbar/paper_airplane_selected.png`
- 清理 `AImental_frontend/pages/daily-checkin/index.js` 中不再使用的纸飞机跳转函数。

## 验证

- `node -e "JSON.parse(...)"` 校验 `app.json` 和新页 `index.json` 通过。
- `node --check AImental_frontend/pages/paper-airplane/index.js` 通过。
- `node --check AImental_frontend/pages/daily-checkin/index.js` 通过。
- 已人工查看生成的纸飞机图标，风格与现有 tabBar 图标基本一致。

## 备注

- “心灵社区”页面仍保留在主包 pages 注册中，但已从底栏移除，不再作为可见入口。
- 后续如果要继续大改首页和信息架构，可以在这版底栏基础上继续推进。
