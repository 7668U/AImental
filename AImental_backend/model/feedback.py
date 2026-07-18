# model/feedback.py

import uuid
from datetime import datetime
from typing import List, Optional

# 1. 导入 Peewee 和 Pydantic 的必要模块
from peewee import Model, CharField, TextField, DateTimeField
from pydantic import BaseModel, Field

# 2. 导入数据库连接实例
from db import feedback_db
from security.data_encryption import EncryptedTextField

# ---------------------------------------------------
# Peewee & Pydantic Models
# ---------------------------------------------------

class Feedback(Model):
    """【Peewee 模型】用于 'feedbacks' 数据表"""
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    user_id = CharField(max_length=36, index=True)
    
    # 【新增】反馈类型字段
    # optimization: 优化意见, bug: 功能异常
    feedback_type = CharField(max_length=50, default='optimization')
    
    content = EncryptedTextField(purpose="feedbacks.content")
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        database = feedback_db
        table_name = 'feedbacks'


class FeedbackModel(BaseModel):
    """【Pydantic 模型】用于 API 响应"""
    id: str
    user_id: str

    # 【新增】在响应中也包含反馈类型
    feedback_type: str

    content: str
    created_at: datetime

    class Config:
        from_attributes = True

# ---------------------------------------------------
# 数据表访问类 (Table Access Class)
# ---------------------------------------------------

class FeedbackTable:
    """封装所有对 'feedbacks' 表的数据库操作"""
    def __init__(self, db_connection):
        self.db = db_connection
        # 确保应用启动时数据表已创建 (Peewee 会自动添加新字段)
        self.db.create_tables([Feedback])

    # 【修改】更新 create_feedback 方法以接收 feedback_type
    def create_feedback(self, user_id: str, content: str, feedback_type: str) -> Feedback:
        """
        创建一个新的用户反馈。

        Args:
            user_id (str): 提交反馈的用户的 ID.
            content (str): 反馈的具体内容.
            feedback_type (str): 反馈的类型 ('optimization' or 'bug').

        Returns:
            Feedback: 创建成功的 Feedback 对象.
        """
        feedback = Feedback.create(
            user_id=user_id,
            content=content,
            feedback_type=feedback_type #【修改】保存类型
        )
        return feedback

    # --- 其他方法无需修改 ---

    def get_feedback_by_user(self, user_id: str) -> List[Feedback]:
        return list(
            Feedback.select()
            .where(Feedback.user_id == user_id)
            .order_by(Feedback.created_at.desc())
        )

    def get_feedback_by_id(self, feedback_id: str) -> Optional[Feedback]:
        return Feedback.get_or_none(Feedback.id == feedback_id)

    def delete_feedback(self, feedback_id: str) -> int:
        query = Feedback.delete().where(Feedback.id == feedback_id)
        return query.execute()

# --- 实例化数据表访问对象 ---
feedback_table = FeedbackTable(feedback_db)
