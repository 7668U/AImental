import base64
import binascii
import hashlib
import json
import os
import secrets
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote, unquote, urlencode, urlparse

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
PRIVATE_MEDIA_DIRECT_UPLOAD_TTL_SECONDS = int(
    os.getenv("PRIVATE_MEDIA_DIRECT_UPLOAD_TTL_SECONDS", "300")
)
MAX_PRIVATE_IMAGE_BYTES = int(
    os.getenv("MAX_PRIVATE_IMAGE_BYTES", str(8 * 1024 * 1024))
)
PRIVATE_MEDIA_STORAGE_BACKEND = os.getenv(
    "PRIVATE_MEDIA_STORAGE_BACKEND",
    "local",
).strip().lower()
PRIVATE_MEDIA_COS_REGION = os.getenv("PRIVATE_MEDIA_COS_REGION", "").strip()
PRIVATE_MEDIA_COS_BUCKET = os.getenv("PRIVATE_MEDIA_COS_BUCKET", "").strip()
PRIVATE_MEDIA_COS_SECRET_ID = os.getenv(
    "PRIVATE_MEDIA_COS_SECRET_ID",
    "",
).strip()
PRIVATE_MEDIA_COS_SECRET_KEY = os.getenv(
    "PRIVATE_MEDIA_COS_SECRET_KEY",
    "",
).strip()
PRIVATE_MEDIA_COS_SESSION_TOKEN = os.getenv(
    "PRIVATE_MEDIA_COS_SESSION_TOKEN",
    "",
).strip()
PRIVATE_MEDIA_COS_PREFIX = os.getenv(
    "PRIVATE_MEDIA_COS_PREFIX",
    "private-media/v1",
).strip().strip("/")
PRIVATE_MEDIA_CDN_BASE_URL = os.getenv(
    "PRIVATE_MEDIA_CDN_BASE_URL",
    "",
).strip().rstrip("/")
PRIVATE_MEDIA_CDN_AUTH_ALGORITHM = os.getenv(
    "PRIVATE_MEDIA_CDN_AUTH_ALGORITHM",
    "sha256",
).strip().lower()
PRIVATE_MEDIA_CDN_AUTH_SIGN_PARAM = os.getenv(
    "PRIVATE_MEDIA_CDN_AUTH_SIGN_PARAM",
    "sign",
).strip()
PRIVATE_MEDIA_CDN_AUTH_UID = os.getenv(
    "PRIVATE_MEDIA_CDN_AUTH_UID",
    "0",
).strip()
PRIVATE_MEDIA_CDN_AUTH_PRIMARY_KEY = os.getenv(
    "PRIVATE_MEDIA_CDN_AUTH_PRIMARY_KEY",
    "",
).strip()
PRIVATE_MEDIA_CDN_AUTH_BACKUP_KEY = os.getenv(
    "PRIVATE_MEDIA_CDN_AUTH_BACKUP_KEY",
    "",
).strip()

MEDIA_REFERENCE_PREFIX = "media:"
ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}
STORAGE_BACKENDS = {"local", "cos"}


class PrivateMedia(Model):
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    owner_user_id = CharField(max_length=36, index=True)
    media_type = CharField(max_length=32)
    content_type = CharField(max_length=64)
    encrypted_path = CharField(max_length=255, unique=True)
    storage_backend = CharField(max_length=16, default="local")
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        database = user_db
        table_name = "private_media"


def _looks_like_supported_image(header: bytes, content_type: str) -> bool:
    if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        return False
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return content_type == "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return content_type == "image/jpeg"
    if header[:6] in (b"GIF87a", b"GIF89a"):
        return content_type == "image/gif"
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
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
    api_marker = "/api/v1/private-media/"
    if api_marker in parsed.path:
        return parsed.path.split(api_marker, 1)[1].split("/", 1)[0] or None

    cos_marker = f"/{PRIVATE_MEDIA_COS_PREFIX}/"
    if PRIVATE_MEDIA_COS_PREFIX and cos_marker in unquote(parsed.path):
        candidate = unquote(parsed.path).split(cos_marker, 1)[1].split("/")[-1]
        try:
            return str(uuid.UUID(candidate))
        except (ValueError, TypeError):
            return None
    return None


