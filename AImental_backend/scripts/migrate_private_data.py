"""Encrypt existing user data and move uploaded images into private storage.

Run from AImental_backend:
    python scripts/migrate_private_data.py
    python scripts/migrate_private_data.py --dry-run
"""

import argparse
import json
import mimetypes
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlparse


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))
os.chdir(BACKEND_ROOT)

from dotenv import load_dotenv

load_dotenv(BACKEND_ROOT / ".env")

from security.data_encryption import (
    encrypt_bytes,
    encrypt_text,
    is_encrypted_value,
)


FIELD_SPECS: Dict[str, Dict[str, Dict[str, str]]] = {
    "user_account.db": {
        "users": {
            "openid": "users.openid",
            "nickname": "users.nickname",
            "avatar_url": "users.avatar_url",
            "gender": "users.gender",
            "birthday": "users.birthday",
        },
    },
    "community_chat.db": {
        "chats": {
            "title": "chats.title",
            "message": "chats.message",
        },
        "community_chats": {
            "messages_history": "community_chats.messages_history",
            "favorability_history": "community_chats.favorability_history",
            "last_message_snippet": "community_chats.last_message_snippet",
        },
        "friendships": {
            "verification_message": "friendships.verification_message",
        },
        "community_user_memory": {
            "profile_card_json": "community_user_memory.profile_card_json",
        },
        "community_history_summaries": {
            "summary_card_json": "community_history_summaries.summary_card_json",
        },
    },
    "psychological_assessment.db": {
        "user_assessments": {
            "answers": "user_assessments.answers",
            "raw_score": "user_assessments.raw_score",
            "final_score": "user_assessments.final_score",
            "result_level": "user_assessments.result_level",
            "result_interpretation": "user_assessments.result_interpretation",
            "result_recommendation": "user_assessments.result_recommendation",
            "result_details": "user_assessments.result_details",
        },
        "history_analyses": {
            "analyzed_history_ids": "history_analyses.analyzed_history_ids",
            "content": "history_analyses.content",
        },
    },
    "ai_status.db": {
        "checkins": {
            "mood": "checkins.mood",
            "mood_id": "checkins.mood_id",
            "mood_family": "checkins.mood_family",
            "mood_valence": "checkins.mood_valence",
            "mood_energy": "checkins.mood_energy",
            "color": "checkins.color",
            "color_id": "checkins.color_id",
            "color_label": "checkins.color_label",
            "color_group": "checkins.color_group",
            "color_tone": "checkins.color_tone",
            "color_description": "checkins.color_description",
            "tags": "checkins.tags",
            "status_ids": "checkins.status_ids",
            "status_families": "checkins.status_families",
            "text_content": "checkins.text_content",
            "image_url": "checkins.image_url",
            "image_urls": "checkins.image_urls",
            "location_name": "checkins.location_name",
            "location_address": "checkins.location_address",
            "location_latitude": "checkins.location_latitude",
            "location_longitude": "checkins.location_longitude",
        },
        "analyses": {
            "content": "analyses.content",
        },
        "emotion_color_card_cache": {
            "palette_signature": "emotion_color_card_cache.palette_signature",
            "mixed_hex": "emotion_color_card_cache.mixed_hex",
            "mixed_color": "emotion_color_card_cache.mixed_color",
            "selected_colors": "emotion_color_card_cache.selected_colors",
            "color_name": "emotion_color_card_cache.color_name",
            "subtitle": "emotion_color_card_cache.subtitle",
            "tags": "emotion_color_card_cache.tags",
            "scene_hint": "emotion_color_card_cache.scene_hint",
            "prompt": "emotion_color_card_cache.prompt",
            "error": "emotion_color_card_cache.error",
        },
    },
    "daily_status.db": {
        "checkins": {
            "mood": "checkins.mood",
            "color": "checkins.color",
            "tags": "checkins.tags",
            "text_content": "checkins.text_content",
            "image_url": "checkins.image_url",
        },
        "analyses": {
            "content": "analyses.content",
        },
    },
    "feedback.db": {
        "feedbacks": {
            "content": "feedbacks.content",
        },
    },
    "promotion.db": {
        "test_records": {
            "result_personality_id": "test_records.result_personality_id",
            "answers_json": "test_records.answers_json",
        },
        "soul_drink_records": {
            "visitor_token": "soul_drink_records.visitor_token",
            "answers_json": "soul_drink_records.answers_json",
            "scores_json": "soul_drink_records.scores_json",
            "result_type": "soul_drink_records.result_type",
            "result_drink": "soul_drink_records.result_drink",
        },
    },
    "cabinet.db": {
        "notes": {
            "title": "notes.title",
            "content": "notes.content",
        },
    },
    "note.db": {
        "notes": {
            "title": "notes.title",
            "content": "notes.content",
        },
    },
    "paper_airplane.db": {
        "paper_airplanes": {
            "message": "paper_airplanes.message",
        },
    },
    "airplane.db": {
        "paper_airplanes": {
            "message": "paper_airplanes.message",
        },
    },
}


