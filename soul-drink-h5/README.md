# Drink-TI H5

这是独立静态 H5 测试页，可直接部署 `soul-drink-h5/` 目录，也可以使用整理后的上线包 `dist/soul-drink-h5-release.zip`。

- 入口文件：`index.html`
- 样式文件：`styles.css`
- 题目、计分与结果逻辑：`app.js`
- 首屏、答题、二维码和结果卡素材默认走统一 CDN：
  `https://assets.feelyourself.cn/miniprogram/assets/v1/pkgAssessment/images/drink-ti/`
- 结果卡图片：`result-cards/*.jpg`
- 匿名档案 API：默认请求同域 `/api/v1/promotion/soul-drink`

本地预览可直接打开 `index.html`；上线前建议用 HTTP 服务预览一次，避免服务器路径或静态资源配置问题：

```bash
python -m http.server 5173 --bind 127.0.0.1 --directory soul-drink-h5
```

本地跨端口调试后端时，可在 URL 里指定 API 地址：

```text
http://127.0.0.1:5173/?apiBase=http%3A%2F%2F127.0.0.1%3A8000%2Fapi%2Fv1%2Fpromotion%2Fsoul-drink
```

如果需要临时切换到其他静态资源域名，可在页面加载前注入：

```html
<script>
  window.SOUL_DRINK_ASSET_BASE = "https://your-cdn.example.com/drink-ti/";
</script>
```

如果部署到服务器，保持引用到的文件结构不变即可。未被页面引用的源图素材可以不放入首版上线包。
