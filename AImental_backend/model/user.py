# models/user.py

import uuid
from datetime import datetime
from typing import Optional

# Import necessary types from peewee and other libraries
from peewee import Model, CharField, IntegerField, DateTimeField
from pydantic import BaseModel
from fastapi import UploadFile
import shutil
import os

# Import the database connection
from db import user_db

# --- Static Configuration ---
DEFAULT_AVATAR_URL = "/static/avatars/default.png"
AVATAR_UPLOAD_DIR = "static/avatars/"

# ---------------------------------------------------
# 1. Peewee & Pydantic Models (No changes here)
# ---------------------------------------------------

class User(Model):
    """The Peewee Model for the 'users' table."""
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    openid = CharField(max_length=128, unique=True, index=True)
    nickname = CharField(max_length=255, null=True)
    avatar_url = CharField(max_length=1024, null=True)
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
    status: int
    created_at: datetime
    last_login_at: datetime
    
    class Config:
        from_attributes = True

# ---------------------------------------------------
# 2. Table Access Class (Updated)
# ---------------------------------------------------

class UserTable:
    """Encapsulates all database operations for the 'users' table."""
    def __init__(self, db_connection):
        self.db = db_connection
        self.db.create_tables([User])
        os.makedirs(AVATAR_UPLOAD_DIR, exist_ok=True)

    # --- Method 1: Create User (Modified for login flow) ---
    def create_user(self, openid: str, nickname: str, avatar_url: Optional[str] = None) -> Optional[User]:
        """
        Creates a new user. If the user already exists, returns None.
        Handles optional avatar_url.
        """
        if User.get_or_none(User.openid == openid):
            return None # User already exists

        user = User.create(
            id=str(uuid.uuid4()), 
            openid=openid,
            nickname=nickname,
            # Use provided avatar_url or fall back to the default
            avatar_url=avatar_url or DEFAULT_AVATAR_URL
        )
        return user

    # --- Method 2: Get User by OpenID (NEW) ---
    def get_user_by_openid(self, openid: str) -> Optional[User]:
        """
        Finds a user by their openid.
        Returns the User object or None if not found.
        """
        return User.get_or_none(User.openid == openid)

    # --- Method 3: Get User by ID (NEW) ---
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Finds a user by their primary key ID.
        """
        return User.get_or_none(User.id == user_id)

    # --- Method 4: Update User Profile (NEW) ---
    def update_user_profile(self, user_id: str, nickname: Optional[str], avatar_url: Optional[str]):
        """
        Updates a user's nickname and/or avatar URL.
        Only updates fields that are actually provided.
        """
        update_data = {}
        if nickname is not None:
            update_data[User.nickname] = nickname
        if avatar_url is not None:
            update_data[User.avatar_url] = avatar_url
        
        if update_data:
            query = User.update(update_data).where(User.id == user_id)
            query.execute()

    # --- Method 5: Update User Avatar (Existing, no changes needed) ---
    def update_avatar(self, user_id: str, image_file: UploadFile) -> Optional[str]:
        """
        Updates the avatar for a user identified by their string id.
        """
        user = User.get_or_none(User.id == user_id)
        if not user:
            return None

        file_extension = os.path.splitext(image_file.filename)[1]
        new_filename = f"{user_id}_{int(datetime.now().timestamp())}{file_extension}"
        
        save_path = os.path.join(AVATAR_UPLOAD_DIR, new_filename)
        web_path = f"/{save_path}" # Assuming 'static' is served at the root

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
    
# --- Instantiate the table access object ---
user_table = UserTable(user_db)