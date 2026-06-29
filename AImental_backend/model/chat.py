import uuid
import time
import json
from typing import Optional, List, Dict, Any

# Import necessary types from peewee and pydantic
# 【第1步】: 导入 BooleanField
from peewee import Model, CharField, TextField, IntegerField, BooleanField
from pydantic import BaseModel, Field

# Import the database connection for the chat module
from db import chat_db

# ---------------------------------------------------
# 1. Peewee & Pydantic Models
# ---------------------------------------------------

class Chat(Model):
    """
    The Peewee Model for the 'chats' table.
    """
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    user_id = CharField(index=True)
    title = CharField(default="New Chat")
    message = TextField(default='[]')
    timestamp = IntegerField(default=lambda: int(time.time()))
    # 【第2步】: 新增 with_context 字段，记录此会话是否加载历史背景
    with_context = BooleanField(default=True, help_text="是否在对话中引入用户历史背景")

    class Meta:
        database = chat_db
        table_name = 'chats'


class ChatModel(BaseModel):
    """
    The Pydantic Model for a chat session.
    """
    id: str
    user_id: str
    title: str
    message: str
    timestamp: int
    # 【第3步】: 在 Pydantic 模型中也同步添加该字段
    with_context: bool

    class Config:
        from_attributes = True

# This is a Pydantic model for the input when adding a new message.
class NewMessageForm(BaseModel):
    role: str = Field(..., description="消息发送者的角色，例如 'user' 或 'assistant'")
    content: str = Field(..., description="消息的内容")

# ---------------------------------------------------
# 2. Table Access Class
# ---------------------------------------------------

class ChatTable:
    """
    Encapsulates all database operations for the 'chats' table.
    """
    def __init__(self, db_connection):
        self.db = db_connection
        # The create_tables call will now handle the new 'with_context' column
        self.db.create_tables([Chat])

    def get_chat_summaries_for_user(self, user_id: str) -> List[Dict[str, str]]:
        """
        Retrieves a list of all chat summaries (id and title) for a specific user,
        sorted with the most recent chat first.
        """
        query = (Chat
                 .select(Chat.id, Chat.title)
                 .where(Chat.user_id == user_id)
                 .order_by(Chat.timestamp.desc()))
        
        return [{'id': chat.id, 'title': chat.title} for chat in query]

    def get_latest_empty_chat_for_user(self, user_id: str) -> Optional[Chat]:
        """
        Returns the latest empty chat session for the user, if one exists.
        """
        return (Chat
                .select()
                .where((Chat.user_id == user_id) & (Chat.message == '[]'))
                .order_by(Chat.timestamp.desc())
                .first())

    # 【第4步】: 修改 create_new_chat 函数签名，使其可以接收 with_context 参数
    def create_new_chat(self, user_id: str, with_context: bool = True) -> Chat:
        """
        Creates a new chat session for a given user with a title.
        """
        existing_empty_chat = self.get_latest_empty_chat_for_user(user_id)
        if existing_empty_chat:
            if existing_empty_chat.with_context != with_context:
                existing_empty_chat.with_context = with_context
                existing_empty_chat.timestamp = int(time.time())
                existing_empty_chat.save()
            return existing_empty_chat

        new_chat = Chat.create(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title="新对话",  # 统一初始标题
            message="[]",
            timestamp=int(time.time()),
            # 【第5步】: 将传入的参数值保存到数据库的新字段中
            with_context=with_context
        )
        return new_chat
    
    def update_chat_title(self, chat_id: str, new_title: str) -> bool:
        """
        Updates the title of a specific chat session.
        Returns True if the update was successful, False otherwise.
        """
        query = Chat.update(title=new_title).where(Chat.id == chat_id)
        rows_updated = query.execute()
        return rows_updated > 0

    def add_message_to_chat(self, chat_id: str, new_message: NewMessageForm) -> Optional[Chat]:
        """
        Adds a new message to an existing chat's history.
        """
        chat = Chat.get_or_none(Chat.id == chat_id)
        if not chat:
            return None

        history = json.loads(chat.message)
        history.append(new_message.model_dump())
        
        chat.message = json.dumps(history)
        chat.timestamp = int(time.time())
        chat.save()
        
        return chat

    def delete_chat_by_id(self, chat_id: str) -> bool:
        """
        Deletes a chat session by its ID.
        Returns True if deletion was successful, False otherwise.
        """
        chat_to_delete = Chat.get_or_none(Chat.id == chat_id)
        
        if chat_to_delete:
            chat_to_delete.delete_instance()
            return True
        
        return False
    
    def get_chat_history_by_id(self, chat_id: str) -> Optional[Chat]:
        """
        根据聊天ID，获取单个聊天的完整历史记录。
        """
        return Chat.get_or_none(Chat.id == chat_id)
    
chat_table = ChatTable(chat_db)
