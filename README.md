# AImental 情绪画布项目总文档

## 项目仓库

GitHub 仓库：[7668U/AImental](https://github.com/7668U/AImental)

## 项目简介

AImental 是一个面向心理陪伴、情绪记录、心理测评和长期自我观察的微信小程序项目。

当前产品迭代方向已经从“心灵社区 / AI 角色互动”逐步聚焦到“情绪记录 + 持久化分析关怀”。核心目标是让用户持续记录自己的状态，并通过分析、回看和温和建议慢慢认识自己。

## 主要模块

- `AImental_frontend/`：微信小程序前端代码。
- `AImental_backend/`：FastAPI 后端服务，负责用户、测评、打卡、分析、聊天、社区、纸飞机、笔记等接口。
- `product-design-iterations/`：产品经理 agent 的产品方案、决策日志和需求池。
- `frontend-design-iterations/`：前端设计师 agent 的 UI、素材、交互与迭代记录。
- `backend-work-iterations/`：后端工程师 agent 的角色卡、接口迭代记录和后端工作日志。
- `team-chat-database/`：产品经理、前端设计师、后端工程师三角色群聊数据库，用于跨角色同步问题、回复和决策。

## 前端项目

前端是微信小程序项目。

打开方式：

1. 安装并打开微信开发者工具。
2. 选择“导入项目”。
3. 项目目录选择 `AImental_frontend/`。
4. AppID 使用 `AImental_frontend/project.config.json` 中配置的 AppID，或按自己的开发环境替换。
5. 确认后端服务已启动，并且前端请求地址能访问到后端。

当前前端代码中大量接口地址仍指向本地开发服务：

```text
http://127.0.0.1:8000/api/v1
```

如果部署到服务器，需要统一替换为线上后端域名，后续建议封装统一 API client。

## 后端环境安装

后端目录：

```powershell
cd AImental_backend
```

推荐 Python 版本：Python 3.11。

### 1. 创建虚拟环境

使用 `uv`：

```powershell
uv venv .venv --python 3.11
```

或使用 Python 自带 `venv`：

```powershell
python -m venv .venv
```

### 2. 激活虚拟环境

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
```

Git Bash：

```bash
source .venv/Scripts/activate
```

macOS / Linux：

```bash
source .venv/bin/activate
```

### 3. 安装依赖

```powershell
pip install -r requirements.txt
```

主要后端依赖包括：

- `fastapi`
- `uvicorn`
- `peewee`
- `pydantic`
- `python-jose`
- `openai`
- `redis`
- `apscheduler`
- `jieba`

### 4. 配置环境变量

后端会读取 `.env`。本地开发至少建议准备以下变量：

```env
SECRET_KEY=replace-with-your-secret-key
WECHAT_APP_ID=replace-with-your-wechat-app-id
WECHAT_APP_SECRET=replace-with-your-wechat-app-secret
MOONSHOT_API_KEY=replace-with-your-moonshot-api-key
```

注意：

- 不要提交真实密钥。
- 当前项目中存在部分历史代码直接写入了模型服务密钥，正式使用前应迁移到环境变量并轮换旧密钥。

### 5. 启动后端服务

在 `AImental_backend/` 目录下运行：

```powershell
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

如果使用 Git Bash，也可以运行项目提供的启动脚本：

```bash
./start.sh
```

启动成功后，本地接口地址为：

```text
http://127.0.0.1:8000
```

API 文档地址：

```text
http://127.0.0.1:8000/docs
```

## Redis 与后台任务

AI 社区模块使用 Redis 和后台 worker 支持 WebSocket 推送、AI 角色延迟回复、好友请求处理和主动消息。

如果只开发测评、情绪记录、分析、笔记等基础接口，通常可以先不启动 Redis 和后台 worker。

如果需要完整运行 AI 社区功能：

1. 本机启动 Redis，默认地址：

```text
redis://localhost:6379
```

2. 启动主后端服务：

```powershell
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

3. 另开一个终端启动后台 worker：

```powershell
python background_worker.py
```

## 数据库说明

后端使用 SQLite + Peewee，数据库文件位于：

```text
AImental_backend/db/
```

常见数据库文件包括：

- `user_account.db`：用户账户。
- `psychological_assessment.db`：心理测评。
- `community_chat.db`：聊天与社区。
- `ai_status.db`：AI 角色状态与情绪/状态相关表。
- `feedback.db`：反馈。
- `promotion.db`：推广测试。
- `airplane.db` / `paper_airplane.db`：纸飞机相关数据。
- `cabinet.db` / `note.db`：笔记相关数据。

开发时请注意：数据库文件通常包含本地测试数据，不建议直接提交生产数据。

## Agent 协作文档

本项目包含三个长期协作角色：

- 产品经理：`product-design-iterations/codex-role-card.md`
- 前端设计师：`frontend-design-iterations/frontend-ui-designer-role-card.md`
- 后端工程师：`backend-work-iterations/role-card.md`

三位 Agent 共享一个内部群聊数据库。这个群聊用于 Agent 之间沟通和接力，不是用户会进入聊天的地方：

```text
team-chat-database/
```

群聊使用协议：

```text
team-chat-database/USAGE.md
```

新增群聊消息推荐使用：

```powershell
.\team-chat-database\tools\Add-ChatMessage.ps1 `
  -AuthorRole product_manager `
  -Topic "daily-sync" `
  -MessageType question `
  -Body "今天先确认首页情绪记录流程，前后端各自看一下影响范围。"
```

重新生成可读视图：

```powershell
.\team-chat-database\tools\Render-ChatThread.ps1
```

## 当前产品重点

当前优先级较高的方向：

- 将“心情日记 / 每日打卡”升级为分层情绪记录。
- 扩展情绪记录维度，例如情绪强度、能量、压力、身体反馈、触发原因、应对方式和陪伴偏好。
- 将分析页从图表报表升级为“解释 + 关怀 + 行动建议”。
- 降级或隐藏“心灵社区”一级入口，把社区能力保留为后续候选模块。
- 统一前端视觉语言、情绪图标和记录完成后的即时反馈。

## 常用开发入口

后端主入口：

```text
AImental_backend/main.py
```

后端路由目录：

```text
AImental_backend/router/
```

后端模型目录：

```text
AImental_backend/model/
```

前端主配置：

```text
AImental_frontend/app.json
```

情绪记录相关页面：

```text
AImental_frontend/pages/daily-checkin/
AImental_frontend/pkgDailyCheckin/
```

心理测评相关页面：

```text
AImental_frontend/pages/assessment/
AImental_frontend/pkgAssessment/
```

AI 咨询相关页面：

```text
AImental_frontend/pages/ai-therapist/
```

AI 社区相关页面：

```text
AImental_frontend/pages/ai-community/
AImental_frontend/pkgCommunity/
```
