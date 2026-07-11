import base64
import hashlib
import hmac
import json
import os
from datetime import date
from functools import lru_cache
from typing import Any, Dict

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from dotenv import load_dotenv
from peewee import TextField


load_dotenv()

ENCRYPTED_VALUE_PREFIX = "enc"
ENCRYPTED_FILE_MAGIC = b"FYENC1"
NONCE_SIZE = 12


class DataEncryptionError(RuntimeError):
    """Raised when protected data cannot be encrypted or decrypted safely."""


def _decode_key(raw_value: str, variable_name: str) -> bytes:
    value = (raw_value or "").strip()
    if not value:
        raise DataEncryptionError(f"{variable_name} is required.")

    padding = "=" * (-len(value) % 4)
    try:
        decoded = base64.urlsafe_b64decode(value + padding)
    except Exception as exc:
        raise DataEncryptionError(
            f"{variable_name} must be a URL-safe base64 encoded 32-byte key."
        ) from exc

    if len(decoded) != 32:
        raise DataEncryptionError(
            f"{variable_name} must decode to exactly 32 bytes, got {len(decoded)}."
        )
    return decoded


class DataKeyring:
    def __init__(
        self,
        keys: Dict[str, bytes],
        active_version: str,
        blind_index_key: bytes,
        url_signing_key: bytes,
    ):
        if active_version not in keys:
            raise DataEncryptionError(
                f"Active encryption key version '{active_version}' is not configured."
            )
        self.keys = keys
        self.active_version = active_version
        self.blind_index_key = blind_index_key
        self.url_signing_key = url_signing_key

    @classmethod
    def from_environment(cls) -> "DataKeyring":
        raw_keyring = os.getenv("DATA_ENCRYPTION_KEYS", "").strip()
        single_key = os.getenv("DATA_ENCRYPTION_KEY", "").strip()
        active_version = os.getenv(
            "ACTIVE_DATA_ENCRYPTION_KEY_VERSION", "v1"
        ).strip()

        if raw_keyring:
            try:
                configured_keys = json.loads(raw_keyring)
            except json.JSONDecodeError as exc:
                raise DataEncryptionError(
                    "DATA_ENCRYPTION_KEYS must be a JSON object."
                ) from exc
            if not isinstance(configured_keys, dict) or not configured_keys:
                raise DataEncryptionError(
                    "DATA_ENCRYPTION_KEYS must contain at least one key version."
                )
        elif single_key:
            configured_keys = {active_version: single_key}
        else:
            raise DataEncryptionError(
                "Configure DATA_ENCRYPTION_KEYS (preferred) or DATA_ENCRYPTION_KEY."
            )

        keys = {
            str(version): _decode_key(str(raw_key), f"DATA_ENCRYPTION_KEYS[{version}]")
            for version, raw_key in configured_keys.items()
        }
        blind_index_key = _decode_key(
            os.getenv("DATA_BLIND_INDEX_KEY", ""),
            "DATA_BLIND_INDEX_KEY",
        )
        url_signing_key = _decode_key(
            os.getenv("PRIVATE_MEDIA_URL_SIGNING_KEY", ""),
            "PRIVATE_MEDIA_URL_SIGNING_KEY",
        )
        return cls(keys, active_version, blind_index_key, url_signing_key)


@lru_cache(maxsize=1)
def get_keyring() -> DataKeyring:
    return DataKeyring.from_environment()


def reset_keyring_cache() -> None:
    get_keyring.cache_clear()


