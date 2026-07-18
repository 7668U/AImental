"""
心灵社区开发模式（Community Dev Mode）。

开启 COMMUNITY_DEV_MODE 后，AI 角色的每日日程不再调用 LLM 生成，
而是把历史上某天已生成的完整日程「克隆」到目标日期上，作为稳定的测试数据。
这样本地启动后端时无需等待上游 LLM，也不会因为网络/额度问题拿不到日程。

来源日期选择顺序：
1. 环境变量 COMMUNITY_DEV_SCHEDULE_SOURCE_DATE（YYYY-MM-DD）指定的日期；
2. 该角色在目标日期之前、最近一个存在真实日程的历史日期（自动探测）；
3. 都没有时退化为本地兜底日程 build_fallback_daily_schedule（纯本地，无 LLM）。

克隆时只替换日期，保留每条状态的时:分、状态分类、描述、专注等级等，
因此 get_current_status 依然能按「当前时刻」命中对应状态。
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import pytz

from feature_flags import (
    COMMUNITY_DEV_MODE,
    COMMUNITY_DEV_SCHEDULE_SOURCE_DATE,
)

BEIJING_TZ = pytz.timezone("Asia/Shanghai")


def _parse_source_date(raw: str) -> Optional[date]:
    """解析环境变量里配置的来源日期，格式非法时返回 None。"""
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        print(f"⚠️ [DevMode] COMMUNITY_DEV_SCHEDULE_SOURCE_DATE='{raw}' 格式非法，应为 YYYY-MM-DD，将改为自动探测。")
        return None


def resolve_source_date(character_id: str, target_date: date) -> Optional[date]:
    """
    决定从哪一天克隆日程：
    优先用环境变量指定的日期；否则自动探测该角色最近一个有日程的历史日期。
    """
    from model.ai_status import ai_status_table

    configured = _parse_source_date(COMMUNITY_DEV_SCHEDULE_SOURCE_DATE)
    if configured and configured != target_date:
        return configured

    return ai_status_table.get_latest_schedule_date_before(character_id, target_date)


def _load_source_schedule(character_id: str, target_date: date) -> tuple[List[Dict[str, Any]], Optional[date]]:
    """
    读取用于克隆的源日程。返回 (schedule, source_date)。
    找不到任何历史日程时 schedule 为空列表、source_date 为 None。
    """
    from model.ai_status import ai_status_table

    source_date = resolve_source_date(character_id, target_date)
    if not source_date:
        return [], None

    schedule = ai_status_table.get_schedule_for_date(character_id, source_date)
    return schedule, source_date


def _write_schedule_to_date(character_id: str, target_date: date, schedule: List[Dict[str, Any]]) -> int:
    """
    把一份日程（HH:MM 粒度的活动列表）写入目标日期，先清除目标日期已有的真实日程。
    返回写入的条数。
    """
    from model.ai_status import AiStatus, ai_status_table, OFFLINE_STATUS_CATEGORY

    start_of_day = BEIJING_TZ.localize(datetime.combine(target_date, datetime.min.time()))
    next_day = start_of_day + timedelta(days=1)

    # 清掉目标日期已有的（非离线覆盖）日程，避免重复。
    (
        AiStatus.delete()
        .where(
            (AiStatus.character == character_id)
            & (AiStatus.status_category != OFFLINE_STATUS_CATEGORY)
            & (AiStatus.start_time < next_day)
            & (AiStatus.end_time > start_of_day)
        )
        .execute()
    )

    created = 0
    for activity in schedule:
        start_str = activity.get("start_time")
        end_str = activity.get("end_time")
        if not start_str or not end_str:
            continue
        start_dt = BEIJING_TZ.localize(
            datetime.strptime(f"{target_date} {start_str}", "%Y-%m-%d %H:%M")
        )
        end_dt = BEIJING_TZ.localize(
            datetime.strptime(f"{target_date} {end_str}", "%Y-%m-%d %H:%M")
        )
        ai_status_table.create_status(
            character_id=character_id,
            category=activity.get("status_category", "日常"),
            text=activity.get("status_description", ""),
            start_time=start_dt,
            end_time=end_dt,
            reply_delay_minutes=activity.get("reply_delay_minutes", 0),
            focus_level=activity.get("focus_level", "LOW"),
        )
        created += 1
    return created


def apply_dev_schedule(character, target_date: date) -> int:
    """
    开发模式下为单个角色准备 target_date 的日程（克隆历史日程，或退化到本地兜底）。
    返回写入的条数；0 表示未写入（例如已有日程）。character 需含 id / name / profile。
    """
    from generate_ai_status import build_fallback_daily_schedule

    schedule, source_date = _load_source_schedule(character.id, target_date)

    if schedule:
        created = _write_schedule_to_date(character.id, target_date, schedule)
        print(
            f"🧪 [DevMode] 已把 {source_date} 的日程克隆给 '{character.name}' "
            f"作为 {target_date} 的测试数据（{created} 条）。"
        )
        return created

    # 没有任何历史日程可克隆：用本地兜底日程，仍然不调用 LLM。
    fallback = build_fallback_daily_schedule(character.profile)
    created = _write_schedule_to_date(character.id, target_date, fallback)
    print(
        f"🧪 [DevMode] 未找到 '{character.name}' 的历史日程，"
        f"改用本地兜底日程作为 {target_date} 的测试数据（{created} 条）。"
    )
    return created


def ensure_dev_schedules(target_date: date) -> None:
    """
    开发模式入口：为所有 AI 角色确保 target_date 有日程（幂等，已有则跳过）。
    完全不调用 LLM。供 API 启动与后台 worker 复用。
    """
    if not COMMUNITY_DEV_MODE:
        return

    from model.ai_character import ai_character_table
    from model.ai_status import ai_status_table

    characters = ai_character_table.get_all_characters()
    if not characters:
        print("ℹ️ [DevMode] 未发现任何 AI 角色，跳过日程准备。")
        return

    print(f"🧪 [DevMode] 心灵社区开发模式已开启，准备 {target_date} 的日程（不调用 LLM）...")
    for character in characters:
        try:
            if ai_status_table.has_schedule_for_date(character.id, target_date):
                print(f"✅ [DevMode] '{character.name}' 在 {target_date} 已有日程，跳过。")
                continue
            apply_dev_schedule(character, target_date)
        except Exception as exc:  # noqa: BLE001
            print(f"🚨 [DevMode] 为 '{character.name}' 准备 {target_date} 日程时出错: {exc}")
