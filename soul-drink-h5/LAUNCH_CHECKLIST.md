# Drink-TI H5 上线清单

## 上线文件

- `index.html`
- `styles.css`
- `app.js`

## CDN 素材

- 统一前缀：`https://assets.feelyourself.cn/miniprogram/assets/v1/pkgAssessment/images/drink-ti/`
- 结果卡：`result-cards/*.jpg`
- 封面与答题素材：`cover/*.png`、`sparkle.png`、`runner.png`、`feel-yourself-qr.png`

## 部署前检查

- 页面入口可通过 HTTPS 访问。
- CDN 为 `.png` 返回正确图片类型，为 `.svg` 返回 `image/svg+xml`。
- CDN 允许前端跨域读取图片，H5 生成海报需要 `Access-Control-Allow-Origin: *`。
- 后端开放 `/api/v1/promotion/soul-drink/session`、`/progress`、`/complete`、`/restart`。
- 建议图片、CSS、JS 设置长期缓存，HTML 使用较短缓存。

## 验收路径

1. 打开首页，确认封面图、开始按钮、闪光图加载正常。
2. 点击开始测试，确认第 1 题显示，未选择时下一题不可点击。
3. 完成 15 题，确认进入结果页，结果卡 SVG 加载正常。
4. 点击生成海报，确认弹窗内图片带小程序二维码，且可长按保存。
5. 点击重新测试，确认弹窗提示本次结果会被覆盖。
6. 在微信内置浏览器或目标投放渠道打开一次，确认页面高度、点击区和分享标题正常。
