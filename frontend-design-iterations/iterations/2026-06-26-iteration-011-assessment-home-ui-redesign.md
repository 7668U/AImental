# Iteration 011 - Assessment Home UI Redesign

日期：2026-06-26

## 背景

用户提供心理测评首页参考图和两张已准备好的透明背景插画素材，要求按参考重新设计心理测评 UI 界面。

本轮聚焦 `AImental_frontend/pages/assessment/index.*` 首页，不改测评详情、答题和结果页逻辑。

## 设计目标

- 让心理测评首页从旧的“分组 tab + 测评宫格”升级为更温暖的分类入口页。
- 保留四个产品分组：心理健康、自我人格、关系亲密、趣味探索。
- 使用用户提供的素材形成首屏视觉记忆点和底部温柔提示条。
- 保留具体测评入口能力：点击分类后展开对应测评列表，仍进入原有 intro 页面。

## 素材处理

新增前端素材目录：

- `AImental_frontend/images/assessment/home/`

新增素材：

- `hero-journey.png`：来自用户提供的顶部植物、咖啡、窗景透明插画。
- `gentle-dialogue-banner.png`：来自用户提供的底部横幅，并裁掉外圈透明留白。
- `group-health.png`：从参考图裁切的心理健康分类图标。
- `group-personality.png`：从参考图裁切的自我人格分类图标。
- `group-relationship.png`：从参考图裁切的关系亲密分类图标。
- `group-interest.png`：从参考图裁切的趣味探索分类图标。

同步归档到：

- `frontend-design-iterations/assets/assessment-home/`

## 前端实现

修改 `AImental_frontend/pages/assessment/index.wxml`：

- 重构首页结构为顶部 hero、四张分组卡、展开测评列表、底部 banner。
- 分类卡展示图标、标题、描述、量表缩写摘要和数量。
- 具体测评列表在点击分类卡后展开，保留单项测评入口。

修改 `AImental_frontend/pages/assessment/index.js`：

- 为四个分组补充主题、描述、摘要、图标和计数。
- 根据接口返回或本地分组映射计算每组测评数量。
- 新增 `isScaleListOpen` 控制具体测评列表展开/收起。
- 保留原有 `goToTest` 跳转逻辑。

修改 `AImental_frontend/pages/assessment/index.wxss`：

- 使用温暖浅橙背景、柔和白色卡片和低强度阴影贴近参考稿。
- 分类卡按健康、人格、关系、兴趣区分箭头色彩。
- 具体测评列表采用轻量条目式展示，减少首页拥挤感。
- 使用页面专属 `.assessment-page`，避免受全局 `.container` 样式影响。

## 验证

- 已确认新增素材位于小程序可访问路径 `/images/assessment/home/`。
- 已静态检查 WXML/JS/WXSS，分类点击仍复用原有分组过滤与测评跳转。
- 本轮未运行微信开发者工具预览；需在开发者工具中查看真机尺寸下的视觉效果。

