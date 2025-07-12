# models/checkin.py

import uuid
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

# Import necessary types from peewee and pydantic
from peewee import Model, CharField, IntegerField, TextField, IntegrityError
from pydantic import BaseModel, Field

# Import the database connection as requested
# Assuming you have a db.py file with: status_db = pw.SqliteDatabase('db/daily_status.db')
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
    # user_id is a CharField to store the User's UUID string, with an index for faster lookups.
    user_id = CharField(max_length=36, index=True)
    mood = CharField(max_length=50)
    color = CharField(max_length=20) # e.g., "#RRGGBB"
    tags = CharField(max_length=255, null=True) # Comma-separated tags
    text_content = TextField(null=True)
    image_url = CharField(max_length=1024, null=True)
    # Using IntegerField for Unix timestamps as requested.
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
        self.db.create_tables([Checkin])

    def create_checkin(self, user_id: str, data: CheckinBaseModel) -> Optional[Checkin]:
        """Creates a new checkin record."""
        try:
            checkin = Checkin.create(
                user_id=user_id,
                **data.model_dump(exclude_unset=True) # Uses Pydantic model data
            )
            return checkin
        except IntegrityError:
            # Handle potential database integrity errors
            return None

    def get_checkin_by_id(self, checkin_id: str) -> Optional[Checkin]:
        """Retrieves a single checkin by its primary key."""
        return Checkin.get_or_none(Checkin.id == checkin_id)

    def get_checkin_by_date(self, user_id: str, target_date: datetime.date) -> Optional[Checkin]:
        """Gets the checkin for a specific user on a specific date."""
        start_of_day = int(datetime.combine(target_date, datetime.min.time()).timestamp())
        end_of_day = int(datetime.combine(target_date, datetime.max.time()).timestamp())
        
        return Checkin.get_or_none(
            (Checkin.user_id == user_id) &
            (Checkin.timestamp >= start_of_day) &
            (Checkin.timestamp <= end_of_day)
        )

    def get_checkins_by_month(self, user_id: str, year: int, month: int) -> List[Checkin]:
        """Gets all checkins for a specific user in a given month."""
        # Calculate start and end timestamps for the month
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
            
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())

        query = Checkin.select().where(
            (Checkin.user_id == user_id) &
            (Checkin.timestamp >= start_timestamp) &
            (Checkin.timestamp < end_timestamp)
        ).order_by(Checkin.timestamp.asc())
        
        return list(query)

    def update_checkin(self, checkin_id: str, data: CheckinBaseModel) -> Optional[Checkin]:
        """Updates an existing checkin record."""
        update_data = data.model_dump(exclude_unset=True)
        update_data['updated_at'] = int(time.time()) # Manually update the timestamp

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

# ---------------------------------------------------
# 4. Instantiate the Table Access Object
# ---------------------------------------------------
# This single instance will be imported by your routers.
checkin_table = CheckinTable(status_db)