def table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    return bool(
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone()
    )


def table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        row[1]
        for row in connection.execute(f'PRAGMA table_info("{table_name}")')
    }


def backup_databases_and_media(backup_root: Path) -> int:
    backup_root.mkdir(parents=True, exist_ok=False)
    backed_up = 0

    for source in sorted((BACKEND_ROOT / "db").glob("*.db")):
        temporary = backup_root / source.name
        source_connection = sqlite3.connect(source)
        destination_connection = sqlite3.connect(temporary)
        try:
            source_connection.backup(destination_connection)
        finally:
            destination_connection.close()
            source_connection.close()

        encrypted = encrypt_bytes(
            temporary.read_bytes(),
            f"migration-backup:db/{source.name}",
        )
        encrypted_path = temporary.with_suffix(".db.fyenc")
        encrypted_path.write_bytes(encrypted)
        temporary.unlink()
        backed_up += 1

    media_roots = [
        BACKEND_ROOT / "static" / "status",
        BACKEND_ROOT / "static" / "avatars",
    ]
    for media_root in media_roots:
        if not media_root.exists():
            continue
        for source in media_root.rglob("*"):
            if not source.is_file():
                continue
            relative = source.relative_to(BACKEND_ROOT)
            destination = backup_root / "media" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            encrypted = encrypt_bytes(
                source.read_bytes(),
                f"migration-backup:media/{relative.as_posix()}",
            )
            destination.with_suffix(destination.suffix + ".fyenc").write_bytes(
                encrypted
            )
            backed_up += 1

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "encrypted_files": backed_up,
        "restore_note": (
            "Files use the same versioned AES-GCM keyring as the application. "
            "Keep old key versions available until this backup expires."
        ),
    }
    (backup_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return backed_up


def local_media_path(value: Optional[str]) -> Optional[Path]:
    if not value:
        return None
    raw = str(value).strip()
    if raw.startswith("media:"):
        return None
    parsed = urlparse(raw)
    candidate_path = parsed.path if parsed.scheme else raw
    candidate_path = candidate_path.lstrip("/").replace("\\", "/")
    if not candidate_path.startswith("static/"):
        return None
    resolved = (BACKEND_ROOT / candidate_path).resolve()
    if BACKEND_ROOT not in resolved.parents or not resolved.is_file():
        return None
    return resolved


def detect_content_type(path: Path, data: bytes) -> Optional[str]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed


def migrate_media(dry_run: bool) -> tuple[int, list[Path]]:
    if dry_run:
        return 0, []

    from model.private_media import private_media_table

    migrated = 0
    plaintext_files: list[Path] = []

    user_db_path = BACKEND_ROOT / "db" / "user_account.db"
    if user_db_path.exists():
        connection = sqlite3.connect(user_db_path)
        try:
            rows = connection.execute(
                "SELECT id, avatar_url FROM users WHERE avatar_url IS NOT NULL"
            ).fetchall()
            for user_id, avatar_url in rows:
                path = local_media_path(avatar_url)
                if not path or path.name == "default.png":
                    continue
                data = path.read_bytes()
                content_type = detect_content_type(path, data)
                if not content_type:
                    continue
                reference = private_media_table.store_image_bytes(
                    owner_user_id=user_id,
                    media_type="avatar",
                    content_type=content_type,
                    data=data,
                )
                connection.execute(
                    "UPDATE users SET avatar_url=? WHERE id=?",
                    (reference, user_id),
                )
                connection.commit()
                plaintext_files.append(path)
                migrated += 1
        finally:
            connection.close()

    for database_name in ("ai_status.db", "daily_status.db"):
        database_path = BACKEND_ROOT / "db" / database_name
        if not database_path.exists():
            continue
        connection = sqlite3.connect(database_path)
        try:
            if not table_exists(connection, "checkins"):
                continue
            columns = table_columns(connection, "checkins")
            selected = ["rowid", "user_id", "image_url"]
            if "image_urls" in columns:
                selected.append("image_urls")
            rows = connection.execute(
                f"SELECT {', '.join(selected)} FROM checkins"
            ).fetchall()
            for row in rows:
                rowid, user_id, image_url, *extra = row
                raw_values: list[str] = []
                if image_url:
                    raw_values.append(image_url)
                if extra and extra[0]:
                    try:
                        parsed = json.loads(extra[0])
                        if isinstance(parsed, list):
                            raw_values.extend(parsed)
                    except json.JSONDecodeError:
                        raw_values.append(extra[0])

                references: list[str] = []
                seen = set()
                for raw_value in raw_values:
                    path = local_media_path(raw_value)
                    if not path:
                        if raw_value not in seen:
                            references.append(raw_value)
                            seen.add(raw_value)
                        continue
                    data = path.read_bytes()
                    content_type = detect_content_type(path, data)
                    if not content_type:
                        continue
                    reference = private_media_table.store_image_bytes(
                        owner_user_id=user_id,
                        media_type="checkin",
                        content_type=content_type,
                        data=data,
                    )
                    references.append(reference)
                    seen.add(reference)
                    plaintext_files.append(path)
                    migrated += 1

                if references:
                    if "image_urls" in columns:
                        connection.execute(
                            "UPDATE checkins SET image_url=?, image_urls=? WHERE rowid=?",
                            (
                                references[0],
                                json.dumps(
                                    references,
                                    ensure_ascii=False,
                                    separators=(",", ":"),
                                ),
                                rowid,
                            ),
                        )
                    else:
                        connection.execute(
                            "UPDATE checkins SET image_url=? WHERE rowid=?",
                            (references[0], rowid),
                        )
            connection.commit()
        finally:
            connection.close()

    return migrated, plaintext_files


def encrypt_database_fields(dry_run: bool) -> Dict[str, int]:
    totals: Dict[str, int] = {}
    for database_name, tables in FIELD_SPECS.items():
        database_path = BACKEND_ROOT / "db" / database_name
        if not database_path.exists():
            continue

        connection = sqlite3.connect(database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            changed = 0
            for table_name, columns in tables.items():
                if not table_exists(connection, table_name):
                    continue
                existing_columns = table_columns(connection, table_name)
                for column_name, purpose in columns.items():
                    if column_name not in existing_columns:
                        continue
                    rows = connection.execute(
                        f'SELECT rowid, "{column_name}" '
                        f'FROM "{table_name}" '
                        f'WHERE "{column_name}" IS NOT NULL'
                    ).fetchall()
                    for rowid, value in rows:
                        if is_encrypted_value(value):
                            continue
                        changed += 1
                        if dry_run:
                            continue
                        encrypted = encrypt_text(str(value), purpose)
                        connection.execute(
                            f'UPDATE "{table_name}" SET "{column_name}"=? '
                            "WHERE rowid=?",
                            (encrypted, rowid),
                        )
            if dry_run:
                connection.rollback()
            else:
                connection.commit()
            totals[database_name] = changed
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
    return totals


def verify_encryption() -> Dict[str, int]:
    remaining: Dict[str, int] = {}
    for database_name, tables in FIELD_SPECS.items():
        database_path = BACKEND_ROOT / "db" / database_name
        if not database_path.exists():
            continue
        connection = sqlite3.connect(database_path)
        try:
            count = 0
            for table_name, columns in tables.items():
                if not table_exists(connection, table_name):
                    continue
                existing_columns = table_columns(connection, table_name)
                for column_name in columns:
                    if column_name not in existing_columns:
                        continue
                    rows = connection.execute(
                        f'SELECT "{column_name}" FROM "{table_name}" '
                        f'WHERE "{column_name}" IS NOT NULL'
                    )
                    count += sum(
                        1
                        for (value,) in rows
                        if not is_encrypted_value(value)
                    )
            remaining[database_name] = count
        finally:
            connection.close()
    return remaining


def remove_plaintext_media(paths: Iterable[Path]) -> int:
    removed = 0
    for path in sorted(set(paths)):
        try:
            path.unlink(missing_ok=True)
            removed += 1
        except OSError:
            pass
    return removed


def find_orphan_plaintext_user_media() -> list[Path]:
    orphaned = []
    status_root = BACKEND_ROOT / "static" / "status"
    if status_root.exists():
        orphaned.extend(path for path in status_root.rglob("*") if path.is_file())

    avatar_root = BACKEND_ROOT / "static" / "avatars"
    uuid_avatar_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_",
        re.IGNORECASE,
    )
    if avatar_root.exists():
        orphaned.extend(
            path
            for path in avatar_root.iterdir()
            if path.is_file() and uuid_avatar_pattern.match(path.name)
        )
    return orphaned


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--keep-plaintext-media",
        action="store_true",
        help="Keep old static user image files after encrypted copies are verified.",
    )
    args = parser.parse_args()

    backup_root = (
        BACKEND_ROOT
        / "backups"
        / f"privacy-migration-{datetime.now():%Y%m%d-%H%M%S}"
    )

    if args.dry_run:
        field_counts = encrypt_database_fields(dry_run=True)
        print(json.dumps({"dry_run_field_counts": field_counts}, indent=2))
        return 0

    backup_count = backup_databases_and_media(backup_root)
    media_count, plaintext_media = migrate_media(dry_run=False)
    field_counts = encrypt_database_fields(dry_run=False)
    remaining = verify_encryption()
    if any(remaining.values()):
        raise RuntimeError(f"Encryption verification failed: {remaining}")

    removed_count = 0
    if not args.keep_plaintext_media:
        removed_count = remove_plaintext_media(
            [*plaintext_media, *find_orphan_plaintext_user_media()]
        )

    summary = {
        "encrypted_backup_files": backup_count,
        "migrated_private_media": media_count,
        "encrypted_database_values": field_counts,
        "remaining_plaintext_values": remaining,
        "removed_plaintext_media_files": removed_count,
        "backup_directory": str(backup_root),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