class PrivateMediaTable:
    def __init__(self, db_connection):
        self.db = db_connection
        self.db.create_tables([PrivateMedia], safe=True)
        self._ensure_storage_backend_column()
        PRIVATE_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
        self._cos_client = None
        self._validate_storage_backend()

    def _ensure_storage_backend_column(self) -> None:
        columns = {
            column.name
            for column in self.db.get_columns(PrivateMedia._meta.table_name)
        }
        if "storage_backend" not in columns:
            self.db.execute_sql(
                "ALTER TABLE private_media "
                "ADD COLUMN storage_backend TEXT NOT NULL DEFAULT 'local'"
            )

    def _validate_storage_backend(self) -> None:
        if PRIVATE_MEDIA_STORAGE_BACKEND not in STORAGE_BACKENDS:
            raise RuntimeError(
                "PRIVATE_MEDIA_STORAGE_BACKEND must be 'local' or 'cos'."
            )
        if PRIVATE_MEDIA_STORAGE_BACKEND != "cos":
            return
        missing = [
            name
            for name, value in (
                ("PRIVATE_MEDIA_COS_REGION", PRIVATE_MEDIA_COS_REGION),
                ("PRIVATE_MEDIA_COS_BUCKET", PRIVATE_MEDIA_COS_BUCKET),
                ("PRIVATE_MEDIA_COS_SECRET_ID", PRIVATE_MEDIA_COS_SECRET_ID),
                ("PRIVATE_MEDIA_COS_SECRET_KEY", PRIVATE_MEDIA_COS_SECRET_KEY),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Private COS storage is enabled but configuration is missing: "
                + ", ".join(missing)
            )
        if PRIVATE_MEDIA_CDN_BASE_URL:
            if PRIVATE_MEDIA_CDN_AUTH_ALGORITHM not in {"md5", "sha256"}:
                raise RuntimeError(
                    "PRIVATE_MEDIA_CDN_AUTH_ALGORITHM must be md5 or sha256."
                )
            if not PRIVATE_MEDIA_CDN_AUTH_SIGN_PARAM:
                raise RuntimeError(
                    "PRIVATE_MEDIA_CDN_AUTH_SIGN_PARAM cannot be empty."
                )
            if not (
                PRIVATE_MEDIA_CDN_AUTH_PRIMARY_KEY
                or PRIVATE_MEDIA_CDN_AUTH_BACKUP_KEY
            ):
                raise RuntimeError(
                    "Private media CDN is enabled but no auth key is configured."
                )

    def _get_cos_client(self):
        if self._cos_client is not None:
            return self._cos_client
        try:
            from qcloud_cos import CosConfig, CosS3Client
        except ImportError as exc:
            raise RuntimeError(
                "cos-python-sdk-v5 is required for private COS storage."
            ) from exc

        config = CosConfig(
            Region=PRIVATE_MEDIA_COS_REGION,
            SecretId=PRIVATE_MEDIA_COS_SECRET_ID,
            SecretKey=PRIVATE_MEDIA_COS_SECRET_KEY,
            Token=PRIVATE_MEDIA_COS_SESSION_TOKEN or None,
            Scheme="https",
        )
        self._cos_client = CosS3Client(config)
        return self._cos_client

    def _relative_path(self, media_id: str) -> Path:
        return Path(media_id[:2]) / f"{media_id}.bin"

    def _absolute_path(self, relative_path: str | Path) -> Path:
        resolved = (PRIVATE_MEDIA_ROOT / relative_path).resolve()
        if resolved != PRIVATE_MEDIA_ROOT and PRIVATE_MEDIA_ROOT not in resolved.parents:
            raise ValueError("Private media path escaped its storage root.")
        return resolved

    def _cos_object_key(self, media_id: str) -> str:
        return f"{PRIVATE_MEDIA_COS_PREFIX}/{media_id[:2]}/{media_id}"

    def _put_cos_object(
        self,
        *,
        object_key: str,
        body,
        content_type: str,
    ) -> None:
        self._get_cos_client().put_object(
            Bucket=PRIVATE_MEDIA_COS_BUCKET,
            Key=object_key,
            Body=body,
            ACL="private",
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )

    def _direct_upload_token(
        self,
        *,
        media_id: str,
        owner_user_id: str,
        media_type: str,
        content_type: str,
        size: int,
        expires: int,
    ) -> str:
        payload = {
            "media_id": media_id,
            "owner_user_id": owner_user_id,
            "media_type": media_type,
            "content_type": content_type,
            "size": size,
            "expires": expires,
        }
        encoded_payload = base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        ).decode("ascii").rstrip("=")
        signature = sign_url_payload(f"direct-upload:{encoded_payload}")
        return f"{encoded_payload}.{signature}"

    def _decode_direct_upload_token(self, token: str) -> dict:
        try:
            encoded_payload, signature = token.split(".", 1)
            if not verify_url_signature(
                f"direct-upload:{encoded_payload}",
                signature,
            ):
                raise ValueError("Direct upload token is invalid.")
            padded = encoded_payload + ("=" * (-len(encoded_payload) % 4))
            payload = json.loads(
                base64.urlsafe_b64decode(padded).decode("utf-8")
            )
        except (
            ValueError,
            TypeError,
            UnicodeDecodeError,
            binascii.Error,
            json.JSONDecodeError,
        ) as exc:
            raise ValueError("Direct upload token is invalid.") from exc

        if not isinstance(payload, dict):
            raise ValueError("Direct upload token is invalid.")
        required = {
            "media_id",
            "owner_user_id",
            "media_type",
            "content_type",
            "size",
            "expires",
        }
        if not required.issubset(payload):
            raise ValueError("Direct upload token is incomplete.")
        if int(payload["expires"]) < int(time.time()):
            raise ValueError("Direct upload token has expired.")
        return payload

    def prepare_direct_upload(
        self,
        *,
        owner_user_id: str,
        media_type: str,
        content_type: str,
        size: int,
    ) -> dict:
        if PRIVATE_MEDIA_STORAGE_BACKEND != "cos":
            raise RuntimeError(
                "Direct COS upload is unavailable when private media storage is local."
            )
        if media_type not in {"avatar", "checkin"}:
            raise ValueError("Unsupported private media type.")

        normalized_content_type = content_type.lower().strip()
        if normalized_content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
            raise ValueError("Unsupported image content type.")
        if size <= 0 or size > MAX_PRIVATE_IMAGE_BYTES:
            raise ValueError("Image is empty or exceeds the configured size limit.")

        media_id = str(uuid.uuid4())
        object_key = self._cos_object_key(media_id)
        expires = int(time.time()) + PRIVATE_MEDIA_DIRECT_UPLOAD_TTL_SECONDS
        headers = {
            "Content-Type": normalized_content_type,
            "x-cos-server-side-encryption": "AES256",
        }
        return {
            "upload_token": self._direct_upload_token(
                media_id=media_id,
                owner_user_id=owner_user_id,
                media_type=media_type,
                content_type=normalized_content_type,
                size=size,
                expires=expires,
            ),
            "upload_url": self._get_cos_client().get_presigned_url(
                Bucket=PRIVATE_MEDIA_COS_BUCKET,
                Key=object_key,
                Method="PUT",
                Expired=PRIVATE_MEDIA_DIRECT_UPLOAD_TTL_SECONDS,
                Headers=headers,
            ),
            "headers": headers,
            "expires_at": expires,
            "max_size": MAX_PRIVATE_IMAGE_BYTES,
        }

    def confirm_direct_upload(
        self,
        *,
        token: str,
        owner_user_id: str,
        media_type: str,
    ) -> str:
        if PRIVATE_MEDIA_STORAGE_BACKEND != "cos":
            raise RuntimeError(
                "Direct COS upload is unavailable when private media storage is local."
            )
        payload = self._decode_direct_upload_token(token)
        if payload["owner_user_id"] != owner_user_id:
            raise ValueError("Direct upload does not belong to the current user.")
        if payload["media_type"] != media_type:
            raise ValueError("Direct upload media type does not match.")

        media_id = str(payload["media_id"])
        content_type = str(payload["content_type"]).lower()
        expected_size = int(payload["size"])
        object_key = self._cos_object_key(media_id)
        existing = PrivateMedia.get_or_none(PrivateMedia.id == media_id)
        if existing:
            if (
                existing.owner_user_id != owner_user_id
                or existing.media_type != media_type
            ):
                raise ValueError("Direct upload has already been claimed.")
            return media_reference(media_id)

        try:
            metadata = self._get_cos_client().head_object(
                Bucket=PRIVATE_MEDIA_COS_BUCKET,
                Key=object_key,
            )
        except Exception as exc:
            raise ValueError("The COS object was not uploaded.") from exc

        actual_size = int(
            metadata.get("Content-Length")
            or metadata.get("content-length")
            or 0
        )
        actual_content_type = (
            metadata.get("Content-Type")
            or metadata.get("content-type")
            or ""
        ).lower()
        if actual_size != expected_size or actual_content_type != content_type:
            self._delete_storage_object(
                storage_backend="cos",
                storage_path=object_key,
            )
            raise ValueError("The uploaded object metadata does not match.")

        return self._create_record(
            media_id=media_id,
            owner_user_id=owner_user_id,
            media_type=media_type,
            content_type=content_type,
            storage_backend="cos",
            storage_path=object_key,
        )

    def _delete_storage_object(
        self,
        *,
        storage_backend: str,
        storage_path: str,
    ) -> None:
        if storage_backend == "cos":
            self._get_cos_client().delete_object(
                Bucket=PRIVATE_MEDIA_COS_BUCKET,
                Key=storage_path,
            )
            return
        self._absolute_path(storage_path).unlink(missing_ok=True)

    def _create_record(
        self,
        *,
        media_id: str,
        owner_user_id: str,
        media_type: str,
        content_type: str,
        storage_backend: str,
        storage_path: str,
    ) -> str:
        try:
            PrivateMedia.create(
                id=media_id,
                owner_user_id=owner_user_id,
                media_type=media_type,
                content_type=content_type,
                encrypted_path=storage_path,
                storage_backend=storage_backend,
            )
        except Exception:
            self._delete_storage_object(
                storage_backend=storage_backend,
                storage_path=storage_path,
            )
            raise
        return media_reference(media_id)

    def store_image_bytes(
        self,
        *,
        owner_user_id: str,
        media_type: str,
        content_type: str,
        data: bytes,
    ) -> str:
        normalized_content_type = content_type.lower()
        if not data or len(data) > MAX_PRIVATE_IMAGE_BYTES:
            raise ValueError("Image is empty or exceeds the configured size limit.")
        if not _looks_like_supported_image(data[:16], normalized_content_type):
            raise ValueError("Unsupported or mismatched image format.")

        media_id = str(uuid.uuid4())
        if PRIVATE_MEDIA_STORAGE_BACKEND == "cos":
            object_key = self._cos_object_key(media_id)
            self._put_cos_object(
                object_key=object_key,
                body=data,
                content_type=normalized_content_type,
            )
            return self._create_record(
                media_id=media_id,
                owner_user_id=owner_user_id,
                media_type=media_type,
                content_type=normalized_content_type,
                storage_backend="cos",
                storage_path=object_key,
            )

        relative_path = self._relative_path(media_id)
        absolute_path = self._absolute_path(relative_path)
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        purpose = f"private-media:{media_id}:{owner_user_id}:{media_type}"
        encrypted = encrypt_bytes(data, purpose)
        temporary_path = absolute_path.with_suffix(".tmp")
        temporary_path.write_bytes(encrypted)
        os.replace(temporary_path, absolute_path)
        return self._create_record(
            media_id=media_id,
            owner_user_id=owner_user_id,
            media_type=media_type,
            content_type=normalized_content_type,
            storage_backend="local",
            storage_path=relative_path.as_posix(),
        )

    def store_upload(
        self,
        *,
        owner_user_id: str,
        media_type: str,
        upload: UploadFile,
    ) -> str:
        content_type = (upload.content_type or "").lower()
        try:
            upload.file.seek(0, os.SEEK_END)
            size = upload.file.tell()
            upload.file.seek(0)
            header = upload.file.read(16)
            upload.file.seek(0)
            if not size or size > MAX_PRIVATE_IMAGE_BYTES:
                raise ValueError(
                    "Image is empty or exceeds the configured size limit."
                )
            if not _looks_like_supported_image(header, content_type):
                raise ValueError("Unsupported or mismatched image format.")

            if PRIVATE_MEDIA_STORAGE_BACKEND == "cos":
                media_id = str(uuid.uuid4())
                object_key = self._cos_object_key(media_id)
                self._put_cos_object(
                    object_key=object_key,
                    body=upload.file,
                    content_type=content_type,
                )
                return self._create_record(
                    media_id=media_id,
                    owner_user_id=owner_user_id,
                    media_type=media_type,
                    content_type=content_type,
                    storage_backend="cos",
                    storage_path=object_key,
                )

            data = upload.file.read(MAX_PRIVATE_IMAGE_BYTES + 1)
            return self.store_image_bytes(
                owner_user_id=owner_user_id,
                media_type=media_type,
                content_type=content_type,
                data=data,
            )
        finally:
            upload.file.close()

    def read(self, media_id: str) -> tuple[bytes, str]:
        record = PrivateMedia.get_or_none(PrivateMedia.id == media_id)
        if not record:
            raise FileNotFoundError(media_id)

        if record.storage_backend == "cos":
            response = self._get_cos_client().get_object(
                Bucket=PRIVATE_MEDIA_COS_BUCKET,
                Key=record.encrypted_path,
            )
            content = response["Body"].get_raw_stream().read(
                MAX_PRIVATE_IMAGE_BYTES + 1
            )
            if len(content) > MAX_PRIVATE_IMAGE_BYTES:
                raise OSError("Private media object exceeds the configured limit.")
            return content, record.content_type

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

    def exists(self, value: Optional[str]) -> bool:
        media_id = extract_media_id(value)
        if not media_id:
            return False
        return PrivateMedia.select().where(PrivateMedia.id == media_id).exists()

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

    def _cdn_signed_url(self, record: PrivateMedia) -> str:
        signing_key = (
            PRIVATE_MEDIA_CDN_AUTH_PRIMARY_KEY
            or PRIVATE_MEDIA_CDN_AUTH_BACKUP_KEY
        )
        uri = "/" + record.encrypted_path.lstrip("/")
        encoded_uri = quote(uri, safe="/:@-._~")
        timestamp = int(time.time())
        random_value = secrets.token_hex(8)
        signing_payload = (
            f"{uri}-{timestamp}-{random_value}-"
            f"{PRIVATE_MEDIA_CDN_AUTH_UID}-{signing_key}"
        )
        digest = hashlib.new(
            PRIVATE_MEDIA_CDN_AUTH_ALGORITHM,
            signing_payload.encode("utf-8"),
        ).hexdigest()
        signature = (
            f"{timestamp}-{random_value}-"
            f"{PRIVATE_MEDIA_CDN_AUTH_UID}-{digest}"
        )
        query = urlencode({PRIVATE_MEDIA_CDN_AUTH_SIGN_PARAM: signature})
        return f"{PRIVATE_MEDIA_CDN_BASE_URL}{encoded_uri}?{query}"

    def signed_url(self, value: Optional[str]) -> Optional[str]:
        media_id = extract_media_id(value)
        if not media_id:
            return value
        record = PrivateMedia.get_or_none(PrivateMedia.id == media_id)
        if not record:
            return None

        if record.storage_backend == "cos":
            if PRIVATE_MEDIA_CDN_BASE_URL:
                return self._cdn_signed_url(record)
            return self._get_cos_client().get_presigned_url(
                Bucket=PRIVATE_MEDIA_COS_BUCKET,
                Key=record.encrypted_path,
                Method="GET",
                Expired=PRIVATE_MEDIA_URL_TTL_SECONDS,
            )

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

    def migrate_local_record_to_cos(
        self,
        record: PrivateMedia,
        *,
        remove_local: bool = True,
    ) -> bool:
        if PRIVATE_MEDIA_STORAGE_BACKEND != "cos":
            raise RuntimeError(
                "Set PRIVATE_MEDIA_STORAGE_BACKEND=cos before migrating media."
            )
        if record.storage_backend != "local":
            return False

        local_path = self._absolute_path(record.encrypted_path)
        encrypted = local_path.read_bytes()
        purpose = (
            f"private-media:{record.id}:{record.owner_user_id}:{record.media_type}"
        )
        content = decrypt_bytes(encrypted, purpose)
        object_key = self._cos_object_key(record.id)
        self._put_cos_object(
            object_key=object_key,
            body=content,
            content_type=record.content_type,
        )

        try:
            with self.db.atomic():
                record.encrypted_path = object_key
                record.storage_backend = "cos"
                record.save(
                    only=[
                        PrivateMedia.encrypted_path,
                        PrivateMedia.storage_backend,
                    ]
                )
        except Exception:
            self._delete_storage_object(
                storage_backend="cos",
                storage_path=object_key,
            )
            raise

        if remove_local:
            local_path.unlink(missing_ok=True)
        return True

    def delete(
        self,
        value: Optional[str],
        *,
        owner_user_id: Optional[str] = None,
    ) -> bool:
        media_id = extract_media_id(value)
        if not media_id:
            return False
        record = PrivateMedia.get_or_none(PrivateMedia.id == media_id)
        if not record:
            return False
        if owner_user_id and record.owner_user_id != owner_user_id:
            raise ValueError("Private media does not belong to the current user.")

        self._delete_storage_object(
            storage_backend=record.storage_backend,
            storage_path=record.encrypted_path,
        )
        record.delete_instance()
        return True

    def delete_many(
        self,
        values: list[Optional[str]],
        *,
        owner_user_id: Optional[str] = None,
    ) -> int:
        deleted = 0
        seen = set()
        for value in values:
            media_id = extract_media_id(value)
            if not media_id or media_id in seen:
                continue
            seen.add(media_id)
            if self.delete(
                media_reference(media_id),
                owner_user_id=owner_user_id,
            ):
                deleted += 1
        return deleted


private_media_table = PrivateMediaTable(user_db)
