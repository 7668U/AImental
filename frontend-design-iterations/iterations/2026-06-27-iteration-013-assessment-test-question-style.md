# 2026-06-27 Iteration 013 - Assessment Test Question Style

## 背景

用户提供心理测评答题页参考图，希望把每个题目的背景样式改成参考图中的暖色卡片式界面，并提供跑步小人进度素材。

## 素材

- 参考图归档：`frontend-design-iterations/assets/assessment-test-question-style/question-style-reference.png`
- 用户原始跑步小人：`frontend-design-iterations/assets/assessment-test-question-style/runner-source.png`
- 用户原始星星：`frontend-design-iterations/assets/assessment-test-question-style/sparkle-source.png`
- 选项展示问题参考图：`frontend-design-iterations/assets/assessment-test-question-style/score-option-bug-reference.png`
- 前端使用跑步小人：`AImental_frontend/images/assessment/test/runner.png`
- 前端使用星星：`AImental_frontend/images/assessment/test/sparkle.png`

处理说明：

- 跑步小人原图带烘焙棋盘格背景，已通过本地图像处理生成透明 PNG。
- 星星原图带烘焙棋盘格背景，已通过本地图像处理生成透明 PNG。
- 本轮不调用 imagegen，不新增外部素材。

## 前端调整

修改 `AImental_frontend/pkgAssessment/test.json`：

- 将答题页切换为 `navigationStyle: custom`。

修改 `AImental_frontend/pkgAssessment/test.js`：

- 新增导航高度计算。
- 新增自定义返回按钮事件。
- 对 `0分选项 / 1分选项 / 2分选项 / 3分选项` 这类内部计分占位做展示修正：从题干 `/` 分隔文本中拆出真实选项展示，提交值仍保留原 score。
- 保留原有题目加载、答题、进度和提交接口逻辑。
- 底部右侧按钮在最后一题时复用原有提交逻辑。

修改 `AImental_frontend/pkgAssessment/test.wxml`：

- 新增自定义导航栏。
- 将题目区改为独立暖白大卡。
- 将选项区改为圆角白卡选项列表。
- 将底部改为固定进度卡，包含跑步小人、进度文字、上一题和下一题/查看结果按钮。
- 将装饰叉/十字替换为用户提供的星星 PNG。

修改 `AImental_frontend/pkgAssessment/test.wxss`：

- 使用暖白/浅橙背景、柔和径向光斑、星星装饰和圆角卡片。
- 优化长题目、长选项换行，避免文字溢出。
- 保持底部操作区固定且预留安全区。

## 验证

- `E:\node\node.exe --check AImental_frontend\pkgAssessment\test.js`：通过。
- 本地模拟 SDS/BDI-II 第一题拆分后，页面展示选项为真实陈述，不再展示 `0分选项` 等内部占位。

## 注意

- 本轮未改后端接口。
- 未在微信开发者工具中做真机/模拟器截图验收，后续可根据截图继续微调字号、卡片高度和底部间距。
