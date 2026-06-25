# Team Chat Database

这个文件夹是产品经理 Agent、前端设计师 Agent、后端工程师 Agent 三者之间使用的轻量群聊数据库。它不是给项目用户进入聊天的地方，而是几个 Agent 内部交互、同步、接力和沉淀决策的工作空间。

核心原则是：

- 一行就是一条聊天记录，方便直接追加、检索和做 Git diff。
- `reply_to_id` 指向被回复的消息，天然形成讨论线程。
- JSONL 作为日常数据源，旁边保留 JSON Schema 和 SQLite schema，后续要升级成真正数据库也不需要推倒重来。

## 文件结构

- `data/messages.jsonl`：主聊天数据，一行一条消息。
- `data/roles.json`：三位角色的固定 ID、中文名和职责边界。
- `views/thread-view.md`：当前聊天内容的可读视图。
- `templates/message.template.json`：新增普通消息模板。
- `templates/reply.template.json`：回复某条消息的模板。
- `USAGE.md`：三位 Agent 的群聊使用协议，说明谁来用、什么时候用、怎么发、怎么回复和怎么形成闭环。
- `schema/message.schema.json`：单条消息的 JSON Schema。
- `schema/chat.sqlite.sql`：未来迁移到 SQLite 时可直接使用的表结构。
- `tools/Add-ChatMessage.ps1`：用命令快速追加消息。
- `tools/Render-ChatThread.ps1`：把 JSONL 渲染成 Markdown 聊天视图。

## 使用协议

三位 Agent 开始使用群聊前，先读 `USAGE.md`。

简要原则：

- 群聊只给 Agent 之间使用，用户不会进入这里聊天。
- Agent 不要在群聊里等待用户回复；需要用户确认的问题应回到主对话。
- 需要跨角色确认的问题才进群聊。
- 发消息时写清 `message_type`、`mentions`、`related_files`。
- 回复别人时必须填写 `reply_to_id`。
- 重要共识用 `message_type: "decision"`。
- 阶段性交接用 `message_type: "handoff"` 或 `task`。
- 发完消息后运行 `tools/Render-ChatThread.ps1` 更新可读视图。

## 角色 ID

| Agent | author_role | author_name |
| --- | --- | --- |
| 产品经理 Agent | `product_manager` | `产品经理` |
| 前端设计师 Agent | `frontend_designer` | `前端设计师` |
| 后端工程师 Agent | `backend_engineer` | `后端工程师` |

## 最快添加一条消息

```powershell
.\team-chat-database\tools\Add-ChatMessage.ps1 `
  -AuthorRole product_manager `
  -Topic "daily-sync" `
  -MessageType question `
  -Body "今天先确认首页情绪记录流程，前后端各自看一下影响范围。"
```

回复某条消息：

```powershell
.\team-chat-database\tools\Add-ChatMessage.ps1 `
  -AuthorRole backend_engineer `
  -ReplyToId msg-20260622-0002 `
  -Topic "daily-sync" `
  -MessageType answer `
  -Body "后端需要确认是否复用 daily_status.db，以及是否新增情绪维度字段。"
```

重新生成可读聊天视图：

```powershell
.\team-chat-database\tools\Render-ChatThread.ps1
```

## 手工追加规则

如果不用脚本，也可以直接在 `data/messages.jsonl` 末尾追加一行 JSON。

- `id` 使用 `msg-YYYYMMDD-0001` 这种格式，并保持唯一。
- `reply_to_id` 填被回复消息的 `id`；如果不是回复任何消息，就填 `null`。
- `body` 不要拆成多行；如果需要换行，用 `\n` 写在字符串里。
- `author_role` 只使用上面的三个角色 ID；系统初始化消息可以用 `system`。
- 重要结论用 `message_type: "decision"`，待办动作可以写入 `tasks`。

## 一条消息长什么样

```json
{"id":"msg-20260622-0005","room_id":"core-team","created_at":"2026-06-22T22:10:00+08:00","author_role":"frontend_designer","author_name":"前端设计师","reply_to_id":"msg-20260622-0002","topic":"daily-sync","message_type":"answer","status":"open","tags":["home","emotion-flow"],"mentions":["product_manager"],"body":"我会先检查首页记录入口、状态反馈和历史页跳转是否一致。","links":[],"attachments":[],"related_files":["AImental_frontend/pages/daily-checkin/index.wxml"],"decisions":[],"tasks":[]}
```
