# models/chat_community.py

import uuid
import time
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

# 导入Peewee和Pydantic的核心组件
from peewee import Model, CharField, TextField, IntegerField, FloatField, ForeignKeyField, DoesNotExist
from pydantic import BaseModel, Field

# 导入数据库连接
from db import chat_db 

# 确保从正确的路径导入您的AICharacter模型
from .ai_character import AICharacter

# ---------------------------------------------------
# 1. Pydantic 数据模型 (已更新)
# ---------------------------------------------------

class ChatMessageModel(BaseModel):
    """定义了单条聊天消息的结构，包含时间戳。"""
    role: str = Field(..., description="消息发送者的角色: 'user' 或 'ai'")
    content: str = Field(..., description="消息的文本内容")
    timestamp: int = Field(default_factory=lambda: int(time.time()))

class ChatListSummaryModel(BaseModel):
    """用于API返回聊天列表摘要的输出模型，现在包含了未读数。"""
    character_id: str
    character_name: str
    character_avatar_url: str
    last_message_snippet: str
    last_message_timestamp: int
    favorability: float
    # 【新增】未读消息数字段，用于前端渲染小红点
    unread_count: int = Field(..., description="用户未读的AI消息数量")

# ---------------------------------------------------
# 2. Peewee 数据库模型 (已更新)
# ---------------------------------------------------

class CommunityChat(Model):
    """
    Peewee模型: 存储用户与单个AI角色之间的完整对话及关系数据。
    """
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    
    user_id = CharField(index=True)
    character = ForeignKeyField(AICharacter, field='id', backref='chats', on_delete='CASCADE')
    
    messages_history = TextField(default='[]')
    
    favorability = FloatField(default=50.0)
    favorability_history = TextField(default='[]')
    
    # --- 【核心新增字段】 ---
    # 用于实现小红点功能
    unread_count = IntegerField(default=0, help_text="用户未读的AI消息数量")
    # --- 【核心新增字段】 ---
    
    last_message_timestamp = IntegerField(default=lambda: int(time.time()))
    last_message_snippet = CharField(max_length=100, default="你们还不是好友哦~")

    class Meta:
        database = chat_db
        table_name = 'community_chats'
        indexes = ((('user_id', 'character_id'), True),)

# ---------------------------------------------------
# 3. 数据表管理类 (已更新)
# ---------------------------------------------------

class CommunityChatTable:
    """封装所有对 'community_chats' 表的数据库操作。"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.db.create_tables([CommunityChat])

    def add_message(self, user_id: str, character_id: str, role: str, content: str) -> Optional[CommunityChat]:
        """向指定的对话中添加一条新消息。"""
        conversation, created = CommunityChat.get_or_create(
            user_id=user_id,
            character_id=character_id
        )
        
        try:
            history: List[Dict] = json.loads(conversation.messages_history)
        except json.JSONDecodeError:
            history = []
            
        new_message = ChatMessageModel(role=role, content=content)
        history.append(new_message.model_dump())
        
        conversation.messages_history = json.dumps(history, ensure_ascii=False)
        conversation.last_message_timestamp = new_message.timestamp
        conversation.last_message_snippet = (
            new_message.content[:97] + '...' 
            if len(new_message.content) > 100 
            else new_message.content
        )
        
        # 【新增逻辑】如果是AI发送的消息，则未读数+1
        if role == 'ai':
            # 使用Peewee的原子性操作，防止并发问题
            CommunityChat.update(unread_count=CommunityChat.unread_count + 1).where(
                CommunityChat.id == conversation.id
            ).execute()
        
        conversation.save()
        return conversation

    def get_chat_list_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """获取一个用户的所有聊天列表摘要，已包含未读数。"""
        query = (CommunityChat
                 .select(CommunityChat, AICharacter)
                 .join(AICharacter, on=(CommunityChat.character == AICharacter.id))
                 .where(CommunityChat.user_id == user_id)
                 .order_by(CommunityChat.last_message_timestamp.desc()))
        
        chat_list = [
            ChatListSummaryModel(
                character_id=conv.character.id,
                character_name=conv.character.name,
                character_avatar_url=conv.character.avatar_url,
                last_message_snippet=conv.last_message_snippet,
                last_message_timestamp=conv.last_message_timestamp,
                favorability=round(conv.favorability, 1),
                # 【新增】包含未读数
                unread_count=conv.unread_count
            ).model_dump() for conv in query
        ]
        return chat_list

    def get_conversation_history(self, user_id: str, character_id: str, limit: int = 50) -> Optional[List[Dict]]:
        """获取指定对话的完整历史。"""
        try:
            conversation = CommunityChat.get(user_id=user_id, character=character_id)
            return json.loads(conversation.messages_history)[-limit:]
        except (DoesNotExist, json.JSONDecodeError):
            return []

    def mark_as_read(self, user_id: str, character_id: str) -> bool:
        """【新增方法】将对话标记为已读，清空未读数。"""
        query = CommunityChat.update({CommunityChat.unread_count: 0}).where(
            (CommunityChat.user_id == user_id) & 
            (CommunityChat.character == character_id)
        )
        return query.execute() > 0

    def get_all_active_conversations(self) -> List[CommunityChat]:
        """
        【新增】获取所有活跃的对话，用于后台批量更新好感度。
        可以根据需要增加筛选条件，例如只更新最近一个月内有活动的用户。
        """
        return list(CommunityChat.select())

    def update_favorability(self, conversation_id: str, new_score: float, reason: str) -> bool:
        """
        【新增】更新指定对话的好感度，并记录变更历史。
        """
        try:
            convo = CommunityChat.get_by_id(conversation_id)
            
            # 限制好感度在0-100之间
            clamped_score = max(0.0, min(100.0, new_score))
            
            try:
                history: List[Dict] = json.loads(convo.favorability_history)
            except json.JSONDecodeError:
                history = []
                
            today_str = datetime.now().strftime('%Y-%m-%d')
            
            # 为了防止重复记录，如果今天已经有记录，则更新它，否则添加新的
            day_found = False
            for record in history:
                if record.get('date') == today_str:
                    record['score'] = clamped_score
                    record['reason'] = reason
                    day_found = True
                    break
            
            if not day_found:
                history.append({
                    "date": today_str,
                    "score": clamped_score,
                    "reason": reason
                })
            
            # 为了防止历史记录无限增长，可以只保留最近的N条记录
            history = history[-30:]
            
            # 使用原子性更新，效率更高
            query = CommunityChat.update(
                favorability=clamped_score,
                favorability_history=json.dumps(history, ensure_ascii=False)
            ).where(CommunityChat.id == conversation_id)
            
            return query.execute() > 0
        
        except DoesNotExist:
            return False

# ---------------------------------------------------
# 4. 实例化
# ---------------------------------------------------
community_chat_table = CommunityChatTable(chat_db)
