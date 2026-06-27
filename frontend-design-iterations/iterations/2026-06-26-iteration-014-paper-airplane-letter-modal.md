# Iteration 014 - Paper Airplane Letter Modal

日期：2026-06-26

## 背景

用户反馈纸飞机页面打开纸飞机后的展示框仍然很简陋，希望改成类似参考图的“展开一张信纸”模式：中间展示手写感内容，去掉“今日小纸条”“来自远方的纸飞机”等说明小字，底部按钮也按参考图的胶囊按钮气质重做。

## 素材方案

- 理想素材：一张无文字的竖版信纸背景图，只包含纸张质感、中心留白、轻量纸飞机装饰和飞行虚线。
- 不把动态正文、标题或按钮文字画进背景图，避免不同纸飞机内容无法复用。
- 已尝试使用 fhl Images API：
  - 参考图编辑：返回 `503 No available compatible accounts`。
  - 纯文本生成：返回 `503 No available compatible accounts`。
- 为不阻塞前端落地，先使用本地绘制方式生成可替换素材：
  - `AImental_frontend/images/paper-airplane/letter-paper-bg.png`
  - 尺寸：`900x1180`
  - 格式：`RGBA PNG`
- 后续 fhl 恢复后，可直接替换同名素材，无需改页面结构。

## 前端实施

- 改造 `AImental_frontend/pages/paper-airplane/index.wxml`：
  - 将旧 `modal-content read-modal` 替换为专用 `letter-modal`。
  - 使用 `letter-paper-bg.png` 作为信纸背景。
  - 正文改为覆盖在信纸中心的滚动区域。
  - 删除读取弹窗中的标题、副标题和说明文案，只保留纸飞机内容本身。
  - 底部按钮改为“收进纸篓”和“轻轻收起”。
- 用户随后提供精修信纸 UI 素材，已直接替换：
  - `AImental_frontend/images/paper-airplane/letter-paper-bg.png`
  - 新素材尺寸：`1101x1429`
- 按新素材重新对齐读取弹窗：
  - 右上角关闭按钮放到信纸右上角内侧，避免偏出卡片。
  - 正文区域对齐到中间白色便签范围。
  - 底部按钮对齐到底部浅橙胶囊槽内。
  - 按钮文案简化为“收下”和“放飞”。
- 新增 `releaseOpenedAirplane()`：
  - 右上角关闭和“放飞”走放飞逻辑，关闭弹窗后补一架新的可捡纸飞机。
  - “收下”继续走收藏接口。
- 用户继续提供去掉底部按钮槽的自然纸张素材，已再次替换：
  - `AImental_frontend/images/paper-airplane/letter-paper-bg.png`
  - 新素材尺寸：`1086x1448`
- 按用户反馈继续调整：
  - 删除信纸内右上角 `×`，不再显示关闭按钮。
  - “放飞”即关闭/释放当前纸飞机。
  - 两个按钮脱离素材底槽，作为前端叠加控件放在纸张底部偏上一点的位置。
  - 按钮保持“收下 / 放飞”两个短文案。
- 改造 `AImental_frontend/pages/paper-airplane/index.wxss`：
  - 新增信纸弹窗尺寸、展开动画和柔和遮罩。
  - 圆形关闭按钮曾用于第一版信纸弹窗，后按用户反馈移除。
  - 正文使用楷体/仿宋优先的字体栈，居中排版，模拟手写纸条感。
  - 底部按钮改为一浅一橙的圆角胶囊样式，接近参考图。
  - 移除旧读取弹窗的 `message-display` 和 `read-modal` 样式。

## 验证

- `node --check AImental_frontend/pages/paper-airplane/index.js`：通过。
- 已检查 `letter-paper-bg.png`，无固定文字、无水印，中心留白可承载动态文本。
- 替换用户精修素材后再次确认 `letter-paper-bg.png` 为 `1101x1429 RGB PNG`。
- 替换去底槽自然纸素材后再次确认 `letter-paper-bg.png` 为 `1086x1448 RGB PNG`。

## 未完成

- fhl 当前账户侧不可用，未能生成 AI 版本信纸素材；本地生成素材先作为可用版本落地。

## 2026-06-26 04:12 Follow-up

用户继续要求：

- 删除后端已查看过的纸飞机记录，让它们显示为未查看。
- 新增 100 条假数据，方便连续点击足够多的纸飞机。
- 将“扔一个”写信界面也改成同款信纸模式，中间纸张区域作为输入框，下方按钮为“扔出去”。
- 写信界面需要保留关闭按钮，用于撤回/不扔了。

本次实施：

- 直接操作本地后端数据库 `AImental_backend/db/paper_airplane.db`：
  - 清空 `user_picked_airplanes`，将已查看/已捡起状态重置为未查看。
  - 保留 `user_collected_airplanes`，不删除已收进飞机篓的记录。
  - 使用系统用户 `system_paper_airplane_user` 新增 100 条测试纸飞机。
