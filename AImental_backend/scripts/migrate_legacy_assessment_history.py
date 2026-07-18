"""Restore legacy multi-assessment synthesis reports after user remapping.

Run from AImental_backend:
    python scripts/migrate_legacy_assessment_history.py --dry-run
    python scripts/migrate_legacy_assessment_history.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.chdir(BACKEND_ROOT)
load_dotenv(BACKEND_ROOT / ".env")

from model.history_analysis import HistoryAnalysis  # noqa: E402


def backup_database(source: Path, target: Path) -> None:
    source_connection = sqlite3.connect(source)
    target_connection = sqlite3.connect(target)
    try:
        source_connection.backup(target_connection)
    finally:
        target_connection.close()
        source_connection.close()


def parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return datetime.fromisoformat(value)


def create_signature(history_ids: list[str]) -> str:
    payload = json.dumps(sorted(history_ids), separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_source_records(source_path: Path) -> list[dict]:
    connection = sqlite3.connect(source_path)
    connection.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in connection.execute("SELECT * FROM history_analyses")]
    finally:
        connection.close()


def resolve_target_user(
    assessment_connection: sqlite3.Connection,
    user_connection: sqlite3.Connection,
    history_ids: list[str],
) -> str | None:
    placeholders = ",".join("?" for _ in history_ids)
    rows = assessment_connection.execute(
        f"""
        SELECT DISTINCT user_id
        FROM user_assessments
        WHERE id IN ({placeholders})
        """,
        history_ids,
    ).fetchall()
    user_ids = {str(row[0]) for row in rows if row[0]}
    if len(user_ids) != 1:
        return None
    target_user_id = next(iter(user_ids))
    exists = user_connection.execute(
        "SELECT 1 FROM users WHERE id = ?",
        (target_user_id,),
    ).fetchone()
    return target_user_id if exists else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Restore legacy multi-assessment synthesis reports."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=PROJECT_ROOT
        / "output"
        / "old-server-db-backups"
        / "20260704-221632"
        / "raw"
        / "db"
        / "psychological_assessment.db",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source = args.source.resolve()
    target = (BACKEND_ROOT / "db" / "psychological_assessment.db").resolve()
    user_db_path = (BACKEND_ROOT / "db" / "user_account.db").resolve()
    if not source.exists():
        raise SystemExit(f"Source database not found: {source}")

    source_records = load_source_records(source)
    if not source_records:
        print("legacy_history_records=0")
        return

    assessment_connection = sqlite3.connect(target)
    user_connection = sqlite3.connect(user_db_path)
    try:
        candidates = []
        for record in source_records:
            try:
                history_ids = json.loads(record["analyzed_history_ids"])
                content = json.loads(record["content"])
            except (TypeError, json.JSONDecodeError) as exc:
                print(f"skip id={record.get('id')}: invalid legacy payload ({exc})")
                continue
            if not isinstance(history_ids, list) or not isinstance(content, dict):
                print(f"skip id={record.get('id')}: unexpected legacy payload shape")
                continue
            history_ids = [str(item) for item in history_ids]
            target_user_id = resolve_target_user(
                assessment_connection,
                user_connection,
                history_ids,
            )
            signature = create_signature(history_ids)
            candidates.append(
                {
                    "id": str(record["id"]),
                    "legacy_user_id": str(record["user_id"]),
                    "target_user_id": target_user_id,
                    "history_ids": sorted(history_ids),
                    "signature": signature,
                    "content": content,
                    "created_at": parse_datetime(record.get("created_at")),
                }
            )

        print(f"legacy_history_records={len(source_records)}")
        print(f"migratable_records={sum(1 for item in candidates if item['target_user_id'])}")
        for item in candidates:
            print(
                "candidate "
                f"id={item['id']} "
                f"legacy_user={item['legacy_user_id']} "
                f"target_user={item['target_user_id']} "
                f"history_count={len(item['history_ids'])}"
            )

        if args.dry_run:
            return

        backup_dir = (
            BACKEND_ROOT
            / "backups"
            / f"legacy-assessment-history-{datetime.now():%Y%m%d-%H%M%S}"
        )
        backup_dir.mkdir(parents=True, exist_ok=False)
        backup_database(target, backup_dir / target.name)
        print(f"database_backup={backup_dir}")

        migrated = 0
        skipped = 0
        for item in candidates:
            if not item["target_user_id"]:
                skipped += 1
                continue

            existing_by_id = assessment_connection.execute(
                "SELECT 1 FROM history_analyses WHERE id = ?",
                (item["id"],),
            ).fetchone()
            existing_by_signature = assessment_connection.execute(
                "SELECT 1 FROM history_analyses WHERE analysis_signature = ?",
                (item["signature"],),
            ).fetchone()
            if existing_by_id or existing_by_signature:
                skipped += 1
                continue

            HistoryAnalysis.create(
                id=item["id"],
                user=item["target_user_id"],
                analysis_signature=item["signature"],
                analyzed_history_ids=json.dumps(
                    item["history_ids"],
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                content=json.dumps(item["content"], ensure_ascii=False),
                created_at=item["created_at"],
            )
            migrated += 1

        print(f"migrated={migrated}")
        print(f"skipped={skipped}")
    finally:
        user_connection.close()
        assessment_connection.close()


if __name__ == "__main__":
    main()
