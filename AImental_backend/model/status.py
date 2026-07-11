# models/status.py

import uuid
import time
import datetime 
import calendar
import json
import os
from typing import Optional, List, Dict, Any

# Import necessary types from peewee and pydantic
from peewee import Model, CharField, IntegerField, TextField, FloatField, IntegrityError, fn
from pydantic import BaseModel, Field
from fastapi import UploadFile
import random
from .checkin_dimensions import (
    MOOD_OPTIONS,
    STATUS_OPTIONS,
    COLOR_OPTIONS,
    enrich_checkin_payload,
    get_mood_meta,
    get_color_meta,
    build_status_meta_from_tags,
    load_list,
)
from security.data_encryption import EncryptedFloatField, EncryptedTextField

MAX_CHECKIN_IMAGES = 3


def normalize_image_urls(value: Any, fallback_url: Optional[str] = None) -> List[str]:
    """Returns a deduplicated, capped list of check-in image URLs."""
    raw_items = []
    if isinstance(value, list):
        raw_items.extend(value)
    elif isinstance(value, str):
        stripped = value.strip()
        if stripped:
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    raw_items.extend(parsed)
                else:
                    raw_items.append(stripped)
            except json.JSONDecodeError:
                raw_items.append(stripped)

    if fallback_url:
        raw_items.append(fallback_url)

    urls = []
    seen = set()
    for item in raw_items:
        url = str(item).strip() if item is not None else ""
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
        if len(urls) >= MAX_CHECKIN_IMAGES:
            break
    return urls


def dump_image_urls(value: Any, fallback_url: Optional[str] = None) -> str:
    return json.dumps(
        normalize_image_urls(value, fallback_url),
        ensure_ascii=False,
        separators=(",", ":"),
    )

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
    mood = EncryptedTextField(purpose="checkins.mood")
    mood_id = EncryptedTextField(purpose="checkins.mood_id", null=True)
    mood_family = EncryptedTextField(purpose="checkins.mood_family", null=True)
    mood_valence = EncryptedTextField(purpose="checkins.mood_valence", null=True)
    mood_energy = EncryptedTextField(purpose="checkins.mood_energy", null=True)
    color = EncryptedTextField(purpose="checkins.color")
    color_id = EncryptedTextField(purpose="checkins.color_id", null=True)
    color_label = EncryptedTextField(purpose="checkins.color_label", null=True)
    color_group = EncryptedTextField(purpose="checkins.color_group", null=True)
    color_tone = EncryptedTextField(purpose="checkins.color_tone", null=True)
    color_description = EncryptedTextField(
        purpose="checkins.color_description",
        null=True,
    )
    tags = EncryptedTextField(purpose="checkins.tags", null=True)
    status_ids = EncryptedTextField(purpose="checkins.status_ids", null=True)
    status_families = EncryptedTextField(
        purpose="checkins.status_families",
        null=True,
    )
    text_content = EncryptedTextField(purpose="checkins.text_content", null=True)
    image_url = EncryptedTextField(purpose="checkins.image_url", null=True)
    image_urls = EncryptedTextField(purpose="checkins.image_urls", null=True)
    location_name = EncryptedTextField(purpose="checkins.location_name", null=True)
    location_address = EncryptedTextField(
        purpose="checkins.location_address",
        null=True,
    )
    location_latitude = EncryptedFloatField(
        purpose="checkins.location_latitude",
        null=True,
    )
    location_longitude = EncryptedFloatField(
        purpose="checkins.location_longitude",
        null=True,
    )
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
    image_urls: Optional[List[str]] = None
    mood_id: Optional[str] = None
    mood_family: Optional[str] = None
    mood_valence: Optional[str] = None
    mood_energy: Optional[str] = None
    status_ids: Optional[List[str]] = None
    status_families: Optional[List[str]] = None
    color_id: Optional[str] = None
    color_label: Optional[str] = None
    color_group: Optional[str] = None
    color_tone: Optional[str] = None
    color_description: Optional[str] = None
    location_name: Optional[str] = None
    location_address: Optional[str] = None
    location_latitude: Optional[float] = None
    location_longitude: Optional[float] = None

