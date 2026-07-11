# models/user.py

import uuid
from datetime import datetime, date
from typing import Optional

from peewee import Model, CharField, IntegerField, DateTimeField, BooleanField, ForeignKeyField
from pydantic import BaseModel, Field
from fastapi import UploadFile

from db import user_db
from privacy_policy import (
    PRIVACY_POLICY_VERSION,
    get_privacy_policy_digest,
)
from security.data_encryption import (
    EncryptedDateField,
    EncryptedIntegerField,
    EncryptedTextField,
    blind_index,
)

DEFAULT_AVATAR_URL = "/static/avatars/default.png"

class User(Model):
    """The Peewee Model for the 'users' table."""
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    openid = EncryptedTextField(purpose="users.openid")
    openid_lookup = CharField(max_length=64, unique=True, index=True, null=True)
    nickname = EncryptedTextField(purpose="users.nickname", null=True)
    avatar_url = EncryptedTextField(purpose="users.avatar_url", null=True)
    has_unlocked_community = BooleanField(default=False, help_text="是否已分享解锁了社区")
    gender = EncryptedIntegerField(purpose="users.gender", default=0, null=True)
    birthday = EncryptedDateField(purpose="users.birthday", null=True)
    allow_ai_read_data = BooleanField(default=False)
    privacy_consent_version = CharField(max_length=32, null=True)
    privacy_policy_digest = CharField(max_length=64, null=True)
    privacy_consented_at = DateTimeField(null=True)
    privacy_consent_withdrawn_at = DateTimeField(null=True)
    status = IntegerField(default=1)
    created_at = DateTimeField(default=datetime.now)
    last_login_at = DateTimeField(default=datetime.now)

    class Meta:
        database = user_db
        table_name = 'users'


class PrivacyConsent(Model):
    """Append-only privacy consent audit record."""

    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    user = ForeignKeyField(
        User,
        backref="privacy_consents",
        field="id",
        on_delete="CASCADE",
    )
    policy_version = CharField(max_length=32)
    policy_digest = CharField(max_length=64)
    action = CharField(max_length=16)
    source = CharField(max_length=64)
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        database = user_db
        table_name = "privacy_consents"
        indexes = ((("user", "created_at"), False),)


class UserModel(BaseModel):
    """Public API representation. The WeChat openid is never returned."""
    id: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    gender: Optional[int] = Field(None, description="0: 保密, 1: 男, 2: 女")
    birthday: Optional[date] = None
    allow_ai_read_data: bool
    privacy_consent_version: Optional[str] = None
    privacy_consented_at: Optional[datetime] = None
    status: int
    created_at: datetime
    last_login_at: datetime
    
    class Config:
        from_attributes = True


