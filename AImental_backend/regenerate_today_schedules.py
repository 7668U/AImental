import argparse
import os
from datetime import datetime, timedelta

import pytz

os.environ.setdefault("SCHEDULE_LLM_TIMEOUT_SECONDS", "180")

from db import chat_db, status_db
from generate_ai_status import generate_daily_schedule
from model.ai_character import ai_character_table
from model.ai_status import AiStatus, ai_status_table


BEIJING_TZ = pytz.timezone("Asia/Shanghai")


def parse_args():
    parser = argparse.ArgumentParser(description="Regenerate AI community schedules for one date.")
    parser.add_argument("--date", help="Target date in YYYY-MM-DD. Defaults to today in Asia/Shanghai.")
    return parser.parse_args()


def looks_like_fallback(schedule):
    if len(schedule) != 9:
        return False
    first = schedule[0]
    return (
        first.get("status_category") == "睡觉"
        and "手机放在枕边" in first.get("status_description", "")
    )


def replace_schedule(character_id, target_date, schedule):
    start_of_day = BEIJING_TZ.localize(datetime.combine(target_date, datetime.min.time()))
    next_day = start_of_day + timedelta(days=1)

    deleted = (
        AiStatus.delete()
        .where(
            (AiStatus.character == character_id)
            & (AiStatus.start_time < next_day)
            & (AiStatus.end_time > start_of_day)
        )
        .execute()
    )

    created = 0
    for activity in schedule:
        start_dt = BEIJING_TZ.localize(
            datetime.strptime(f"{target_date} {activity['start_time']}", "%Y-%m-%d %H:%M")
        )
        end_dt = BEIJING_TZ.localize(
            datetime.strptime(f"{target_date} {activity['end_time']}", "%Y-%m-%d %H:%M")
        )
        ai_status_table.create_status(
            character_id=character_id,
            category=activity["status_category"],
            text=activity["status_description"],
            start_time=start_dt,
            end_time=end_dt,
            reply_delay_minutes=activity.get("reply_delay_minutes", 0),
            focus_level=activity.get("focus_level", "LOW"),
        )
        created += 1

    return deleted, created


def main():
    args = parse_args()
    target_date = (
        datetime.strptime(args.date, "%Y-%m-%d").date()
        if args.date
        else datetime.now(BEIJING_TZ).date()
    )

    for db in (chat_db, status_db):
        if db.is_closed():
            db.connect()

    print(f"TARGET_DATE={target_date}", flush=True)
    characters = ai_character_table.get_all_characters()
    success = 0
    skipped = 0

    try:
        for index, character in enumerate(characters, start=1):
            print(f"[{index}/{len(characters)}] GENERATING {character.name} ({character.id})", flush=True)
            schedule = generate_daily_schedule(
                character_profile=character.profile,
                recent_history=[],
                target_date=target_date,
            )

            if not schedule or looks_like_fallback(schedule):
                skipped += 1
                print(f"[{index}/{len(characters)}] SKIP {character.name}: LLM generation fell back or returned empty.", flush=True)
                continue

            deleted, created = replace_schedule(character.id, target_date, schedule)
            success += 1
            print(f"[{index}/{len(characters)}] OK {character.name}: deleted={deleted}, created={created}", flush=True)
    finally:
        for db in (chat_db, status_db):
            if not db.is_closed():
                db.close()

    print(f"DONE success={success} skipped={skipped} total={len(characters)}", flush=True)


if __name__ == "__main__":
    main()
