import uuid
import time
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# 导入Peewee和Pydantic的核心组件
from peewee import Model, CharField, TextField, IntegerField, FloatField, ForeignKeyField, DoesNotExist, BooleanField

from pydantic import BaseModel, Field

# 导入数据库连接和日志记录器
from db import chat_db 
from logger_config import logger 

# 确保从正确的路径导入您的AICharacter模型
from .ai_character import AICharacter

# ---------------------------------------------------
# 1. Pydantic 数据模型 (已改造)
# ---------------------------------------------------

class ChatMessageModel(BaseModel):
    """定义了单条聊天消息的结构，包含时间戳。"""
    role: str = Field(..., description="消息发送者的角色: 'user' 或 'ai'")
    content: str = Field(..., description="消息的文本内容")
    timestamp: int = Field(default_factory=lambda: int(time.time()))

class ChatListSummaryModel(BaseModel):
    """
    【已改造】用于API返回聊天列表摘要的输出模型。
    使用 unread 布尔值代替了 unread_count。
    """
    character_id: str
    character_name: str
    character_avatar_url: str
    last_message_snippet: str
    last_message_timestamp: int
    favorability: float
    # 【核心改动】使用布尔值来表示是否有未读消息
    unread: bool = Field(..., description="用户是否还没查看最新消息 (True代表有红点)")

# ---------------------------------------------------
# 2. Peewee 数据库模型 (已改造)
# ---------------------------------------------------

class CommunityChat(Model):
    """
    【已改造】Peewee模型: 存储用户与单个AI角色之间的完整对话及关系数据。
    使用 user_has_peeked 代替了 unread_count。
    """
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    
    user_id = CharField(index=True)
    character = ForeignKeyField(AICharacter, field='id', backref='chats', on_delete='CASCADE')
    
    messages_history = TextField(default='[]')
    favorability = FloatField(default=50.0)
    favorability_history = TextField(default='[]')
    
    # --- 【核心新增】“用户窥视”标志位 ---
    user_has_peeked = BooleanField(default=True, help_text="用户是否已查看过由AI发送的最新消息")
    # --- --------------------------- ---
    
    last_message_timestamp = IntegerField(default=lambda: int(time.time()))
    last_message_snippet = CharField(max_length=100, default="你们还不是好友哦~")

    class Meta:
        database = chat_db
        table_name = 'community_chats'
        indexes = ((('user_id', 'character_id'), True),)

# ---------------------------------------------------
# 3. 数据表管理类 (已改造)
# ---------------------------------------------------

class CommunityChatTable:
    """封装所有对 'community_chats' 表的数据库操作。"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.db.create_tables([CommunityChat])

    def add_message(self, user_id: str, character_id: str, role: str, content: str) -> Optional[CommunityChat]:
        """
        【已改造】
        向指定对话中添加一条新消息。
        如果消息来自AI，则将'user_has_peeked'状态置为False。
        """
        conversation, created = CommunityChat.get_or_create(
            user_id=user_id,
            character=character_id 
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
        
        # 【核心改动】不再处理 unread_count，改为处理 user_has_peeked
        if role == 'ai':
            logger.info(f"AI向用户({user_id})发送新消息，将'user_has_peeked'状态置为 False。")
            conversation.user_has_peeked = False
        
        conversation.save()
        
        # 直接返回已更新的 conversation 对象即可
        return conversation
    
    def get_chat_list_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        【已改造】获取一个用户的所有聊天列表摘要。
        unread 状态现在基于 user_has_peeked 计算。
        """
        query = (CommunityChat
                 .select(CommunityChat, AICharacter)
                 .join(AICharacter, on=(CommunityChat.character == AICharacter.id))
                 .where(CommunityChat.user_id == user_id)
                 .order_by(CommunityChat.last_message_timestamp.desc()))
        
        chat_list = []
        for conv in query:
            summary_data = {
                "character_id": conv.character.id,
                "character_name": conv.character.name,
                "character_avatar_url": conv.character.avatar_url,
                "last_message_snippet": conv.last_message_snippet,
                "last_message_timestamp": conv.last_message_timestamp,
                "favorability": round(conv.favorability, 1),
                # 【核心改动】未读状态的逻辑是“非 peeked”
                "unread": not conv.user_has_peeked
            }
            # 使用Pydantic模型验证并转换数据
            chat_list.append(ChatListSummaryModel(**summary_data).model_dump())
            
        return chat_list

    def get_conversation_history(self, user_id: str, character_id: str, limit: int = 50) -> Optional[List[Dict]]:
        """获取指定对话的完整历史。(此函数无需改动)"""
        try:
            conversation = CommunityChat.get(user_id=user_id, character=character_id)
            return json.loads(conversation.messages_history)[-limit:]
        except (DoesNotExist, json.JSONDecodeError):
            return []

    def mark_as_peeked(self, user_id: str, character_id: str) -> bool:
        """
        【核心新增方法】将对话标记为“用户已窥视”，用于清除红点。
        """
        logger.info(f"用户({user_id})正在窥视与角色({character_id})的聊天，将'user_has_peeked'置为 True。")
        query = CommunityChat.update({CommunityChat.user_has_peeked: True}).where(
            (CommunityChat.user_id == user_id) & 
            (CommunityChat.character == character_id)
        )
        rows_updated = query.execute()
        return rows_updated > 0

    def get_all_active_conversations(self) -> List[CommunityChat]:
        """获取所有活跃的对话。(此函数无需改动)"""
        return list(CommunityChat.select())

    def update_favorability(self, conversation_id: str, new_score: float, reason: str) -> bool:
        """更新指定对话的好感度。(此函数无需改动)"""
        try:
            convo = CommunityChat.get_by_id(conversation_id)
            
            clamped_score = max(0.0, min(100.0, new_score))
            
            try:
                history: List[Dict] = json.loads(convo.favorability_history)
            except json.JSONDecodeError:
                history = []
            
            today_str = (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d')
            
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
            
            history = history[-30:]
            
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