class UserTable:
    """Encapsulates all database operations for the 'users' table."""
    def __init__(self, db_connection):
        self.db = db_connection
        if not self.db.table_exists(User._meta.table_name):
            self.db.create_tables([User], safe=True)
        self._ensure_security_schema()
        self.db.create_tables([PrivacyConsent], safe=True)
        self._backfill_openid_lookups()

    def _ensure_security_schema(self):
        existing_columns = {
            column.name for column in self.db.get_columns(User._meta.table_name)
        }
        migrations = {
            "openid_lookup": "VARCHAR(64)",
            "privacy_consent_version": "VARCHAR(32)",
            "privacy_policy_digest": "VARCHAR(64)",
            "privacy_consented_at": "DATETIME",
            "privacy_consent_withdrawn_at": "DATETIME",
        }
        for column_name, column_type in migrations.items():
            if column_name not in existing_columns:
                self.db.execute_sql(
                    f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"
                )
        self.db.execute_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS users_openid_lookup "
            "ON users(openid_lookup)"
        )

    def _backfill_openid_lookups(self):
        pending_users = User.select().where(
            (User.openid_lookup.is_null(True)) | (User.openid_lookup == "")
        )
        for user in pending_users:
            if not user.openid:
                continue
            user.openid_lookup = blind_index(user.openid, "users.openid")
            user.save(only=[User.openid_lookup])

    def create_user(self, openid: str, nickname: str, avatar_url: Optional[str] = None) -> Optional[User]:
        lookup = blind_index(openid, "users.openid")
        if User.get_or_none(User.openid_lookup == lookup):
            return None

        user = User.create(
            id=str(uuid.uuid4()),
            openid=openid,
            openid_lookup=lookup,
            nickname=nickname,
            avatar_url=avatar_url or DEFAULT_AVATAR_URL
        )
        return user

    def get_user_by_openid(self, openid: str) -> Optional[User]:
        lookup = blind_index(openid, "users.openid")
        user = User.get_or_none(User.openid_lookup == lookup)
        if user:
            return user

        # Compatibility path for a database that has not run the migration yet.
        for candidate in User.select().where(User.openid_lookup.is_null(True)):
            if candidate.openid == openid:
                candidate.openid_lookup = lookup
                candidate.save(only=[User.openid_lookup])
                return candidate
        return None

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        return User.get_or_none(User.id == user_id)

    def get_or_create_test_user(self, user_id: str) -> tuple[User, bool]:
        existing = self.get_user_by_id(user_id)
        if existing:
            return existing, False
        openid = f"test_openid_{user_id}"
        return (
            User.create(
                id=user_id,
                openid=openid,
                openid_lookup=blind_index(openid, "users.openid"),
                nickname=f"测试用户-{user_id[:6]}",
                avatar_url=DEFAULT_AVATAR_URL,
            ),
            True,
        )

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

        try:
            from model.private_media import private_media_table

            reference = private_media_table.store_upload(
                owner_user_id=user_id,
                media_type="avatar",
                upload=image_file,
            )
        except (OSError, ValueError) as exc:
            print(f"Error saving encrypted avatar: {exc}")
            return None

        user.avatar_url = reference
        user.save(only=[User.avatar_url])
        return private_media_table.signed_url(reference)
        
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

    def update_ai_read_permission(self, user_id: str, allow: bool) -> bool:
        query = User.update({User.allow_ai_read_data: allow}).where(User.id == user_id)
        rows_updated = query.execute()
        return rows_updated > 0

    def has_current_privacy_consent(self, user_id: str) -> bool:
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        return bool(
            user.privacy_consent_version == PRIVACY_POLICY_VERSION
            and user.privacy_policy_digest == get_privacy_policy_digest()
            and user.privacy_consented_at
            and not user.privacy_consent_withdrawn_at
        )

    def accept_privacy_consent(
        self,
        user_id: str,
        policy_version: str,
        source: str,
    ) -> bool:
        user = self.get_user_by_id(user_id)
        if not user or policy_version != PRIVACY_POLICY_VERSION:
            return False

        digest = get_privacy_policy_digest()
        if self.has_current_privacy_consent(user_id):
            return True

        now = datetime.now()
        with self.db.atomic():
            user.privacy_consent_version = policy_version
            user.privacy_policy_digest = digest
            user.privacy_consented_at = now
            user.privacy_consent_withdrawn_at = None
            user.save(
                only=[
                    User.privacy_consent_version,
                    User.privacy_policy_digest,
                    User.privacy_consented_at,
                    User.privacy_consent_withdrawn_at,
                ]
            )
            PrivacyConsent.create(
                user=user_id,
                policy_version=policy_version,
                policy_digest=digest,
                action="accepted",
                source=source[:64],
                created_at=now,
            )
        return True

    def withdraw_privacy_consent(self, user_id: str, source: str) -> bool:
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        now = datetime.now()
        with self.db.atomic():
            user.privacy_consent_withdrawn_at = now
            user.save(only=[User.privacy_consent_withdrawn_at])
            PrivacyConsent.create(
                user=user_id,
                policy_version=user.privacy_consent_version or PRIVACY_POLICY_VERSION,
                policy_digest=user.privacy_policy_digest or get_privacy_policy_digest(),
                action="withdrawn",
                source=source[:64],
                created_at=now,
            )
        return True

    def serialize_user(self, user: User) -> dict:
        from model.private_media import private_media_table

        return {
            "id": user.id,
            "nickname": user.nickname,
            "avatar_url": private_media_table.signed_url(user.avatar_url),
            "gender": user.gender,
            "birthday": user.birthday,
            "allow_ai_read_data": user.allow_ai_read_data,
            "privacy_consent_version": user.privacy_consent_version,
            "privacy_consented_at": user.privacy_consented_at,
            "status": user.status,
            "created_at": user.created_at,
            "last_login_at": user.last_login_at,
        }


user_table = UserTable(user_db)
