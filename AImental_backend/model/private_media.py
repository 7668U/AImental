import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import UploadFile
from peewee import CharField, DateTimeField, Model

from db import user_db
from security.data_encryption import (
    decrypt_bytes,
    encrypt_bytes,
    sign_url_payload,
    verify_url_signature,
)


PRIVATE_MEDIA_ROOT = Path(
    os.getenv("PRIVATE_MEDIA_ROOT", "private_media")
).resolve()
PRIVATE_MEDIA_URL_TTL_SECONDS = int(
    os.getenv("PRIVATE_MEDIA_URL_TTL_SECONDS", "900")
)
MAX_PRIVATE_IMAGE_BYTES = int(
    os.getenv("MAX_PRIVATE_IMAGE_BYTES", str(8 * 1024 * 1024))
)
MEDIA_REFERENCE_PREFIX = "media:"
ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}


class PrivateMedia(Model):
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    owner_user_id = CharField(max_length=36, index=True)
    media_type = CharField(max_length=32)
    content_type = CharField(max_length=64)
    encrypted_path = CharField(max_length=255, unique=True)
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        database = user_db
        table_name = "private_media"


def _looks_like_supported_image(data: bytes, content_type: str) -> bool:
    if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        return False
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return content_type == "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return content_type == "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return content_type == "image/gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return content_type == "image/webp"
    return False


def media_reference(media_id: str) -> str:
    return f"{MEDIA_REFERENCE_PREFIX}{media_id}"


def extract_media_id(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    raw = str(value).strip()
    if raw.startswith(MEDIA_REFERENCE_PREFIX):
        candidate = raw[len(MEDIA_REFERENCE_PREFIX) :]
        return candidate or None

    parsed = urlparse(raw)
    marker = "/api/v1/private-media/"
    if marker in parsed.path:
        return parsed.path.split(marker, 1)[1].split("/", 1)[0] or None
    return None


class PrivateMediaTable:
    def __init__(self, db_connection):
        self.db = db_connection
        self.db.create_tables([PrivateMedia], safe=True)
        PRIVATE_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

    def _relative_path(self, media_id: str) -> Path:
        return Path(media_id[:2]) / f"{media_id}.bin"

    def _absolute_path(self, relative_path: str | Path) -> Path:
        resolved = (PRIVATE_MEDIA_ROOT / relative_path).resolve()
        if PRIVATE_MEDIA_ROOT not in resolved.parents:
            raise ValueError("Private media path escaped its storage root.")
        return resolved

    def store_image_bytes(
        self,
        *,
        owner_user_id: str,
        media_type: str,
        content_type: str,
        data: bytes,
    ) -> str:
        if not data or len(data) > MAX_PRIVATE_IMAGE_BYTES:
            raise ValueError("Image is empty or exceeds the configured size limit.")
        if not _looks_like_supported_image(data, content_type):
            raise ValueError("Unsupported or mismatched image format.")

        media_id = str(uuid.uuid4())
        relative_path = self._relative_path(media_id)
        absolute_path = self._absolute_path(relative_path)
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        purpose = f"private-media:{media_id}:{owner_user_id}:{media_type}"
        encrypted = encrypt_bytes(data, purpose)
        temporary_path = absolute_path.with_suffix(".tmp")
        temporary_path.write_bytes(encrypted)
        os.replace(temporary_path, absolute_path)

        try:
            PrivateMedia.create(
                id=media_id,
                owner_user_id=owner_user_id,
                media_type=media_type,
                content_type=content_type,
                encrypted_path=relative_path.as_posix(),
            )
        except Exception:
            absolute_path.unlink(missing_ok=True)
            raise
        return media_reference(media_id)

    def store_upload(
        self,
        *,
        owner_user_id: str,
        media_type: str,
        upload: UploadFile,
    ) -> str:
        try:
            data = upload.file.read(MAX_PRIVATE_IMAGE_BYTES + 1)
            return self.store_image_bytes(
                owner_user_id=owner_user_id,
                media_type=media_type,
                content_type=(upload.content_type or "").lower(),
                data=data,
            )
        finally:
            upload.file.close()

    def read(self, media_id: str) -> tuple[bytes, str]:
        record = PrivateMedia.get_or_none(PrivateMedia.id == media_id)
        if not record:
            raise FileNotFoundError(media_id)
        encrypted = self._absolute_path(record.encrypted_path).read_bytes()
        purpose = (
            f"private-media:{record.id}:{record.owner_user_id}:{record.media_type}"
        )
        return decrypt_bytes(encrypted, purpose), record.content_type

    def belongs_to(self, media_id: str, owner_user_id: str) -> bool:
        return (
            PrivateMedia.select()
            .where(
                (PrivateMedia.id == media_id)
                & (PrivateMedia.owner_user_id == owner_user_id)
            )
            .exists()
        )

    def normalize_owner_reference(
        self,
        value: Optional[str],
        owner_user_id: str,
    ) -> Optional[str]:
        media_id = extract_media_id(value)
        if not media_id:
            return value
        if not self.belongs_to(media_id, owner_user_id):
            raise ValueError("Private media does not belong to the current user.")
        return media_reference(media_id)

    def signed_url(self, value: Optional[str]) -> Optional[str]:
        media_id = extract_media_id(value)
        if not media_id:
            return value
        expires = int(time.time()) + PRIVATE_MEDIA_URL_TTL_SECONDS
        payload = f"{media_id}:{expires}"
        signature = sign_url_payload(payload)
        return (
            f"/api/v1/private-media/{media_id}"
            f"?expires={expires}&signature={signature}"
        )

    def verify_signed_request(
        self,
        media_id: str,
        expires: int,
        signature: str,
    ) -> bool:
        if expires < int(time.time()):
            return False
        return verify_url_signature(f"{media_id}:{expires}", signature)


private_media_table = PrivateMediaTable(user_db)
