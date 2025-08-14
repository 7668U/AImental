# models/friendship.py

import uuid
from datetime import datetime, timedelta
from peewee import Model, CharField, TextField, DateTimeField, ForeignKeyField, DoesNotExist
from typing import Optional
# 导入数据库连接及相关模型
from db import chat_db  # 好友关系可以认为是用户核心数据的一部分
from .ai_character import AICharacter
from .user import User # 假设您的用户模型在这里

class Friendship(Model):
    """
    Peewee模型: 记录用户与AI角色之间的好友关系。
    """
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    
    # 关系双方
    user = ForeignKeyField(User, backref='ai_friends', field='id', on_delete='CASCADE')
    character = ForeignKeyField(AICharacter, backref='human_friends', field='id', on_delete='CASCADE')
    
    # 关系状态: 'pending', 'accepted', 'rejected', 'blocked'
    status = CharField(max_length=20, default='pending', index=True)
    
    # 用户发送的验证信息
    verification_message = TextField(null=True)
    
    # 时间戳
    request_timestamp = DateTimeField(default=lambda: datetime.utcnow() + timedelta(hours=8))
    response_timestamp = DateTimeField(null=True)

    class Meta:
        database = chat_db
        table_name = 'friendships'
        indexes = (
            (('user', 'character'), True), # 确保一个用户和一个AI角色之间只有一种关系
        )

class FriendshipTable:
    def __init__(self, db_connection):
        self.db = db_connection
        self.db.create_tables([Friendship])

    def create_request(self, user_id: str, character_id: str, message: str) -> 'Friendship':
        """创建或重新发起一个好友请求。"""
        request, created = Friendship.get_or_create(
            user_id=user_id,
            character_id=character_id,
            defaults={
                'verification_message': message,
                'status': 'pending',
                'request_timestamp': datetime.utcnow() + timedelta(hours=8)
            }
        )
        # 如果不是新创建的（例如之前被拒绝过），则重置状态和消息
        if not created:
            request.status = 'pending'
            request.verification_message = message
            request.request_timestamp = datetime.utcnow() + timedelta(hours=8)
            request.response_timestamp = None
            request.save()
        return request

    def get_friendship_status(self, user_id: str, character_id: str) -> Optional[str]:
        """获取两个实体间的关系状态。"""
        try:
            friendship = Friendship.get(user=user_id, character=character_id)
            return friendship.status
        except DoesNotExist:
            return None

    def update_request_status(self, request_id: str, new_status: str) -> bool:
        """根据ID更新请求状态。"""
        query = Friendship.update(
            status=new_status,
            response_timestamp=datetime.utcnow() + timedelta(hours=8)
        ).where(Friendship.id == request_id)
        return query.execute() > 0

# 实例化
friendship_table = FriendshipTable(chat_db)