class CheckinModel(CheckinBaseModel):
    """The full Pydantic Model for a Checkin response."""
    id: str
    user_id: str
    timestamp: int
    updated_at: int
    mood_icon: Optional[str] = None
    status_items: List[Dict[str, Any]] = Field(default_factory=list)
    image_urls: List[str] = Field(default_factory=list)
    
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
        self._ensure_schema()
        # self.create_dummy_data_for_month()

    def _ensure_schema(self):
        """Adds V2 dimension columns to existing SQLite tables without data loss."""
        existing_columns = {
            row[1] for row in self.db.execute_sql("PRAGMA table_info(checkins)").fetchall()
        }
        migrations = {
            "mood_id": "VARCHAR(50)",
            "mood_family": "VARCHAR(50)",
            "mood_valence": "VARCHAR(20)",
            "mood_energy": "VARCHAR(20)",
            "color_id": "VARCHAR(50)",
            "color_label": "VARCHAR(50)",
            "color_group": "VARCHAR(50)",
            "color_tone": "VARCHAR(20)",
            "color_description": "VARCHAR(255)",
            "status_ids": "TEXT",
            "status_families": "TEXT",
            "image_urls": "TEXT",
            "location_name": "VARCHAR(255)",
            "location_address": "VARCHAR(1024)",
            "location_latitude": "REAL",
            "location_longitude": "REAL",
        }
        for column_name, column_type in migrations.items():
            if column_name not in existing_columns:
                self.db.execute_sql(
                    f"ALTER TABLE checkins ADD COLUMN {column_name} {column_type}"
                )
        
    def create_dummy_data_for_month(self, user_id: str = "c959d470-64e7-45fe-8942-45ee05d0f153"):
        """
        Generates a full month of random check-in data for a user.
        """
        mood_choices = [item["label"] for item in MOOD_OPTIONS]
        tag_choices = [item["label"] for item in STATUS_OPTIONS]
        color_choices = [item["hex"] for item in COLOR_OPTIONS]

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

            dummy_record = enrich_checkin_payload({
                "user_id": user_id,
                "mood": random.choice(mood_choices),
                "tags": random.choice(tag_choices),
                "color": random.choice(color_choices),
                "text_content": f"这是{month}月{day}日的自动生成记录。",
                "timestamp": checkin_timestamp,
                "updated_at": checkin_timestamp
            })
            
            Checkin.create(**dummy_record)
            created_count += 1
        
        print(f"Dummy data generation complete. Created {created_count} new records.")
        return {"message": f"Process complete. Created {created_count} new records."}

    def seed_five_days_for_month(
        self,
        user_id: str,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Creates up to five deterministic check-ins in a month for local analysis testing.
        Existing days are kept intact and counted toward the five-day target.
        """
        today = datetime.datetime.now()
        target_year = year or today.year
        target_month = month or today.month
        num_days = calendar.monthrange(target_year, target_month)[1]
        seed_days = [day for day in [1, 2, 3, 4, 5] if day <= num_days]

        seed_rows = [
            {
                "mood": "平静",
                "tags": "学习,放空",
                "color": "#8BB8FF",
                "text_content": "今天像一小片晴空，慢慢把心里的声音整理清楚。",
            },
            {
                "mood": "放松",
                "tags": "充电,宅家",
                "color": "#8FD7A5",
                "text_content": "给自己留了一点安静时间，像把窗户打开透了透气。",
            },
            {
                "mood": "期待",
                "tags": "元气满满,户外",
                "color": "#FFB35C",
                "text_content": "有一点新的期待冒出来，整个人也亮了一点。",
            },
            {
                "mood": "疲惫",
                "tags": "低电量,勿扰",
                "color": "#91A7B4",
                "text_content": "身体有点累，但我还是认真记下了今天的感受。",
            },
            {
                "mood": "满足",
                "tags": "美食,娱乐",
                "color": "#FFE08A",
                "text_content": "一点小小的满足感，让这一天有了温柔的收尾。",
            },
        ]

        created_dates = []
        skipped_dates = []
        for index, day in enumerate(seed_days):
            target_date_str = f"{target_year}-{target_month:02d}-{day:02d}"
            if self.get_checkin_by_date(user_id, target_date_str):
                skipped_dates.append(target_date_str)
                continue

            checkin_dt = datetime.datetime.combine(
                datetime.date(target_year, target_month, day),
                datetime.time(12, 0),
            )
            checkin_timestamp = int(checkin_dt.timestamp())
            payload = enrich_checkin_payload({
                "user_id": user_id,
                **seed_rows[index],
                "timestamp": checkin_timestamp,
                "updated_at": checkin_timestamp,
            })
            Checkin.create(**payload)
            created_dates.append(target_date_str)

        return {
            "created_count": len(created_dates),
            "created_dates": created_dates,
            "skipped_dates": skipped_dates,
            "target_total_days": len(seed_days),
            "year": target_year,
            "month": target_month,
        }

    def _prepare_checkin_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = enrich_checkin_payload(payload)
        if "image_urls" in data or "image_url" in data:
            image_urls = normalize_image_urls(data.get("image_urls"), data.get("image_url"))
            data["image_urls"] = dump_image_urls(image_urls)
            data["image_url"] = image_urls[0] if image_urls else None
        return data

    def create_checkin(self, user_id: str, data: CheckinBaseModel) -> Optional[Checkin]:
        """Creates a new checkin record."""
        try:
            payload = self._prepare_checkin_payload(data.model_dump(exclude_unset=True))
            checkin = Checkin.create(
                user_id=user_id,
                **payload
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
        update_data = self._prepare_checkin_payload(data.model_dump(exclude_unset=True))
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
        """Encrypt and store an uploaded check-in image outside the static root."""
        try:
            from model.private_media import private_media_table

            return private_media_table.store_upload(
                owner_user_id=user_id,
                media_type="checkin",
                upload=image_file,
            )
        except (OSError, ValueError) as exc:
            print(f"Error saving encrypted check-in image: {exc}")
            return None
            
    def update_image_url(self, checkin_id: str, image_url: str) -> bool:
        """Updates only the image_url for a given check-in."""
        checkin = self.get_checkin_by_id(checkin_id)
        if not checkin:
            return False
        image_urls = self._normalize_owned_image_urls(
            [image_url],
            checkin.user_id,
        )
        query = Checkin.update(
            image_url=image_urls[0] if image_urls else None,
            image_urls=dump_image_urls(image_urls),
            updated_at=int(time.time()),
        ).where(Checkin.id == checkin_id)
        rows_affected = query.execute()
        return rows_affected > 0

    def get_image_urls(self, checkin: Checkin) -> List[str]:
        return normalize_image_urls(
            getattr(checkin, "image_urls", None),
            getattr(checkin, "image_url", None),
        )

    def set_image_urls(self, checkin_id: str, image_urls: List[str]) -> Optional[Checkin]:
        checkin = self.get_checkin_by_id(checkin_id)
        if not checkin:
            return None
        urls = self._normalize_owned_image_urls(image_urls, checkin.user_id)
        if len(image_urls) > MAX_CHECKIN_IMAGES or len(urls) > MAX_CHECKIN_IMAGES:
            return None
        query = Checkin.update(
            image_url=urls[0] if urls else None,
            image_urls=dump_image_urls(urls),
            updated_at=int(time.time()),
        ).where(Checkin.id == checkin_id)
        rows_affected = query.execute()
        if rows_affected > 0:
            return self.get_checkin_by_id(checkin_id)
        return None

    def _normalize_owned_image_urls(
        self,
        image_urls: List[str],
        user_id: str,
    ) -> List[str]:
        from model.private_media import private_media_table

        normalized = []
        for value in normalize_image_urls(image_urls):
            normalized.append(
                private_media_table.normalize_owner_reference(value, user_id)
            )
        return normalize_image_urls(normalized)

    def append_image_urls(self, checkin_id: str, image_urls: List[str]) -> Optional[Checkin]:
        checkin = self.get_checkin_by_id(checkin_id)
        if not checkin:
            return None
        next_urls = self.get_image_urls(checkin) + normalize_image_urls(image_urls)
        if len(next_urls) > MAX_CHECKIN_IMAGES:
            return None
        return self.set_image_urls(checkin_id, next_urls)

    def replace_image_url(self, checkin_id: str, image_index: int, image_url: str) -> Optional[Checkin]:
        checkin = self.get_checkin_by_id(checkin_id)
        if not checkin:
            return None
        urls = self.get_image_urls(checkin)
        if image_index < 0 or image_index > len(urls) or image_index >= MAX_CHECKIN_IMAGES:
            return None
        if image_index == len(urls):
            urls.append(image_url)
        else:
            urls[image_index] = image_url
        return self.set_image_urls(checkin_id, urls)

    def delete_image_url(self, checkin_id: str, image_index: int) -> Optional[Checkin]:
        checkin = self.get_checkin_by_id(checkin_id)
        if not checkin:
            return None
        urls = self.get_image_urls(checkin)
        if image_index < 0 or image_index >= len(urls):
            return None
        urls.pop(image_index)
        return self.set_image_urls(checkin_id, urls)

# ---------------------------------------------------
# 4. Helper Function & Instantiation
# ---------------------------------------------------

def model_to_dict(model_instance: Model) -> Dict:
    """A helper function to convert a Peewee model instance to a dictionary."""
    mood_meta = get_mood_meta(getattr(model_instance, "mood_id", None) or model_instance.mood)
    color_meta = get_color_meta(getattr(model_instance, "color_id", None) or model_instance.color)
    status_items = build_status_meta_from_tags(
        model_instance.tags,
        getattr(model_instance, "status_ids", None),
    )
    status_ids = load_list(getattr(model_instance, "status_ids", None))
    if not status_ids and status_items:
        status_ids = [item["id"] for item in status_items]
    status_families = load_list(getattr(model_instance, "status_families", None))
    if not status_families and status_items:
        status_families = list(dict.fromkeys(item["family"] for item in status_items))
    image_urls = normalize_image_urls(
        getattr(model_instance, "image_urls", None),
        getattr(model_instance, "image_url", None),
    )
    from model.private_media import private_media_table
    signed_image_urls = [
        private_media_table.signed_url(image_url)
        for image_url in image_urls
    ]

    return {
        "id": model_instance.id,
        "user_id": model_instance.user_id,
        "mood": model_instance.mood,
        "mood_id": getattr(model_instance, "mood_id", None) or mood_meta.get("id"),
        "mood_icon": mood_meta.get("icon"),
        "mood_family": getattr(model_instance, "mood_family", None) or mood_meta.get("family"),
        "mood_valence": getattr(model_instance, "mood_valence", None) or mood_meta.get("valence"),
        "mood_energy": getattr(model_instance, "mood_energy", None) or mood_meta.get("energy"),
        "color": model_instance.color,
        "color_id": getattr(model_instance, "color_id", None) or color_meta.get("id"),
        "color_label": getattr(model_instance, "color_label", None) or color_meta.get("label"),
        "color_group": getattr(model_instance, "color_group", None) or color_meta.get("group"),
        "color_tone": getattr(model_instance, "color_tone", None) or color_meta.get("tone"),
        "color_description": getattr(model_instance, "color_description", None) or color_meta.get("description"),
        "tags": model_instance.tags,
        "status_ids": status_ids,
        "status_families": status_families,
        "status_items": status_items,
        "text_content": model_instance.text_content,
        "image_url": signed_image_urls[0] if signed_image_urls else None,
        "image_urls": signed_image_urls,
        "location_name": getattr(model_instance, "location_name", None),
        "location_address": getattr(model_instance, "location_address", None),
        "location_latitude": getattr(model_instance, "location_latitude", None),
        "location_longitude": getattr(model_instance, "location_longitude", None),
        "timestamp": model_instance.timestamp,
        "updated_at": model_instance.updated_at
    }

checkin_table = CheckinTable(status_db)
