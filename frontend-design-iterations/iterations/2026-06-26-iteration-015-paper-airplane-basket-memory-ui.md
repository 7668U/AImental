# Iteration 015 - Paper Airplane Basket Memory UI

日期：2026-06-26

## 背景

用户反馈飞机篓打开列表非常简陋，希望改成参考图那种温柔纸张弹层列表。用户还提出：每条飞机篓记录可以展示当时收下来的素材图，并给素材图编一个号，编号也存到数据库里，让列表更有记忆感。

用户随后明确：飞机篓里不需要“全部 / 未读”，因为能收进飞机篓的纸飞机必然已经打开过。

## 前端实施

- 改造 `AImental_frontend/pages/paper-airplane/index.wxml`：
  - 将飞机篓从通用白色弹窗改为专用 `basket-modal`。
  - 顶部使用圆形纸飞机徽章、标题和关闭按钮。
  - 列表项展示纸飞机素材缩略图、素材编号、记忆编号、收下时间和内容摘要。
  - 空状态使用一张纸飞机素材，不再使用纯文字空列表。
  - 点击列表项会打开已有信纸阅读弹层复看内容。
  - 移除“全部 / 未读”概念。
- 改造 `AImental_frontend/pages/paper-airplane/index.wxss`：
  - 新增纸质暖色弹层、卡片阴影、素材编号胶囊和空状态样式。
  - 保持卡片圆角克制，列表区域固定高度滚动。
- 改造 `AImental_frontend/pages/paper-airplane/index.js`：
  - 为 24 张本地纸飞机素材生成 `P01` 到 `P24` 编号。
  - 捡起纸飞机时记录当前展示的 `assetNumber` 和 `assetPath`。
  - 收下纸飞机时把素材编号和路径随请求传给后端。
  - 读取飞机篓列表时兼容旧数据：如果后端没有素材字段，按纸飞机 id 稳定映射到本地素材。
  - 修正 dataset id 可能为字符串导致当前纸飞机移除失败的问题。

## 后端实施

- 更新 `AImental_backend/model/airplane.py`：
  - `UserCollectedAirplane` 新增 `asset_number` 和 `asset_path`。
  - 启动时为已存在的 `user_collected_airplanes` 表安全补列。
  - `collect_airplane()` 保存前端传来的素材编号和路径。
  - `get_collected_airplanes()` 返回收藏关系中的素材字段和 `collected_time`。
- 更新 `AImental_backend/router/airplane.py`：
  - 新增 `PaperAirplaneCollect` 请求体接收 `asset_number` 和 `asset_path`。
  - `POST /api/v1/airplane/{airplane_id}/collect` 将素材记忆字段传入模型层。

## 验证

- `node --check AImental_frontend/pages/paper-airplane/index.js`：通过。
- `AImental_backend/.venv/Scripts/python.exe -m py_compile AImental_backend/model/airplane.py AImental_backend/router/airplane.py`：通过。
- 已检查前端无“全部 / 未读”残留。
