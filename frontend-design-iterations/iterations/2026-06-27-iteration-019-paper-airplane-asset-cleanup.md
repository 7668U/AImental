# Iteration 019 - Paper Airplane Asset Cleanup

## 背景

用户反馈纸飞机模块里：
- “扔一个”按钮图和飞行纸飞机素材有残留虚线边。
- 信纸页面右上角关闭按钮上方有一个像加号的装饰，观感不好，希望去掉。

本次按前端 UI 设计师角色卡处理，优先复用现有素材，不重新生成风格可能漂移的新图。

## 素材处理

- 清理 `AImental_frontend/images/paper-airplane/throw-button.png`：
  - 去掉按钮底部和右侧的中性灰预览/裁切残留。
  - 保持原画布尺寸 `1625x619`，避免影响现有页面定位。
- 清理 `AImental_frontend/images/paper-airplane/flying/*.png`：
  - 对 24 张飞行纸飞机素材做 alpha 连通域清理。
  - 保留纸飞机主体，删除不相连的虚线裁切参考线和少量孤立像素。
  - 重点清理紫色、黄色几组素材周围的虚线残留。
- 清理 `AImental_frontend/images/paper-airplane/letter-paper-bg-clean.png`：
  - 确认右上角“加号”不是 WXML/CSS 额外叠加，而是信纸背景 PNG 内的装饰像素。
  - 只移除该局部橙色加号/星形装饰，并用周围纸张纹理做局部补全。
  - 保持原画布尺寸 `1086x1448` 和透明边界。

## 页面代码

- 未改动 `AImental_frontend/pages/paper-airplane/index.wxml`。
- 未改动 `AImental_frontend/pages/paper-airplane/index.wxss`。
- 现有写信弹窗仍引用 `letter-paper-bg-clean.png`，关闭控件仍由前端节点 `write-letter-close` 控制。

## 验证

- 对按钮图和 24 张飞行纸飞机 PNG 做 alpha 连通域检查：无独立虚线/孤立残留组件。
- 对信纸右上角目标区域做橙色像素检查：加号装饰已清除。
- 生成本地 contact sheet 做肉眼复核：`output/asset-inspection/paper-airplane-after-final/contact-sheet-final.png`。
- `node --check AImental_frontend/pages/paper-airplane/index.js`：通过。

## Follow-up - Button State Clarity

用户反馈“扔出去 / 收下 / 放飞”等信纸弹窗按钮透明度过高，容易让人误以为按钮不可点击。

本次调整：
- 将 `AImental_frontend/pages/paper-airplane/index.wxss` 中 `.letter-action` 的 `opacity` 从 `0.5` 调整为 `0.9`。
- 保留柔和质感，但让主按钮和次按钮都更接近可点击状态。

## Follow-up - Basket Hit Area

用户反馈飞机篓入口体积太大，点击周围纸飞机时容易误触飞机篓。

本次调整：
- 将 `.basket-entry` 从 `390rpx x 390rpx` 缩小为 `300rpx x 300rpx`。
- 将入口位置从 `top: 1080rpx` 微调到 `top: 1110rpx`，减少与底部纸飞机热区重叠。
