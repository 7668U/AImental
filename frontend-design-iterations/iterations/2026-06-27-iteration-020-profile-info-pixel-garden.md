# Iteration 020 - Profile Info Pixel Garden UI

日期：2026-06-27

## 背景

用户希望修改“我的”板块中“我的信息”界面 UI，并提供了参考图和素材目录 `UI素材/`，要求素材使用时扣掉背景。

## 本轮实施

- 阅读 `frontend-design-iterations/frontend-ui-designer-role-card.md`，按前端 UI 设计师职责承接本次页面改造。
- 将 `UI素材/ChatGPT Image 2026年6月27日 19_01_04.png` 复制并压缩为页面背景：`AImental_frontend/images/profile/profile-info-bg.png`。
- 将三枚像素信息项素材裁切并去除外部棋盘格背景，导出为透明 PNG：
  - `AImental_frontend/images/profile/profile-info-cat.png`
  - `AImental_frontend/images/profile/profile-info-heart.png`
  - `AImental_frontend/images/profile/profile-info-cake.png`
- 重构 `AImental_frontend/pkgProfile/inform.wxml`，加入整页背景、头像区、信息项图标和右侧箭头。
- 重写 `AImental_frontend/pkgProfile/inform.wxss`，落地参考图中的暖色导航、圆形头像、白色圆角信息卡、像素图标和文本溢出保护。
- 微调 `AImental_frontend/pkgProfile/inform.js` 的缓存读取，避免本地没有 `userInfo` 时访问头像字段报错。
- 排查页面一直显示“加载中...”的问题：本机 8000 后端服务请求超时，导致 `fetchUserInfo()` 的全屏 loading 无法结束。
- 为 `fetchUserInfo()` 和 `updateUserInfo()` 增加 8 秒请求超时；请求失败时关闭 loading 并提示检查后端服务。
- 修复 `start-backend.ps1` 的 Windows 编码启动问题，设置 `PYTHONUTF8=1` 与 `PYTHONIOENCODING=utf-8`，避免后端启动时 emoji 日志触发 `UnicodeEncodeError`。

## 验证

- `node --check AImental_frontend/pkgProfile/inform.js` 通过。
- 已确认 WXML/WXSS 引用的 `/images/profile/profile-info-*.png` 路径存在。
- 已确认三枚图标 PNG 具备透明信息，四角透明。
- `curl -I http://127.0.0.1:8000/docs` 返回 `200 OK`。
- `curl http://127.0.0.1:8000/api/v1/users/me/info` 未带 token 时快速返回 `401`，确认后端不再挂起请求。
