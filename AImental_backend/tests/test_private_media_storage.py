import base64
import hashlib
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from peewee import SqliteDatabase
from starlette.datastructures import Headers, UploadFile

import model.private_media as private_media


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/x8AAusB9Wl2n0YAAAAASUVORK5CYII="
)


class FakeBody:
    def __init__(self, data):
        self.data = data

    def get_raw_stream(self):
        return BytesIO(self.data)


class FakeCosClient:
    def __init__(self):
        self.objects = {}
        self.object_metadata = {}

    def put_object(self, *, Body, Key, **kwargs):
        self.objects[Key] = Body.read() if hasattr(Body, "read") else bytes(Body)
        self.object_metadata[Key] = {
            "Content-Type": kwargs.get("ContentType", ""),
        }
        return {"ETag": "fake"}

    def get_object(self, *, Key, **kwargs):
        return {"Body": FakeBody(self.objects[Key])}

    def delete_object(self, *, Key, **kwargs):
        self.objects.pop(Key, None)
        self.object_metadata.pop(Key, None)
        return {}

    def head_object(self, *, Key, **kwargs):
        metadata = self.object_metadata[Key]
        return {
            "Content-Length": str(len(self.objects[Key])),
            "Content-Type": metadata["Content-Type"],
        }

    def get_presigned_url(self, *, Bucket, Key, **kwargs):
        return (
            f"https://{Bucket}.cos.ap-beijing.myqcloud.com/{Key}"
            "?q-sign-time=1%3B2"
        )


