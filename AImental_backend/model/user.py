# models/user.py

import uuid
from datetime import datetime, date
from typing import Optional

# Import necessary types from peewee and other libraries
from peewee import Model, CharField, IntegerField, DateTimeField, DateField, BooleanField
from pydantic import BaseModel, Field
from fastapi import UploadFile
import shutil
import os

# Import the database connection
from db import user_db

# --- Static Configuration ---
DEFAULT_AVATAR_URL = "/static/avatars/default.png"
AVATAR_UPLOAD_DIR = "static/avatars/"

# ---------------------------------------------------
# 1. Peewee & Pydantic Models (已更新)
# ---------------------------------------------------

class User(Model):
    """The Peewee Model for the 'users' table."""
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    openid = CharField(max_length=128, unique=True, index=True)
    nickname = CharField(max_length=255, null=True)
    avatar_url = CharField(max_length=1024, null=True)
        # --- 【新增字段】 ---
    # 这个标志位将用于永久记录用户是否已通过分享解锁了所有社区角色
    has_unlocked_community = BooleanField(default=False, help_text="是否已分享解锁了社区")
    # --- 【新增结束】 ---
    gender = IntegerField(default=0, null=True)  # 0: 未知, 1: 男, 2: 女
    birthday = DateField(null=True)
    
    # --- 【新增字段】 ---
    allow_ai_read_data = BooleanField(default=False)
    # --- --------- ---
    
    status = IntegerField(default=1)
    created_at = DateTimeField(default=datetime.now)
    last_login_at = DateTimeField(default=datetime.now)

    class Meta:
        database = user_db
        table_name = 'users'


class UserModel(BaseModel):
    """The Pydantic Model for a user."""
    id: str
    openid: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    
    gender: Optional[int] = Field(None, description="0: 保密, 1: 男, 2: 女")
    birthday: Optional[date] = None
    
    # --- 【新增字段】 ---
    allow_ai_read_data: bool
    # --- --------- ---

    status: int
    created_at: datetime
    last_login_at: datetime
    
    class Config:
        from_attributes = True

# ---------------------------------------------------
# 2. Table Access Class (已更新)
# ---------------------------------------------------

class UserTable:
    """Encapsulates all database operations for the 'users' table."""
    def __init__(self, db_connection):
        self.db = db_connection
        # 确保启动时自动创建表（包括新字段）
        self.db.create_tables([User])
        os.makedirs(AVATAR_UPLOAD_DIR, exist_ok=True)

    def create_user(self, openid: str, nickname: str, avatar_url: Optional[str] = None) -> Optional[User]:
        if User.get_or_none(User.openid == openid):
            return None

        user = User.create(
            id=str(uuid.uuid4()), 
            openid=openid,
            nickname=nickname,
            avatar_url=avatar_url or DEFAULT_AVATAR_URL
        )
        return user

    def get_user_by_openid(self, openid: str) -> Optional[User]:
        return User.get_or_none(User.openid == openid)

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        return User.get_or_none(User.id == user_id)

    def update_user_profile(self, user_id: str, nickname: Optional[str], avatar_url: Optional[str]):
        update_data = {}
        if nickname is not None:
            update_data[User.nickname] = nickname
        if avatar_url is not None:
            update_data[User.avatar_url] = avatar_url
        
        if update_data:
            query = User.update(update_data).where(User.id == user_id)
            query.execute()

    def update_avatar(self, user_id: str, image_file: UploadFile) -> Optional[str]:
        user = User.get_or_none(User.id == user_id)
        if not user:
            return None

        file_extension = os.path.splitext(image_file.filename)[1]
        new_filename = f"{user_id}_{int(datetime.now().timestamp())}{file_extension}"
        
        save_path = os.path.join(AVATAR_UPLOAD_DIR, new_filename)
        web_path = f"/{save_path}"

        try:
            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
        except IOError as e:
            print(f"Error saving file: {e}")
            return None
        finally:
            image_file.file.close()

        user.avatar_url = web_path
        user.save()

        return web_path
        
    def update_user_info(self, user_id: str, nickname: Optional[str], gender: Optional[int], birthday: Optional[date]) -> bool:
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        update_data = {}
        if nickname is not None:
            update_data['nickname'] = nickname
        if gender is not None:
            update_data['gender'] = gender
        if birthday is not None:
            update_data['birthday'] = birthday

        if not update_data:
            return True

        query = User.update(**update_data).where(User.id == user_id)
        rows_updated = query.execute()
        return rows_updated > 0

    # --- 【新增方法】 ---
    def update_ai_read_permission(self, user_id: str, allow: bool) -> bool:
        """
        Updates the user's permission for the AI to read their data.
        """
        query = User.update({User.allow_ai_read_data: allow}).where(User.id == user_id)
        rows_updated = query.execute()
        return rows_updated > 0

# --- Instantiate the table access object ---
user_table = UserTable(user_db)
