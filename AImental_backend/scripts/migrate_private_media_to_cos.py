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

from model.private_media import (  # noqa: E402
    PRIVATE_MEDIA_STORAGE_BACKEND,
    PrivateMedia,
    private_media_table,
)


def backup_user_database() -> Path:
    source = BACKEND_ROOT / "db" / "user_account.db"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target_dir = BACKEND_ROOT / "backups" / f"private-media-cos-{timestamp}"
    target_dir.mkdir(parents=True, exist_ok=False)
    target = target_dir / source.name

    source_connection = sqlite3.connect(source)
    target_connection = sqlite3.connect(target)
    try:
        source_connection.backup(target_connection)
    finally:
        target_connection.close()
        source_connection.close()
    return target


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate encrypted local private media into private COS."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show how many records would be migrated without uploading.",
    )
    parser.add_argument(
        "--keep-local",
        action="store_true",
        help="Keep encrypted local files after successful COS migration.",
    )
    args = parser.parse_args()

    local_records = list(
        PrivateMedia.select()
        .where(PrivateMedia.storage_backend == "local")
        .order_by(PrivateMedia.created_at.asc())
    )
    print(f"local_records={len(local_records)}")
    if args.dry_run:
        return
    if PRIVATE_MEDIA_STORAGE_BACKEND != "cos":
        raise SystemExit(
            "PRIVATE_MEDIA_STORAGE_BACKEND must be set to cos in "
            "AImental_backend/.env before migration."
        )
    if not local_records:
        print("Nothing to migrate.")
        return

    backup_path = backup_user_database()
    print(f"database_backup={backup_path}")

    migrated = 0
    failed = []
    for record in local_records:
        try:
            if private_media_table.migrate_local_record_to_cos(
                record,
                remove_local=not args.keep_local,
            ):
                migrated += 1
        except Exception as exc:  # noqa: BLE001
            failed.append((record.id, str(exc)))
            print(f"FAILED media_id={record.id}: {str(exc)[:300]}")

    print(f"migrated={migrated} failed={len(failed)}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
