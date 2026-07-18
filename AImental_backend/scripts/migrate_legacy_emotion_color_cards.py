#!/usr/bin/env python
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

load_dotenv(BACKEND_ROOT / ".env")

from model.emotion_color_card import (  # noqa: E402
    EMOTION_COLOR_CARD_MEDIA_OWNER,
    EmotionColorCardCache,
)
from model.private_media import private_media_table  # noqa: E402


def backup_database(source: Path, target: Path) -> None:
    source_connection = sqlite3.connect(source)
    target_connection = sqlite3.connect(target)
    try:
        source_connection.backup(target_connection)
    finally:
        target_connection.close()
        source_connection.close()


def resolve_legacy_path(record: EmotionColorCardCache) -> Path | None:
    candidates = []
    if record.local_path:
        candidates.append(Path(record.local_path))
    if record.background_image_url and record.background_image_url.startswith(
        "/static/"
    ):
        candidates.append(BACKEND_ROOT / record.background_image_url.lstrip("/"))

    for candidate in candidates:
        if not candidate.is_absolute():
            candidate = BACKEND_ROOT / candidate
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Move legacy public emotion color card files into private media storage."
        )
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--keep-legacy",
        action="store_true",
        help="Keep old public image and raw response files after migration.",
    )
    args = parser.parse_args()

    records = [
        record
        for record in EmotionColorCardCache.select()
        if (
            record.background_image_url
            and record.background_image_url.startswith("/static/")
        )
    ]
    print(f"legacy_records={len(records)}")
    if args.dry_run or not records:
        return

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = BACKEND_ROOT / "backups" / f"legacy-color-cards-{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    for database_name in ("user_account.db", "ai_status.db"):
        source = BACKEND_ROOT / "db" / database_name
        if source.exists():
            backup_database(source, backup_dir / database_name)
    print(f"database_backup={backup_dir}")

    migrated = 0
    failed = []
    for record in records:
        image_path = resolve_legacy_path(record)
        if not image_path:
            failed.append((record.palette_key, "legacy image file not found"))
            continue

        old_local_path = Path(record.local_path) if record.local_path else image_path
        if not old_local_path.is_absolute():
            old_local_path = BACKEND_ROOT / old_local_path
        old_raw_path = Path(record.raw_path) if record.raw_path else None
        if old_raw_path and not old_raw_path.is_absolute():
            old_raw_path = BACKEND_ROOT / old_raw_path

        media_reference = None
        try:
            media_reference = private_media_table.store_image_bytes(
                owner_user_id=EMOTION_COLOR_CARD_MEDIA_OWNER,
                media_type="emotion_color_card",
                content_type="image/png",
                data=image_path.read_bytes(),
            )
            with record._meta.database.atomic():
                record.background_image_url = media_reference
                record.local_path = None
                record.raw_path = None
                record.save(
                    only=[
                        EmotionColorCardCache.background_image_url,
                        EmotionColorCardCache.local_path,
                        EmotionColorCardCache.raw_path,
                    ]
                )
        except Exception as exc:  # noqa: BLE001
            if media_reference:
                private_media_table.delete(
                    media_reference,
                    owner_user_id=EMOTION_COLOR_CARD_MEDIA_OWNER,
                )
            failed.append((record.palette_key, str(exc)))
            continue

        if not args.keep_legacy:
            old_local_path.unlink(missing_ok=True)
            if old_raw_path:
                old_raw_path.unlink(missing_ok=True)
        migrated += 1

    print(f"migrated={migrated} failed={len(failed)}")
    for palette_key, error in failed:
        print(f"FAILED palette_key={palette_key}: {error[:300]}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