- 改造 `AImental_frontend/pages/paper-airplane/index.wxml`：
  - 将旧写信白框替换为 `write-letter-modal` 信纸模式。
  - 中间白色便签区域改为 `textarea`。
  - 底部按钮改为单个“扔出去”。
  - 写信界面保留一个轻量关闭按钮。
- 改造 `AImental_frontend/pages/paper-airplane/index.wxss`：
  - 删除旧 `modal-content`、`write-modal`、`message-input`、`modal-button` 写信样式。
  - 新增 `letter-input`、`write-letter-close`、`write-letter-actions` 等样式。
  - 校准读信正文和写信输入框，使其贴合新素材中间白色便签范围。

验证：

- `node --check AImental_frontend/pages/paper-airplane/index.js`：通过。
- 数据库检查：
  - `paper_airplanes`: 115
  - `user_picked_airplanes`: 0
  - `user_collected_airplanes`: 1
  - `local-dev-user` 当前可见纸飞机：115

## 2026-06-26 04:15 Follow-up

用户继续反馈：

- 信纸素材周围仍有一块大的白底。
- 写信界面的关闭 `×` 很丑，希望模仿飞机篓的轻量关闭符号。

本次实施：

- 对 `AImental_frontend/images/paper-airplane/letter-paper-bg.png` 做本地透明化处理：
  - 去除外圈近白色矩形画布。
  - 保留信纸本体、装饰和阴影。
  - 输出为 `1086x1448 RGBA PNG`。
- 将写信界面关闭控件从 `button` 改为普通 `view`：
  - 删除白色圆底、默认按钮样式和阴影。
  - 使用与飞机篓关闭按钮一致的轻量橙色 `×` 风格。

验证：

- `node --check AImental_frontend/pages/paper-airplane/index.js`：通过。
- `letter-paper-bg.png` 四角 alpha 已为 0，中间纸张区域 alpha 为 255。

## 2026-06-26 04:21 Follow-up

用户继续反馈：

- 打开纸飞机后的正文会飘出便签外，没有被很好限制在中间白色便签内。
- 外围仍然像有白色光晕/白底。
- 用户提供新的无背景信纸素材。

本次实施：

- 基于用户新素材生成并接入新文件：
  - `AImental_frontend/images/paper-airplane/letter-paper-bg-clean.png`
  - 通过边缘连通区域抠图方式移除导出图中的白色/棋盘预览背景。
  - 保留信纸本体、花朵、纸飞机和阴影。
- 将写信和读信弹窗统一改为引用 `letter-paper-bg-clean.png`。
- 将读信正文节点从 `text` 改为块级 `view`，更稳定地支持宽度约束。
- 调整 `letter-message-scroll` 和 `letter-input`：
  - 收窄左右边距，使内容严格落在中间白色便签区域。
  - 增加 `overflow: hidden`、`word-break: break-all`、`overflow-wrap: break-word`。
  - 字号从 `36rpx` 调整为 `32rpx`，降低长句溢出概率。
- 新增 `formatLetterMessage()`：
  - 打开纸飞机和打开飞机篓纸飞机时，会按约 13 个字一行自动插入换行。
  - 优先在中文/英文标点处断行，避免一整句冲出便签。

验证：

- `node --check AImental_frontend/pages/paper-airplane/index.js`：通过。
- `letter-paper-bg-clean.png` 为 `1086x1448 RGBA PNG`，四角 alpha 为 0，中间纸张区域 alpha 为 255。

## 2026-06-26 04:26 Follow-up

用户继续反馈：

- 写纸飞机界面基本可以，但看纸飞机界面的正文仍然是歪的。
- 读信内容应和写信一样显示在对应便签位置。
- 长内容超出时不要飘出便签，应在固定隐形文字框内向下滑动查看。
- 写纸飞机按钮需要再往上调一点。

本次实施：

- 取消 `formatLetterMessage()` 的手动断行逻辑，读信内容不再预先插入换行，避免人为造成排版偏右/偏斜。
- 将 `letter-message-scroll` 的坐标、宽度、高度和内边距调整为与 `letter-input` 完全一致：
  - 形成一个固定在白色便签上的隐形滚动文字框。
  - 长内容通过 `scroll-view scroll-y` 在便签内下滑查看。
- 将读信正文改为左对齐自然换行，使用 `white-space: pre-wrap`、`word-break: break-word` 和 `overflow-wrap: break-word` 控制溢出。
- 写信按钮 `.write-letter-actions` 上移：`bottom` 从 `46rpx` 调整到 `62rpx`。

验证：

- `node --check AImental_frontend/pages/paper-airplane/index.js`：通过。
