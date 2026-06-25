# Team Chat Usage Guide

这个文件是产品经理、前端设计师、后端工程师三个 Agent 的内部群聊操作协议。

这个群聊不是用户会进入的聊天空间，而是给几个 Agent 自己交互、沟通、提问、回复、接任务和沉淀共识用的工作空间。

用户通过主对话、需求文档或项目文件提出目标和反馈；Agent 不要在群聊里等待用户回复。群聊里应该主动找其他 Agent 对齐，而不是把问题丢给用户。

群聊不是替代各自的迭代目录，而是用来处理 Agent 之间的跨角色协作：谁需要谁确认、谁被什么阻塞、什么结论已经对齐、下一步由谁接。

## 使用主体

- 使用者：产品经理 Agent、前端设计师 Agent、后端工程师 Agent。
- 不使用者：项目用户/项目负责人不会进入这个群聊参与讨论。
- 用户输入来源：主对话、需求文档、项目代码和迭代记录。
- 群聊目标：让 Agent 之间主动同步，形成可追踪协作闭环。

## 先读顺序

每个 Agent 开始一轮工作前，先快速读取：

1. `team-chat-database/data/roles.json`
2. `team-chat-database/views/thread-view.md`
3. 自己的角色卡和工作目录

如果 `thread-view.md` 不是最新的，先运行：

```powershell
.\team-chat-database\tools\Render-ChatThread.ps1
```

## 必须使用群聊的场景

遇到以下情况时，不要只写在自己的迭代目录里，需要发群聊消息给其他 Agent：

- 需求、页面、接口、数据模型或验收标准需要另一个 Agent 确认。
- 你的方案会影响另一个 Agent 的工作范围。
- 发现阻塞、风险、依赖缺口或前后端不一致。
- 做出跨角色共识，例如入口下架、字段新增、接口结构定稿。
- 一个 Agent 完成阶段性工作，需要把下一步交给另一个 Agent。

## 不必使用群聊的场景

以下内容优先写回自己的工作目录：

- 单角色内部思考。
- 不影响其他角色的小实现细节。
- 尚未形成问题、结论或依赖的临时草稿。
- 纯代码验证记录，除非验证结果影响产品或前端联调。

## 消息类型怎么选

| message_type | 什么时候用 |
| --- | --- |
| `question` | 需要别人回答或确认 |
| `answer` | 回复别人的问题 |
| `decision` | 已形成跨角色结论或阶段性定案 |
| `task` | 明确分配一个后续动作 |
| `handoff` | 一个 Agent 把工作交给另一个 Agent |
| `review` | 对方案、页面或接口做审查反馈 |
| `note` | 低风险同步，不需要立即响应 |
| `message` | 普通沟通 |

## 状态怎么选

| status | 含义 |
| --- | --- |
| `open` | 刚提出，等待处理 |
| `in_progress` | 正在处理 |
| `blocked` | 被某个问题卡住 |
| `resolved` | 已解决或已对齐 |
| `archived` | 已归档，不再推进 |

## 发消息命令

普通问题：

```powershell
.\team-chat-database\tools\Add-ChatMessage.ps1 `
  -AuthorRole product_manager `
  -Topic "emotion-record" `
  -MessageType question `
  -Status open `
  -Tags "emotion-record","api" `
  -Mentions "frontend_designer","backend_engineer" `
  -RelatedFiles "product-design-iterations/backlog.md" `
  -Body "情绪记录页准备新增能量、压力、身体反馈三个字段。请前端确认页面承载方式，后端确认是否复用 checkins 表。"
```

回复某条消息：

```powershell
.\team-chat-database\tools\Add-ChatMessage.ps1 `
  -AuthorRole backend_engineer `
  -ReplyToId msg-20260625-0001 `
  -Topic "emotion-record" `
  -MessageType answer `
  -Status open `
  -Mentions "product_manager","frontend_designer" `
  -RelatedFiles "AImental_backend/model/status.py","AImental_backend/router/status.py" `
  -Body "后端建议先扩展 checkins 表，新增可选字段，保证旧记录仍可读取。"
```

记录决策：

```powershell
.\team-chat-database\tools\Add-ChatMessage.ps1 `
  -AuthorRole product_manager `
  -Topic "emotion-record" `
  -MessageType decision `
  -Status resolved `
  -Mentions "frontend_designer","backend_engineer" `
  -DecisionSummary "情绪记录第一版新增能量、压力、身体反馈三个可选字段，后端保持旧数据兼容。" `
  -Body "本轮先做最小可用扩展，不一次性加入全部深度维度。"
```

交接任务：

```powershell
.\team-chat-database\tools\Add-ChatMessage.ps1 `
  -AuthorRole frontend_designer `
  -Topic "emotion-record" `
  -MessageType handoff `
  -Status open `
  -Mentions "backend_engineer" `
  -TaskTitle "提供情绪记录扩展字段的创建、更新、查询接口" `
  -TaskOwnerRole backend_engineer `
  -Body "前端线框已确认，需要后端先给出字段名和响应结构。"
```

发完消息后，重新生成可读视图：

```powershell
.\team-chat-database\tools\Render-ChatThread.ps1
```

## 回复闭环

一条跨角色沟通最好形成闭环：

1. `question`：提出问题，并明确要哪个 Agent 回答。
2. `answer`：被点名 Agent 回复判断、限制或方案。
3. `decision`：产品经理或发起者总结最终结论。
4. `handoff` 或 `task`：如果还有下一步，明确 owner。

如果只是把问题丢进群聊，但没有 `decision`、`handoff` 或 `resolved` 状态，这条沟通就还没结束。

## 正文建议格式

复杂消息建议按这个结构写在 `Body` 里：

```text
背景：为什么现在要说这件事。
问题：需要谁确认什么。
建议：我当前倾向怎么做。
影响：会影响哪些页面、接口、数据或验收。
需要回复：请谁在什么范围内给判断。
```

## 各 Agent 默认职责

- 产品经理 Agent：发起需求对齐、总结决策、补验收标准。
- 前端设计师 Agent：确认页面承载、交互状态、素材需求和联调问题。
- 后端工程师 Agent：确认接口字段、数据模型、迁移风险、错误码和验证方式。

## 重要原则

- 群聊里只沉淀会影响协作的内容。
- 群聊只给 Agent 使用，不面向用户，不等待用户进入或回复。
- 重要结论要能被后来的人一眼看懂。
- 涉及具体文件时一定写 `related_files`。
- 提到需要别人处理时一定写 `mentions`。
- 决策进入开发前，应同时沉淀到对应角色的 `decision-log.md` 或迭代记录。
