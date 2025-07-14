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

# Import the database connection as requested
try:
    from db import status_db
except ImportError:
    # Fallback for standalone execution or if db.py is not set up yet
    import peewee as pw
    status_db = pw.SqliteDatabase('db/daily_status.db')

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
        # This safely creates the table if it doesn't exist.
        self.db.create_tables([Checkin], safe=True)
        # self.create_dummy_data_for_month()
        
    def create_dummy_data_for_month(self, user_id: str = "d261c579-acf8-4ec6-bb70-5ef580b7465f"):
        """
        Generates a full month of random check-in data for a user.
        """
        mood_choices = ['开心', '平静', '难过', '生气', '放松', '迷茫', '尴尬', '疲惫', '兴奋']
        tag_choices = ['工作', '学习', '美食', '生病', '远足', '娱乐', '躺平', '运动']
        color_choices = ['#FFC107', '#81D4FA', '#A5D6A7', '#B0BEC5', '#F48FB1', '#C5CAE9', '#FF8A80', '#FFF59D', '#80CBC4', '#7986CB', '#BCAAA4', '#F5F5F5']

        today = datetime.datetime.now()
        year, month = today.year, today.month
        num_days = calendar.monthrange(year, month)[1]

        print(f"Attempting to generate dummy data for {year}-{month} for user {user_id}...")
        
        created_count = 0
        for day in range(1, num_days + 1):
            target_date_str = f"{year}-{month:02d}-{day:02d}"
            existing_checkin = self.get_checkin_by_date(user_id, target_date_str)
            if existing_checkin:
                continue

            date_part = datetime.datetime(year, month, day)
            time_part = datetime.time(12, 0)
            checkin_dt_obj = datetime.datetime.combine(date_part, time_part)
            
            checkin_timestamp = int(checkin_dt_obj.timestamp())

            dummy_record = {
                "user_id": user_id,
                "mood": random.choice(mood_choices),
                "tags": random.choice(tag_choices),
                "color": random.choice(color_choices),
                "text_content": f"这是{month}月{day}日的自动生成记录。",
                "timestamp": checkin_timestamp,
                "updated_at": checkin_timestamp
            }
            
            Checkin.create(**dummy_record)
            created_count += 1
        
        print(f"Dummy data generation complete. Created {created_count} new records.")
        return {"message": f"Process complete. Created {created_count} new records."}

    def create_checkin(self, user_id: str, data: CheckinBaseModel) -> Optional[Checkin]:
        """Creates a new checkin record."""
        try:
            checkin = Checkin.create(
                user_id=user_id,
                **data.model_dump(exclude_unset=True)
            )
            return checkin
        except IntegrityError:
            return None

    def get_checkin_by_id(self, checkin_id: str) -> Optional[Checkin]:
        """Retrieves a single checkin by its primary key."""
        return Checkin.get_or_none(Checkin.id == checkin_id)

    def get_checkin_by_date(self, user_id: str, target_date_str: str) -> Optional[Checkin]:
        """
        Gets the checkin for a specific user on a specific date.
        """
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
        """
        Gets all checkins for a specific user in a given month and returns them
        as a dictionary keyed by the day of the month.
        """
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

    def get_checkins_by_period(self, user_id: str, start_timestamp: int, end_timestamp: int) -> List[Dict]:
        """
        Gets all checkins for a user within a given timestamp range.
        Returns a list of dictionaries, suitable for multi-month, quarterly, or yearly queries.
        """
        query = Checkin.select().where(
            (Checkin.user_id == user_id) &
            (Checkin.timestamp >= start_timestamp) &
            (Checkin.timestamp < end_timestamp)
        ).order_by(Checkin.timestamp.asc())

        return [model_to_dict(c) for c in query]

    def update_checkin(self, checkin_id: str, data: CheckinBaseModel) -> Optional[Checkin]:
        """Updates an existing checkin record."""
        update_data = data.model_dump(exclude_unset=True)
        update_data['updated_at'] = int(time.time())

        query = Checkin.update(update_data).where(Checkin.id == checkin_id)
        rows_affected = query.execute()

        if rows_affected > 0:
            return self.get_checkin_by_id(checkin_id)
        return None

    def delete_checkin(self, checkin_id: str) -> bool:
        """Deletes a checkin record by its ID."""
        query = Checkin.delete().where(Checkin.id == checkin_id)
        rows_affected = query.execute()
        return rows_affected > 0
    
    def save_checkin_image(self, user_id: str, image_file: UploadFile) -> Optional[str]:
        """
        Saves an uploaded image for a check-in into a structured directory.
        """
        try:
            base_upload_dir = "static/status"
            today_str = datetime.datetime.now().strftime('%Y-%m-%d')
            user_specific_dir = os.path.join(base_upload_dir, user_id, today_str)
            os.makedirs(user_specific_dir, exist_ok=True)
            file_extension = os.path.splitext(image_file.filename)[1]
            new_filename = f"{int(time.time())}{file_extension}"
            save_path = os.path.join(user_specific_dir, new_filename)
            
            # --- FIX: Perform the string replacement outside of the f-string ---
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
        """Updates only the image_url for a given check-in."""
        query = Checkin.update(image_url=image_url).where(Checkin.id == checkin_id)
        rows_affected = query.execute()
        return rows_affected > 0

# ---------------------------------------------------
# 4. Helper Function & Instantiation
# ---------------------------------------------------

def model_to_dict(model_instance: Model) -> Dict:
    """A helper function to convert a Peewee model instance to a dictionary."""
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
