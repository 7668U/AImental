# Iteration 013 - Paper Airplane Redesign and Basket

日期：2026-06-26

## 背景

用户希望将纸飞机页面重做为参考图样式：左上展示“放飞烦恼”标题和说明，左下使用生成好的“扔一个”按钮素材，右下展示可点击的飞机篓。用户要求新增“收飞机”逻辑：读到纸飞机后可以收进飞机篓，并能从飞机篓查看曾经收起的飞机。天空中飞的纸飞机素材暂时未定，先留空缺。

## 前端实施

- 替换纸飞机页标题素材：
  - `AImental_frontend/images/paper-airplane/title-fly-worries.png`
  - 使用用户提供的新透明素材，并裁掉右侧半截星星。
- 替换飞机篓素材：
  - `AImental_frontend/images/paper-airplane/basket.png`
  - 使用用户提供的新透明素材。
- 新增按钮素材：
  - `AImental_frontend/images/paper-airplane/throw-button.png`
  - 从用户提供素材中抠除预览底并裁边。
- 新增提示小字素材：
  - `AImental_frontend/images/paper-airplane/guide-text.png`
  - 替换原先的普通文本提示，保持左对齐。
- 新增飞行纸飞机素材：
  - `AImental_frontend/images/paper-airplane/flying/*.png`
  - 从 `C:\Users\29537\Downloads\paper_planes_24_png.zip` 解压得到 24 个 PNG。
- 重做 `AImental_frontend/pages/paper-airplane/index.wxml`：
  - 顶部使用“放飞烦恼”标题图。
  - 删除两行普通说明文字，中部提示改为图片素材。
  - 天空纸飞机从透明点击热区改为随机使用 24 个纸飞机 PNG。
  - 左下按钮改为整张按钮素材。
  - 右下新增可点击飞机篓入口。
  - 阅读弹窗新增“收进飞机篓”操作。
  - 新增飞机篓弹窗，展示已收起纸飞机列表。
- 重做 `AImental_frontend/pages/paper-airplane/index.wxss`，使布局接近参考图，并保证按钮、飞机篓、标题图按素材展示。
- 根据用户反馈微调布局：
  - 提示小字上移，贴近“放飞烦恼”标题图。
  - 飞机篓缩小并向右移动一点。
  - 左下按钮向左移动一点，拉开与飞机篓的距离。
- 更新 `AImental_frontend/pages/paper-airplane/index.js`：
  - 新增 `showBasketModal`、`openedAirplaneId`、`collectedAirplanes` 等状态。
  - 新增 24 个飞行纸飞机素材路径。
  - 新增固定安全点位，随机选用纸飞机素材并避开标题、提示、按钮和飞机篓。
  - 新增 `collectOpenedAirplane()`，调用 `POST /api/v1/airplane/{airplane_id}/collect`。
  - 新增 `openBasket()`，调用 `GET /api/v1/airplane/collected`。

## 后端实施

- 更新 `AImental_backend/model/airplane.py`：
  - 新增 `UserCollectedAirplane` 表模型，对应 `user_collected_airplanes`。
  - 新增 `collect_airplane()`：仅允许当前用户把已捡起且非自己发布的纸飞机收进飞机篓。
  - 新增 `get_collected_airplanes()`：按收起时间倒序返回当前用户飞机篓列表。
- 更新 `AImental_backend/router/airplane.py`：
  - 新增 `POST /api/v1/airplane/{airplane_id}/collect`。
  - 新增 `GET /api/v1/airplane/collected`。

## 团队协作

- 已在群聊发起后端需求同步：`msg-20260626-0001`。
- 已在群聊补充最小后端实现与验证结果：`msg-20260626-0002`。

## 验证

- `node --check AImental_frontend/pages/paper-airplane/index.js`：通过。
- `AImental_backend/.venv/Scripts/python.exe -m py_compile AImental_backend/model/airplane.py AImental_backend/router/airplane.py`：通过。
- 已确认飞行纸飞机素材数量为 24 个，均为 RGBA PNG。
- 已确认提示小字、标题、飞机篓和按钮素材均已落到 `AImental_frontend/images/paper-airplane/`。
- 使用后端虚拟环境完成模型级 smoke test：
  - 未捡起纸飞机时不能收进飞机篓。
  - 捡起后可以收进飞机篓。
  - 飞机篓列表可以查到已收纸飞机。

## 2026-06-26 Follow-up Layout Adjustment

- Moved the throw button upward into the sky area and kept it separated from the basket.
- Reworked flying airplane markup into a fixed hit area plus an animated inner image.
- Replaced margin-based airplane motion with slow `translate3d` drift and light rotation to avoid jitter.
- Changed airplane safe slots from height percentages to fixed rpx coordinates so they do not drift into existing UI on different screen heights.
- Checked the six airplane motion boxes against title, guide text, throw button, and basket areas at 1334rpx and 1624rpx estimated viewport heights; no overlaps found.

## 未完成

- 背景图保持用户提供的原始浅色天台图，不再做去网格加工。
