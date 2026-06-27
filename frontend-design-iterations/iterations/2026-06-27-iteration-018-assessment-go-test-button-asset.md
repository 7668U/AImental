# 2026-06-27 Iteration 018 - Assessment Go Test Button Asset

## 背景

用户希望将测评入口中用于进入下一个量表/进入量表详情的箭头，统一替换为提供的高清“去测试”按钮素材。

## 素材处理

- 用户提供的第一张图是截图式白底素材，直接进入小程序会带白色底边和截图留白。
- 尝试抠图后仍存在边缘底色残留，因此改为按参考图重绘透明 PNG。
- 正式前端资源：`AImental_frontend/images/assessment/common/go-test-button.png`
- 原始素材归档：`frontend-design-iterations/assets/assessment-go-test-button/go-test-source.png`
- 重绘后素材归档：`frontend-design-iterations/assets/assessment-go-test-button/go-test-button.png`

## 前端调整

修改 `AImental_frontend/pages/assessment/index.wxml`：

- 将首页四个分类卡右侧的圆形文字箭头替换为 `<image class="group-action">`。

修改 `AImental_frontend/pages/assessment/index.wxss`：

- 删除旧的 `group-arrow`、`arrow-symbol` 和分组颜色箭头样式。
- 增加 `group-action` 图片按钮尺寸。

修改 `AImental_frontend/pkgAssessment/category/category.wxml`：

- 将普通量表卡右侧圆形箭头和趣味探索卡右侧 CSS “去测试”按钮统一替换为 `<image class="test-action">`。

修改 `AImental_frontend/pkgAssessment/category/category.wxss`：

- 删除旧的 `arrow-button`、`arrow-symbol`、`test-button`、`test-button-arrow` 样式。
- 增加 `test-action` 图片按钮尺寸。

## 验证

- 已检查入口相关文件不再残留旧的 `group-arrow`、`arrow-button`、`arrow-symbol`、`test-button` 样式。
- 已确认正式资源存在：`AImental_frontend/images/assessment/common/go-test-button.png`。

## 注意

- 答题页底部“下一题”按钮的箭头属于问卷内部翻页，不是进入量表入口，本轮未替换为“去测试”按钮。