class PrivateMediaStorageTestCase(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.database = SqliteDatabase(self.root / "private-media-test.db")
        self.bind_context = self.database.bind_ctx([private_media.PrivateMedia])
        self.bind_context.__enter__()

        self.patchers = [
            patch.object(private_media, "PRIVATE_MEDIA_ROOT", self.root / "media"),
            patch.object(private_media, "PRIVATE_MEDIA_STORAGE_BACKEND", "local"),
            patch.object(
                private_media,
                "encrypt_bytes",
                lambda data, purpose: b"encrypted:" + data,
            ),
            patch.object(
                private_media,
                "decrypt_bytes",
                lambda data, purpose: data.removeprefix(b"encrypted:"),
            ),
            patch.object(
                private_media,
                "sign_url_payload",
                lambda payload: "s" * 64,
            ),
            patch.object(
                private_media,
                "verify_url_signature",
                lambda payload, signature: signature == "s" * 64,
            ),
        ]
        for patcher in self.patchers:
            patcher.start()

        self.table = private_media.PrivateMediaTable(self.database)

    def tearDown(self):
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.database.close()
        self.bind_context.__exit__(None, None, None)
        self.temporary_directory.cleanup()

    def test_local_storage_encrypts_reads_signs_and_deletes(self):
        reference = self.table.store_image_bytes(
            owner_user_id="user-1",
            media_type="avatar",
            content_type="image/png",
            data=PNG_BYTES,
        )
        media_id = private_media.extract_media_id(reference)
        record = private_media.PrivateMedia.get_by_id(media_id)
        stored_path = self.table._absolute_path(record.encrypted_path)

        self.assertEqual(record.storage_backend, "local")
        self.assertNotEqual(stored_path.read_bytes(), PNG_BYTES)
        self.assertEqual(self.table.read(media_id), (PNG_BYTES, "image/png"))
        self.assertTrue(
            self.table.signed_url(reference).startswith(
                f"/api/v1/private-media/{media_id}"
            )
        )
        self.assertTrue(self.table.delete(reference, owner_user_id="user-1"))
        self.assertFalse(stored_path.exists())
        self.assertFalse(self.table.exists(reference))

    def test_cos_storage_streams_and_round_trips_presigned_url(self):
        fake_client = FakeCosClient()
        self.table._cos_client = fake_client

        with (
            patch.object(private_media, "PRIVATE_MEDIA_STORAGE_BACKEND", "cos"),
            patch.object(private_media, "PRIVATE_MEDIA_CDN_BASE_URL", ""),
            patch.object(
                private_media,
                "PRIVATE_MEDIA_COS_BUCKET",
                "private-test-1234567890",
            ),
        ):
            upload = UploadFile(
                file=BytesIO(PNG_BYTES),
                filename="avatar.png",
                headers=Headers({"content-type": "image/png"}),
            )
            reference = self.table.store_upload(
                owner_user_id="user-2",
                media_type="avatar",
                upload=upload,
            )
            media_id = private_media.extract_media_id(reference)
            record = private_media.PrivateMedia.get_by_id(media_id)
            signed_url = self.table.signed_url(reference)

            self.assertEqual(record.storage_backend, "cos")
            self.assertEqual(
                self.table.normalize_owner_reference(signed_url, "user-2"),
                reference,
            )
            self.assertEqual(self.table.read(media_id), (PNG_BYTES, "image/png"))
            self.assertTrue(self.table.delete(signed_url, owner_user_id="user-2"))
            self.assertEqual(fake_client.objects, {})

    def test_cos_storage_generates_type_a_sha256_cdn_url(self):
        fake_client = FakeCosClient()
        self.table._cos_client = fake_client

        with (
            patch.object(private_media, "PRIVATE_MEDIA_STORAGE_BACKEND", "cos"),
            patch.object(
                private_media,
                "PRIVATE_MEDIA_COS_BUCKET",
                "private-test-1234567890",
            ),
            patch.object(
                private_media,
                "PRIVATE_MEDIA_CDN_BASE_URL",
                "https://media.example.com",
            ),
            patch.object(
                private_media,
                "PRIVATE_MEDIA_CDN_AUTH_ALGORITHM",
                "sha256",
            ),
            patch.object(
                private_media,
                "PRIVATE_MEDIA_CDN_AUTH_SIGN_PARAM",
                "sign",
            ),
            patch.object(private_media, "PRIVATE_MEDIA_CDN_AUTH_UID", "0"),
            patch.object(
                private_media,
                "PRIVATE_MEDIA_CDN_AUTH_PRIMARY_KEY",
                "PrimaryKey123",
            ),
            patch.object(
                private_media,
                "PRIVATE_MEDIA_CDN_AUTH_BACKUP_KEY",
                "",
            ),
            patch.object(private_media.time, "time", return_value=1784351607),
            patch.object(
                private_media.secrets,
                "token_hex",
                return_value="abcdef0123456789",
            ),
        ):
            reference = self.table.store_image_bytes(
                owner_user_id="user-4",
                media_type="avatar",
                content_type="image/png",
                data=PNG_BYTES,
            )
            media_id = private_media.extract_media_id(reference)
            record = private_media.PrivateMedia.get_by_id(media_id)
            uri = f"/{record.encrypted_path}"
            digest = hashlib.sha256(
                (
                    f"{uri}-1784351607-abcdef0123456789-"
                    "0-PrimaryKey123"
                ).encode("utf-8")
            ).hexdigest()
            expected_url = (
                f"https://media.example.com{uri}"
                "?sign=1784351607-abcdef0123456789-0-"
                f"{digest}"
            )

            signed_url = self.table.signed_url(reference)
            self.assertEqual(signed_url, expected_url)
            self.assertEqual(
                self.table.normalize_owner_reference(signed_url, "user-4"),
                reference,
            )
            self.assertTrue(self.table.delete(reference, owner_user_id="user-4"))

    def test_cos_direct_upload_is_scoped_verified_and_registered(self):
        fake_client = FakeCosClient()
        self.table._cos_client = fake_client

        with (
            patch.object(private_media, "PRIVATE_MEDIA_STORAGE_BACKEND", "cos"),
            patch.object(
                private_media,
                "PRIVATE_MEDIA_COS_BUCKET",
                "private-test-1234567890",
            ),
        ):
            prepared = self.table.prepare_direct_upload(
                owner_user_id="user-direct",
                media_type="avatar",
                content_type="image/png",
                size=len(PNG_BYTES),
            )
            token_payload = self.table._decode_direct_upload_token(
                prepared["upload_token"]
            )
            object_key = self.table._cos_object_key(
                token_payload["media_id"]
            )
            fake_client.objects[object_key] = PNG_BYTES
            fake_client.object_metadata[object_key] = {
                "Content-Type": "image/png",
            }

            reference = self.table.confirm_direct_upload(
                token=prepared["upload_token"],
                owner_user_id="user-direct",
                media_type="avatar",
            )
            record = private_media.PrivateMedia.get_by_id(
                private_media.extract_media_id(reference)
            )

            self.assertEqual(record.storage_backend, "cos")
            self.assertEqual(record.encrypted_path, object_key)
            self.assertEqual(
                prepared["headers"],
                {
                    "Content-Type": "image/png",
                    "x-cos-server-side-encryption": "AES256",
                },
            )
            with self.assertRaises(ValueError):
                self.table.confirm_direct_upload(
                    token=prepared["upload_token"],
                    owner_user_id="another-user",
                    media_type="avatar",
                )

    def test_rejects_mismatched_image_content_type(self):
        with self.assertRaises(ValueError):
            self.table.store_image_bytes(
                owner_user_id="user-3",
                media_type="checkin",
                content_type="image/jpeg",
                data=PNG_BYTES,
            )


if __name__ == "__main__":
    unittest.main()
