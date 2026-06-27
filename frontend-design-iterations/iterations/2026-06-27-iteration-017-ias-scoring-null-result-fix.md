# 2026-06-27 Iteration 017 - IAS Scoring And Null Result Fix

## 背景

用户反馈“互动焦虑量表”完成后，历史记录和结果页展示为“交往焦虑量表”，并且结果等级显示 `null`，分析区域没有可展示内容。

## 问题定位

- `AImental_backend/assessment_data/IAS.json` 中量表名称仍为“交往焦虑量表”，与前端分类页“互动焦虑量表”的展示口径不一致。
- 后端通用打分逻辑对反向计分题使用了 `1 - score`，只适合 0/1 选项。
- IAS 选项为 1-5 分，反向题应按 `min_score + max_score - score` 计算；旧逻辑会把反向题扣成负数，使总分低于 IAS 最小分 15，导致解释区间无法匹配，`result_level/result_interpretation/result_recommendation` 均为空。
- 前端历史记录和结果页直接渲染原始 `result_level`，所以异常旧记录会显示 `null`。

## 前后端调整

修改 `AImental_backend/model/assessment.py`：

- 通用打分逻辑按选项实际最小/最大分计算反向题。
- 兼容 `reverse_scoring_items`、`reverse_scored_items`、题目级 `is_reverse_scored/reverse_scored`。
- 返回历史列表和历史详情前，对受反向计分影响或缺失等级的打分记录进行自愈重算并保存，修复已产生的异常旧记录。

修改 `AImental_backend/assessment_data/IAS.json`：

- 将量表名称统一为“互动焦虑量表”。
- 描述文案同步改为“人际互动场合”口径。

修改 `AImental_frontend/pkgAssessment/intro/intro.js`：

- 为 IAS 增加前端展示名兜底，避免后端服务未重启时仍展示旧名。

修改 `AImental_frontend/pkgAssessment/result.js`：

- 对空结果等级统一展示为“结果待确认”，不再裸露 `null`。
- 结果指针限制在 0%-100% 范围内，避免异常旧分数把位置挤出量尺。
- 非结构化 AI 分析时继续展示“当前状态 / 可以先试试”等兜底结果分析内容。

修改 `AImental_frontend/pkgProfile/history.js` 和 `history.wxml`：

- 历史列表展示 IAS 名称为“互动焦虑量表”。
- 历史记录结果等级和得分使用展示字段，避免 `null` 直接出现在 UI 上。

## 验证

- 使用 Node 脚本验证 IAS 反向计分：
  - 全 1 分：31，匹配“正常范围的社交焦虑”。
  - 全 3 分：45，匹配“正常范围的社交焦虑”。
  - 全 5 分：59，匹配“较为明显的社交焦虑”。
- `node --check AImental_frontend/pkgAssessment/result.js`：通过。
- `node --check AImental_frontend/pkgProfile/history.js`：通过。
- `node --check AImental_frontend/pkgAssessment/intro/intro.js`：通过。
- 本机 `python` 是 Windows Store 占位启动器，无法执行 `py_compile`；后端逻辑已通过静态检查和等价计分脚本验证。

## 注意

- 这次修复后，新提交的 IAS 结果会正常匹配等级和结果分析。
- 已生成的异常 IAS 历史记录，会在再次请求历史列表或历史详情时由后端自动重算修复。
