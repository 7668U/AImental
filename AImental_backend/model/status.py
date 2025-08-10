# models/status.py

import uuid
import time
import datetime 
import calendar
import os
import shutil
from typing import Optional, List, Dict, Any

# Import necessary types from peewee and pydantic
from peewee import Model, CharField, IntegerField, TextField, IntegrityError, fn
from pydantic import BaseModel, Field
from fastapi import UploadFile
import random

# Import the database connection as requested
from db import status_db

# ---------------------------------------------------
# 1. Peewee Database Model
# ---------------------------------------------------

class Checkin(Model):
    """The Peewee Model for the 'checkins' table."""
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    user_id = CharField(max_length=36, index=True)
    mood = CharField(max_length=50)
    color = CharField(max_length=20) # e.g., "#RRGGBB"
    tags = CharField(max_length=255, null=True) # Comma-separated tags
    text_content = TextField(null=True)
    image_url = CharField(max_length=1024, null=True)
    timestamp = IntegerField(default=lambda: int(time.time()))
    updated_at = IntegerField(default=lambda: int(time.time()))

    class Meta:
        database = status_db
        table_name = 'checkins'

# ---------------------------------------------------
# 2. Pydantic Data Models (for API validation)
# ---------------------------------------------------

class CheckinBaseModel(BaseModel):
    """Pydantic model for creating/updating a Checkin."""
    mood: str
    color: str
    tags: Optional[str] = None
    text_content: Optional[str] = None
    image_url: Optional[str] = None

class CheckinModel(CheckinBaseModel):
    """The full Pydantic Model for a Checkin response."""
    id: str
    user_id: str
    timestamp: int
    updated_at: int
    
    class Config:
        from_attributes = True

# ---------------------------------------------------
# 3. Table Access Class
# ---------------------------------------------------

class CheckinTable:
    """Encapsulates all database operations for the 'checkins' table."""
    def __init__(self, db_connection):
        self.db = db_connection
        self.db.create_tables([Checkin], safe=True)
        
    def create_checkin(self, user_id: str, data: CheckinBaseModel) -> Optional[Checkin]:
        try:
            checkin = Checkin.create(
                user_id=user_id,
                **data.model_dump(exclude_unset=True)
            )
            return checkin
        except IntegrityError:
            return None

    def get_checkin_by_id(self, checkin_id: str) -> Optional[Checkin]:
        return Checkin.get_or_none(Checkin.id == checkin_id)

    def get_checkin_by_date(self, user_id: str, target_date_str: str) -> Optional[Checkin]:
        try:
            query = Checkin.select().where(
                (Checkin.user_id == user_id) &
                (fn.strftime('%Y-%m-%d', Checkin.timestamp, 'unixepoch') == target_date_str)
            ).first()
            return query
        except Exception as e:
            print(f"Error in get_checkin_by_date: {e}")
            return None

    def get_checkins_by_month(self, user_id: str, year: int, month: int) -> Dict[str, Dict]:
        start_date = datetime.datetime(year, month, 1)
        if month == 12:
            end_date = datetime.datetime(year + 1, 1, 1)
        else:
            end_date = datetime.datetime(year, month + 1, 1)
            
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())

        query = Checkin.select().where(
            (Checkin.user_id == user_id) &
            (Checkin.timestamp >= start_timestamp) &
            (Checkin.timestamp < end_timestamp)
        ).order_by(Checkin.timestamp.asc())
        
        checkins_map = {}
        for checkin in query:
            checkin_date = datetime.datetime.fromtimestamp(checkin.timestamp)
            day_key = str(checkin_date.day)
            checkins_map[day_key] = model_to_dict(checkin)
            
        return checkins_map

    # --- 【新增方法】 ---
    def get_recent_checkins(self, user_id: str, days: int = 7) -> List[Checkin]:
        """
        获取用户最近N天的打卡记录。
        """
        start_timestamp = int((datetime.datetime.now() - datetime.timedelta(days=days)).timestamp())
        
        query = Checkin.select().where(
            (Checkin.user_id == user_id) &
            (Checkin.timestamp >= start_timestamp)
        ).order_by(Checkin.timestamp.desc())
        
        return list(query)
    # --- ----------- ---

    def update_checkin(self, checkin_id: str, data: CheckinBaseModel) -> Optional[Checkin]:
        update_data = data.model_dump(exclude_unset=True)
        update_data['updated_at'] = int(time.time())

        query = Checkin.update(update_data).where(Checkin.id == checkin_id)
        rows_affected = query.execute()

        if rows_affected > 0:
            return self.get_checkin_by_id(checkin_id)
        return None

    def delete_checkin(self, checkin_id: str) -> bool:
        query = Checkin.delete().where(Checkin.id == checkin_id)
        rows_affected = query.execute()
        return rows_affected > 0
    
    def save_checkin_image(self, user_id: str, image_file: UploadFile) -> Optional[str]:
        try:
            base_upload_dir = "static/status"
            user_specific_dir = os.path.join(base_upload_dir, user_id)
            os.makedirs(user_specific_dir, exist_ok=True)
            file_extension = os.path.splitext(image_file.filename)[1]
            new_filename = f"{int(time.time())}{file_extension}"
            save_path = os.path.join(user_specific_dir, new_filename)
            
            clean_path = save_path.replace('\\', '/')
            web_path = f"/{clean_path}"
            
            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
            return web_path
        except IOError as e:
            print(f"Error saving check-in image: {e}")
            return None
        finally:
            image_file.file.close()
            
    def update_image_url(self, checkin_id: str, image_url: str) -> bool:
        query = Checkin.update(image_url=image_url).where(Checkin.id == checkin_id)
        rows_affected = query.execute()
        return rows_affected > 0

# ---------------------------------------------------
# 4. Helper Function & Instantiation
# ---------------------------------------------------

def model_to_dict(model_instance: Model) -> Dict:
    return {
        "id": model_instance.id,
        "user_id": model_instance.user_id,
        "mood": model_instance.mood,
        "color": model_instance.color,
        "tags": model_instance.tags,
        "text_content": model_instance.text_content,
        "image_url": model_instance.image_url,
        "timestamp": model_instance.timestamp,
        "updated_at": model_instance.updated_at
    }

checkin_table = CheckinTable(status_db)