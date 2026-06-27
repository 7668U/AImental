# 2026-06-27 Iteration 020 - Assessment Intro Title Sync

## 背景

用户反馈心理测试四个分类中的量表列表名称，与点击进入后的量表封面名称不一致，希望统一为列表中的名称。

## 问题定位

- 分类列表页使用 `displayTitle` 作为量表卡片名称。
- 封面页虽然也接入了公共展示名工具，但仍可能回退到接口原名，导致列表页和封面页存在两套标题来源。
- 这会造成用户在列表里看到一个名字，点进去封面又变成另一个名字。

## 前端调整

修改 `AImental_frontend/pkgAssessment/category/category.wxml`：

- 在量表卡片节点上增加 `data-title="{{item.displayTitle}}"`。

修改 `AImental_frontend/pkgAssessment/category/category.js`：

- 分类页统一通过 `getScaleDisplayMeta` 和 `getScaleDisplayName` 生成 `displayTitle`。
- 点击量表时，将当前列表卡片显示的 `displayTitle` 通过路由参数传给封面页。

修改 `AImental_frontend/pkgAssessment/intro/intro.js`：

- 增加 `passedDisplayTitle` 状态。
- 封面页加载时优先读取路由传入的列表标题，其次再回退到 `getScaleDisplayName()`。
- 保留图标和简介文案现有逻辑不变。

修改 `AImental_frontend/pkgAssessment/intro/intro.wxml`：

- 标题改为优先显示 `scale.displayName`，确保渲染的就是统一后的展示名。

## 验证

- `E:\node\node.exe --check AImental_frontend\pkgAssessment\intro\intro.js`：通过。
- 已检查分类页跳转参数包含 `title`，封面页存在 `passedDisplayTitle` 和 `scale.displayName` 渲染逻辑。

## 注意

- 本轮只统一用户可见标题，不改量表简介、图标和问卷内容。
- 后续如果继续改量表中文名，优先改公共展示名工具，列表和封面会一起同步。
