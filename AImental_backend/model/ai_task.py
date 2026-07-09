# models/ai_task.py

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict

# 导入Peewee和Pydantic的核心组件
from peewee import Model, CharField, DateTimeField, DoesNotExist
from pydantic import BaseModel, Field

# 导入数据库连接
from db import chat_db  # 假设任务队列也存放在chat_db中

# ---------------------------------------------------
# 1. Pydantic 数据模型
# ---------------------------------------------------

class AITaskModel(BaseModel):
    """用于API响应或数据交换的Pydantic任务模型"""
    id: str
    user_id: str
    character_id: str
    task_type: str
    status: str
    execute_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True

# ---------------------------------------------------
# 2. Peewee 数据库模型
# ---------------------------------------------------

class AITask(Model):
    """
    Peewee模型: AI任务队列。
    这是整个系统异步行为的“大脑中枢”。
    """
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    
    # 任务关联的核心信息
    user_id = CharField(index=True)
    character_id = CharField(index=True)
    
    # 任务类型: 'reply', 'proactive_chat', 'friend_request_response' 等
    task_type = CharField(max_length=50, index=True)
    
    # 任务状态: 'pending', 'processing', 'done', 'failed'
    status = CharField(max_length=20, default='pending', index=True)
    
    # 计划执行时间，异步回复的关键
    execute_at = DateTimeField(index=True)
    
    created_at = DateTimeField(default=lambda: datetime.utcnow() + timedelta(hours=8))
    updated_at = DateTimeField(default=lambda: datetime.utcnow() + timedelta(hours=8))

    def save(self, *args, **kwargs):
        """重写save方法，自动更新updated_at时间戳"""
        self.updated_at = datetime.utcnow() + timedelta(hours=8)
        return super(AITask, self).save(*args, **kwargs)

    class Meta:
        database = chat_db
        table_name = 'ai_task_queue'
        # 为最常见的查询建立联合索引，极大提升性能
        indexes = (
            # 这个索引用于快速查找某个用户与某个AI之间，是否存在待处理的同类型任务
            (('user_id', 'character_id', 'task_type', 'status'), False),
            # 这个索引用于后台工作进程快速拉取到期任务
            (('status', 'execute_at'), False),
        )

# ---------------------------------------------------
# 3. 数据表管理类 (Table Access Class) - 已升级
# ---------------------------------------------------

class AITaskTable:
    """
    封装所有对 'ai_task_queue' 表的操作，并实现您的核心逻辑。
    """
    def __init__(self, db_connection):
        self.db = db_connection
        self.db.create_tables([AITask])

    def create_task_if_needed(self, user_id: str, character_id: str, task_type: str, execute_at: datetime) -> Optional[AITask]:
        """
        【核心逻辑 - 通用版】
        检查是否存在待处理的【同类型】任务，如果不存在，则创建一个新的。
        这个函数现在是所有异步任务的统一入口。

        Args:
            user_id (str): 用户ID
            character_id (str): AI角色ID
            task_type (str): 任务的类型 (e.g., 'reply', 'proactive_chat')
            execute_at (datetime): 任务的计划执行时间

        Returns:
            - 如果成功创建了新任务，则返回该任务实例。
            - 如果已存在待处理的同类型任务，则返回 None。
        """
        try:
            # 查找针对这个用户、角色、且类型和状态都相同的任务
            existing_task = AITask.get(
                (AITask.user_id == user_id) &
                (AITask.character_id == character_id) &
                (AITask.task_type == task_type) &  # <--- 关键修改点
                (AITask.status == 'pending')
            )
            # 如果找到了，说明已经有一个同类型的任务在排队了，无需重复创建
            print(f"INFO: 已存在待处理的 '{task_type}' 任务 for user {user_id} & char {character_id}。无需创建新任务。")
            return None
        except DoesNotExist:
            # 如果没找到，我们创建一个新任务
            print(f"INFO: 未找到待处理的 '{task_type}' 任务。为 user {user_id} & char {character_id} 创建新任务。")
            new_task = AITask.create(
                user_id=user_id,
                character_id=character_id,
                task_type=task_type,  # <--- 使用传入的类型
                execute_at=execute_at,
                status='pending'
            )
            return new_task

    def get_due_tasks(self, limit: int = 10) -> List[AITask]:
        """
        获取所有已到期且待处理的任务。
        这是后台工作进程(background_worker)需要调用的主要函数。
        """
        now = datetime.utcnow() + timedelta(hours=8)
        query = (AITask
                 .select()
                 .where(
                     (AITask.status == 'pending') &
                     (AITask.execute_at <= now)
                 )
                 .order_by(AITask.execute_at)
                 .limit(limit))
        return list(query)

    def update_task_status(self, task_id: str, status: str) -> bool:
        """更新指定任务的状态。"""
        query = AITask.update({
            AITask.status: status,
            AITask.updated_at: datetime.utcnow() + timedelta(hours=8),
        }).where(AITask.id == task_id)
        rows_updated = query.execute()
        return rows_updated > 0

    def has_pending_task(self, user_id: str, character_id: str, task_type: str) -> bool:
        """检查是否已经有同类型待处理任务。"""
        return AITask.select().where(
            (AITask.user_id == user_id)
            & (AITask.character_id == character_id)
            & (AITask.task_type == task_type)
            & (AITask.status == 'pending')
        ).exists()

    def has_recent_done_task(
        self,
        user_id: str,
        character_id: str,
        task_type: str,
        since: datetime,
    ) -> bool:
        """检查指定时间后是否已经完成过某类任务，用于主动消息冷却。"""
        return AITask.select().where(
            (AITask.user_id == user_id)
            & (AITask.character_id == character_id)
            & (AITask.task_type == task_type)
            & (AITask.status == 'done')
            & (AITask.updated_at >= since)
        ).exists()

# ---------------------------------------------------
# 4. 实例化 (Instantiation)
# ---------------------------------------------------
ai_task_table = AITaskTable(chat_db)
