# model/feedback.py

import uuid
from datetime import datetime
from typing import List, Optional

# 1. 导入 Peewee 和 Pydantic 的必要模块
from peewee import Model, CharField, TextField, DateTimeField
from pydantic import BaseModel, Field

# 2. 导入数据库连接实例
from db import feedback_db
# 注意：我们在这里不直接导入 User 模型，因为它们在不同的数据库中。
# 我们通过 user_id (字符串) 来关联。

# ---------------------------------------------------
# Peewee & Pydantic Models
# ---------------------------------------------------

class Feedback(Model):
    """【Peewee 模型】用于 'feedbacks' 数据表"""
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    # 从 JWT 中获取的用户 ID，用于关联用户
    user_id = CharField(max_length=36, index=True)
    # 反馈内容，使用 TextField 以存储较长文本
    content = TextField()
    # 反馈创建时间
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        database = feedback_db
        table_name = 'feedbacks'


class FeedbackModel(BaseModel):
    """【Pydantic 模型】用于 API 响应，定义了反馈信息的数据结构"""
    id: str
    user_id: str
    content: str
    created_at: datetime

    class Config:
        # 允许模型从 ORM 对象 (如 Peewee 实例) 中直接转换和填充数据
        from_attributes = True

# ---------------------------------------------------
# 数据表访问类 (Table Access Class)
# ---------------------------------------------------

class FeedbackTable:
    """封装所有对 'feedbacks' 表的数据库操作"""
    def __init__(self, db_connection):
        self.db = db_connection
        # 确保应用启动时数据表已创建
        self.db.create_tables([Feedback])

    def create_feedback(self, user_id: str, content: str) -> Feedback:
        """
        创建一个新的用户反馈。

        Args:
            user_id (str): 提交反馈的用户的 ID.
            content (str): 反馈的具体内容.

        Returns:
            Feedback: 创建成功的 Feedback 对象.
        """
        feedback = Feedback.create(
            user_id=user_id,
            content=content
        )
        return feedback

    def get_feedback_by_user(self, user_id: str) -> List[Feedback]:
        """
        获取指定用户的所有历史反馈记录，按时间倒序排列。

        Args:
            user_id (str): 用户的 ID.

        Returns:
            List[Feedback]: 该用户的反馈列表.
        """
        return list(
            Feedback.select()
            .where(Feedback.user_id == user_id)
            .order_by(Feedback.created_at.desc())
        )

    def get_feedback_by_id(self, feedback_id: str) -> Optional[Feedback]:
        """
        根据反馈的 ID 获取单个反馈记录。
        (这个函数主要用于删除前的权限校验)

        Args:
            feedback_id (str): 反馈的 ID.

        Returns:
            Optional[Feedback]: 找到的 Feedback 对象或 None.
        """
        return Feedback.get_or_none(Feedback.id == feedback_id)


    def delete_feedback(self, feedback_id: str) -> int:
        """
        根据 ID 删除一条反馈记录。

        Args:
            feedback_id (str): 要删除的反馈的 ID.

        Returns:
            int: 被删除的行数 (通常是 1 或 0).
        """
        query = Feedback.delete().where(Feedback.id == feedback_id)
        return query.execute()

# --- 实例化数据表访问对象 ---
# 创建一个全局唯一的实例，供路由文件导入和使用
feedback_table = FeedbackTable(feedback_db)