def is_encrypted_value(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(f"{ENCRYPTED_VALUE_PREFIX}:")


def encrypt_text(value: str, purpose: str) -> str:
    if not isinstance(value, str):
        value = str(value)

    keyring = get_keyring()
    nonce = os.urandom(NONCE_SIZE)
    aad = purpose.encode("utf-8")
    ciphertext = AESGCM(keyring.keys[keyring.active_version]).encrypt(
        nonce,
        value.encode("utf-8"),
        aad,
    )
    return ":".join(
        (
            ENCRYPTED_VALUE_PREFIX,
            keyring.active_version,
            base64.urlsafe_b64encode(nonce).decode("ascii").rstrip("="),
            base64.urlsafe_b64encode(ciphertext).decode("ascii").rstrip("="),
        )
    )


def decrypt_text(value: Any, purpose: str) -> Any:
    if value is None or not is_encrypted_value(value):
        return value

    try:
        _, version, encoded_nonce, encoded_ciphertext = value.split(":", 3)
        keyring = get_keyring()
        key = keyring.keys[version]
        nonce = base64.urlsafe_b64decode(
            encoded_nonce + ("=" * (-len(encoded_nonce) % 4))
        )
        ciphertext = base64.urlsafe_b64decode(
            encoded_ciphertext + ("=" * (-len(encoded_ciphertext) % 4))
        )
        plaintext = AESGCM(key).decrypt(
            nonce,
            ciphertext,
            purpose.encode("utf-8"),
        )
        return plaintext.decode("utf-8")
    except KeyError as exc:
        raise DataEncryptionError(
            f"Encryption key version is unavailable for purpose '{purpose}'."
        ) from exc
    except (ValueError, InvalidTag, UnicodeDecodeError) as exc:
        raise DataEncryptionError(
            f"Encrypted value failed authentication for purpose '{purpose}'."
        ) from exc


def blind_index(value: str, purpose: str) -> str:
    normalized = value.strip()
    digest = hmac.new(
        get_keyring().blind_index_key,
        f"{purpose}\0{normalized}".encode("utf-8"),
        hashlib.sha256,
    )
    return digest.hexdigest()


def sign_url_payload(payload: str) -> str:
    signature = hmac.new(
        get_keyring().url_signing_key,
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")


def verify_url_signature(payload: str, signature: str) -> bool:
    return hmac.compare_digest(sign_url_payload(payload), signature)


def encrypt_bytes(value: bytes, purpose: str) -> bytes:
    keyring = get_keyring()
    version_bytes = keyring.active_version.encode("ascii")
    if len(version_bytes) > 255:
        raise DataEncryptionError("Encryption key version is too long.")
    nonce = os.urandom(NONCE_SIZE)
    ciphertext = AESGCM(keyring.keys[keyring.active_version]).encrypt(
        nonce,
        value,
        purpose.encode("utf-8"),
    )
    return (
        ENCRYPTED_FILE_MAGIC
        + bytes([len(version_bytes)])
        + version_bytes
        + nonce
        + ciphertext
    )


def decrypt_bytes(value: bytes, purpose: str) -> bytes:
    if not value.startswith(ENCRYPTED_FILE_MAGIC):
        raise DataEncryptionError("Private media file is not encrypted.")

    offset = len(ENCRYPTED_FILE_MAGIC)
    version_length = value[offset]
    offset += 1
    version = value[offset : offset + version_length].decode("ascii")
    offset += version_length
    nonce = value[offset : offset + NONCE_SIZE]
    ciphertext = value[offset + NONCE_SIZE :]

    try:
        key = get_keyring().keys[version]
        return AESGCM(key).decrypt(
            nonce,
            ciphertext,
            purpose.encode("utf-8"),
        )
    except KeyError as exc:
        raise DataEncryptionError(
            f"Encryption key version '{version}' is unavailable."
        ) from exc
    except InvalidTag as exc:
        raise DataEncryptionError("Private media failed authentication.") from exc


class EncryptedTextField(TextField):
    def __init__(self, *args, purpose: str, **kwargs):
        self.encryption_purpose = purpose
        super().__init__(*args, **kwargs)

    def db_value(self, value: Any) -> Any:
        if value is None:
            return None
        if is_encrypted_value(value):
            return value
        return encrypt_text(self.serialize(value), self.encryption_purpose)

    def python_value(self, value: Any) -> Any:
        if value is None:
            return None
        plaintext = decrypt_text(value, self.encryption_purpose)
        return self.deserialize(plaintext)

    def serialize(self, value: Any) -> str:
        return str(value)

    def deserialize(self, value: Any) -> Any:
        return value


class EncryptedIntegerField(EncryptedTextField):
    def serialize(self, value: Any) -> str:
        return str(int(value))

    def deserialize(self, value: Any) -> Any:
        if value in (None, ""):
            return None
        return int(value)


class EncryptedFloatField(EncryptedTextField):
    def serialize(self, value: Any) -> str:
        return repr(float(value))

    def deserialize(self, value: Any) -> Any:
        if value in (None, ""):
            return None
        return float(value)


class EncryptedDateField(EncryptedTextField):
    def serialize(self, value: Any) -> str:
        if isinstance(value, date):
            return value.isoformat()
        return str(value)

    def deserialize(self, value: Any) -> Any:
        if value in (None, ""):
            return None
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))
