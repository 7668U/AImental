# models/chat.py

import uuid
import time
import json
from typing import Optional, List, Dict, Any

# Import necessary types from peewee and pydantic
from peewee import Model, CharField, TextField, IntegerField
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
    # --- [MODIFIED] Added the title field ---
    title = CharField(default="New Chat")  # Add a default title
    message = TextField(default='[]')
    timestamp = IntegerField(default=lambda: int(time.time()))

    class Meta:
        database = chat_db
        table_name = 'chats'


class ChatModel(BaseModel):
    """
    The Pydantic Model for a chat session.
    """
    id: str
    user_id: str
    # --- [MODIFIED] Added the title field ---
    title: str
    message: str
    timestamp: int

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
        # The create_tables call will now handle the new 'title' column
        self.db.create_tables([Chat])

    # --- [MODIFIED] Function renamed and logic updated ---
    def get_chat_summaries_for_user(self, user_id: str) -> List[Dict[str, str]]:
        """
        Retrieves a list of all chat summaries (id and title) for a specific user,
        sorted with the most recent chat first.
        """
        query = (Chat
                   .select(Chat.id, Chat.title)  # Select both id and title
                   .where(Chat.user_id == user_id)
                   .order_by(Chat.timestamp.desc()))
        
        # Return a list of dictionaries, each with an id and a title
        return [{'id': chat.id, 'title': chat.title} for chat in query]

    # --- [MODIFIED] Function signature and create logic updated ---
    def create_new_chat(self, user_id: str, title: str = "New Chat") -> Chat:
        """
        Creates a new chat session for a given user with a title.
        If no title is provided, it uses the default "New Chat".
        """
        new_chat = Chat.create(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,                # Use the provided title
            message="[]",
            timestamp=int(time.time())
        )
        return new_chat

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