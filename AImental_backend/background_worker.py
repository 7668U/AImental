# background_worker.py

import sys

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

import time
from datetime import datetime, timedelta
import random
import json
import re

# 导入 APScheduler
from apscheduler.schedulers.background import BackgroundScheduler
import pytz 

# --- 导入我们项目的所有组件 ---
from db import chat_db, status_db, user_db
from feature_flags import ENABLE_COMMUNITY_BACKEND, COMMUNITY_DEV_MODE
# 导入我们全局配置好的日志记录器
from logger_config import logger

if ENABLE_COMMUNITY_BACKEND:
    from model.ai_character import ai_character_table
    from model.ai_status import ai_status_table
    from model.ai_task import ai_task_table
    from model.friendship import friendship_table, Friendship
    from model.chat_community import community_chat_table
    from model.community_memory import community_memory_table

    # --- 导入AI能力生成器 ---
    from generate_ai_status import generate_daily_schedule
    # 【重要】从 generate_community_response 导入两个函数
    from generate_community_response import generate_ai_response, generate_proactive_message, build_night_reply_context
    from generate_community_affinity import assess_community_affinity
    from generate_friend_response import generate_friend_request_decision

# 定义北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')
AFFINITY_UPDATE_INTERVAL = 20
PROACTIVE_AFFINITY_THRESHOLD = 80.0
PROACTIVE_MIN_MESSAGES = 40
PROACTIVE_MIN_IDLE_AFTER_USER_MINUTES = 90
PROACTIVE_MIN_IDLE_AFTER_AI_MINUTES = 360
PROACTIVE_COOLDOWN_HOURS = 18

# ---------------------------------------------------
# 核心工作函数 (Jobs for the Scheduler)
# ---------------------------------------------------

def build_response_status_context(
    *,
    current_status,
    user_id: str,
    character_id: str,
    now: datetime,
) -> dict:
    """把角色日程转换成回复风格；日程不再阻断回复。"""
    category = current_status.status_category if current_status else "在线"
    status_text = current_status.status_text if current_status else "正在看消息"
    focus_level = current_status.focus_level if current_status else "AVAILABLE"

    is_night = now.hour >= 23 or now.hour < 7
    looks_like_sleep = "睡" in category or "睡" in status_text or focus_level == "UNINTERRUPTIBLE"

    response_mode = "normal"
    response_guidance = "正常陪伴式回复。"
    if is_night or looks_like_sleep:
        response_mode = "night_soft"
        response_guidance = build_night_reply_context(user_id, character_id, now)
    elif focus_level == "HIGH":
        response_mode = "focused"
        response_guidance = "你手头原本有事，但已经看到用户消息。回复可以更短、更像从事情里抬头说话，但不能拒绝或暂停。"
    elif focus_level == "LOW":
        response_mode = "low_energy"
        response_guidance = "你状态比较松弛，可以自然接话，不要表现得像客服。"

    return {
        "status_title": category,
        "status_description": status_text,
        "focus_level": focus_level,
        "response_mode": response_mode,
        "response_guidance": response_guidance,
    }


def extract_mbti(character_profile: dict) -> str:
    raw = str(
        (character_profile or {})
        .get("personality_traits", {})
        .get("mbti", "")
    ).upper()
    match = re.search(r"[IE][NS][FT][JP]", raw)
    return match.group(0) if match else ""


def affinity_speed_modifiers(character_profile: dict) -> dict:
    """根据 MBTI 给关系升温、降温和主动概率一个温和倍率。"""
    mbti = extract_mbti(character_profile)
    warm = 1.0
    cool = 1.0
    proactive = 1.0

    if not mbti:
        return {"mbti": "", "warm": warm, "cool": cool, "proactive": proactive}

    if mbti[0] == "E":
        warm += 0.12
        proactive += 0.18
    else:
        warm -= 0.06
        proactive -= 0.14

    if mbti[2] == "F":
        warm += 0.12
        cool -= 0.06
        proactive += 0.08
    else:
        warm -= 0.04
        cool += 0.08

    if mbti[3] == "P":
        warm += 0.04
        cool -= 0.03
        proactive += 0.06
    else:
        cool += 0.04
        proactive -= 0.04

    if mbti[1] == "N":
        warm += 0.03

    return {
        "mbti": mbti,
        "warm": max(0.75, min(1.32, warm)),
        "cool": max(0.80, min(1.25, cool)),
        "proactive": max(0.65, min(1.35, proactive)),
    }


def apply_affinity_delta(current_score: float, base_delta: float, character_profile: dict) -> float:
    modifiers = affinity_speed_modifiers(character_profile)
    if base_delta > 0:
        adjusted = base_delta * modifiers["warm"]
        if current_score >= 90:
            adjusted *= 0.35
        elif current_score >= 80:
            adjusted *= 0.6
        elif current_score >= 60:
            adjusted *= 0.85
        return min(3.0, adjusted)

    if base_delta < 0:
        adjusted = base_delta * modifiers["cool"]
        if current_score <= 20:
            adjusted *= 0.7
        return max(-8.0, adjusted)

    return 0.0


def proactive_probability(score: float, character_profile: dict) -> float:
    modifiers = affinity_speed_modifiers(character_profile)
    base = 0.06 + max(0.0, score - PROACTIVE_AFFINITY_THRESHOLD) * 0.006
    return max(0.03, min(0.22, base * modifiers["proactive"]))


def parse_message_history(raw_history: str) -> list:
    try:
        history = json.loads(raw_history or "[]")
        return history if isinstance(history, list) else []
    except json.JSONDecodeError:
        return []

def save_ai_message_from_worker(user_id: str, character_id: str, message_content: str):
    """后台任务生成的消息只写入数据库。"""
    new_msg_record = community_chat_table.add_message(
        user_id=user_id,
        character_id=character_id,
        role='ai',
        content=message_content
    )

    if not new_msg_record:
        logger.error(f"保存来自角色 {character_id} 的消息失败。")
        return

    logger.debug(f"已保存来自角色 {character_id} 的后台消息。")
    
def schedule_daily_status_generation():
    """
    【已升级】为所有AI角色生成第二天的完整行程，并保存 focus_level。
    """
    if not ENABLE_COMMUNITY_BACKEND:
        logger.info("JOB_STATUS_GEN: 心灵社区后端已下线，跳过角色日程生成。")
        return

    today_in_beijing = datetime.now(BEIJING_TZ).date()
    target_date = today_in_beijing + timedelta(days=1)

    # 开发模式：克隆历史日程作为测试数据，不调用 LLM。
    if COMMUNITY_DEV_MODE:
        logger.info(f"JOB_STATUS_GEN: 开发模式已开启，克隆历史日程作为 {target_date} 的测试数据（不调用 LLM）。")
        from community_dev_mode import ensure_dev_schedules
        ensure_dev_schedules(target_date)
        return

    logger.info(f"JOB_STATUS_GEN: 开始为所有角色生成 {target_date} 的日程...")

    all_characters = ai_character_table.get_all_characters()
    for character in all_characters:
        try:
            logger.info(f"-> 正在处理角色: {character.name} ({character.id})")
            # a. 准备历史数据 (未来可扩展)
            recent_history = [
                {"date": (today_in_beijing - timedelta(days=1)).strftime('%Y-%m-%d'), "summary": "昨天似乎是休息的一天。"}
            ]
            
            # b. 调用状态生成器
            daily_schedule = generate_daily_schedule(
                character_profile=character.profile,
                recent_history=recent_history,
                target_date=target_date
            )
            
            # c. 将生成的日程写入数据库
            if daily_schedule:
                for activity in daily_schedule:
                    start_dt = BEIJING_TZ.localize(datetime.strptime(f"{target_date} {activity['start_time']}", "%Y-%m-%d %H:%M"))
                    end_dt = BEIJING_TZ.localize(datetime.strptime(f"{target_date} {activity['end_time']}", "%Y-%m-%d %H:%M"))
                    
                    # --- 【核心修改】在这里传入新的 focus_level 字段 ---
                    ai_status_table.create_status(
                        character_id=character.id,
                        category=activity['status_category'],
                        text=activity['status_description'],
                        start_time=start_dt,
                        end_time=end_dt,
                        reply_delay_minutes=activity.get('reply_delay_minutes', 5),
                        focus_level=activity.get('focus_level', 'LOW') # <-- 传入新字段
                    )
                logger.info(f"✅ 成功为 {character.name} 创建了 {len(daily_schedule)} 条日程。")
            else:
                logger.warning(f"❌ 为 {character.name} 生成日程失败。")

        except Exception as e:
            logger.error(f"🚨 处理角色 {character.name} 时发生严重错误: {e}", exc_info=True)
            continue

def check_for_resumable_conversations():
    """
    【全新任务】检查所有被暂停的对话，看是否有AI可以回归了。
    """
    if not ENABLE_COMMUNITY_BACKEND:
        logger.info("JOB_RESUME_CHECK: 心灵社区后端已下线，跳过恢复对话检查。")
        return

    logger.info("JOB_RESUME_CHECK: 开始检查可恢复的对话...")
    resumable_chats = community_chat_table.get_resumable_conversations()
    
    if not resumable_chats:
        return

    for chat in resumable_chats:
        logger.info(f"-> 发现可恢复对话: 用户({chat.user_id}) 与 AI({chat.character.id})")
        
        # 1. 将对话状态改回“可连续”
        community_chat_table.update_conversation_state(
            user_id=chat.user_id,
            character_id=chat.character.id,
            state='CONTINUOUS',
            resumes_at=None
        )

        # 2. 创建一个“主动聊天”任务，让AI回来打个招呼
        #    假设 ai_task_table 中有一个 create_task_if_needed 方法
        ai_task_table.create_task_if_needed(
            user_id=chat.user_id,
            character_id=chat.character.id,
            task_type='proactive_chat', # <-- 使用新的任务类型
            execute_at=datetime.now(BEIJING_TZ) + timedelta(minutes=random.randint(0, 2))
        )
        logger.info(f"   已为 AI({chat.character.id}) 创建主动聊天任务以回归对话。")


def check_for_high_affinity_proactive_conversations():
    """高好感关系的主动消息触发器，避免连续对话中突兀插话。"""
    if not ENABLE_COMMUNITY_BACKEND:
        logger.info("JOB_PROACTIVE_CHECK: 心灵社区后端已下线，跳过主动消息检查。")
        return

    now = datetime.now(BEIJING_TZ)
    if now.hour >= 23 or now.hour < 8:
        logger.debug("JOB_PROACTIVE_CHECK: 当前为夜间，跳过主动消息检查。")
        return

    conversations = community_chat_table.get_all_active_conversations()
    if not conversations:
        return

    logger.info("JOB_PROACTIVE_CHECK: 开始检查高好感主动消息候选...")
    cooldown_since = datetime.utcnow() + timedelta(hours=8) - timedelta(hours=PROACTIVE_COOLDOWN_HOURS)

    for conversation in conversations:
        try:
            score = float(conversation.favorability or 0.0)
            if score < PROACTIVE_AFFINITY_THRESHOLD:
                continue

            history = parse_message_history(conversation.messages_history)
            if len(history) < PROACTIVE_MIN_MESSAGES:
                continue

            last_message = history[-1]
            last_timestamp = int(last_message.get("timestamp") or 0)
            if last_timestamp <= 0:
                continue

            idle_minutes = (int(now.timestamp()) - last_timestamp) / 60
            last_role = last_message.get("role")
            required_idle = (
                PROACTIVE_MIN_IDLE_AFTER_USER_MINUTES
                if last_role == "user"
                else PROACTIVE_MIN_IDLE_AFTER_AI_MINUTES
            )
            if idle_minutes < required_idle:
                continue

            recent_ai_tail = 0
            for message in reversed(history[-4:]):
                if message.get("role") == "ai":
                    recent_ai_tail += 1
                else:
                    break
            if recent_ai_tail >= 2:
                continue

            user_id = conversation.user_id
            character_id = conversation.character.id
            if ai_task_table.has_pending_task(user_id, character_id, "proactive_chat"):
                continue
            if ai_task_table.has_pending_task(user_id, character_id, "reply"):
                continue
            if ai_task_table.has_recent_done_task(
                user_id,
                character_id,
                "proactive_chat",
                cooldown_since,
            ):
                continue

            current_status = ai_status_table.get_current_status(character_id)
            status_context = build_response_status_context(
                current_status=current_status,
                user_id=user_id,
                character_id=character_id,
                now=now,
            )
            if status_context.get("response_mode") == "night_soft":
                continue
            if status_context.get("focus_level") in {"HIGH", "UNINTERRUPTIBLE"}:
                continue

            character = ai_character_table.get_character_by_id(character_id)
            if not character:
                continue

            chance = proactive_probability(score, character.profile)
            roll = random.random()
            if roll > chance:
                logger.debug(
                    "主动消息候选未触发 user=%s character=%s score=%.1f roll=%.3f chance=%.3f",
                    user_id,
                    character_id,
                    score,
                    roll,
                    chance,
                )
                continue

            execute_at = now + timedelta(minutes=random.randint(2, 10))
            task = ai_task_table.create_task_if_needed(
                user_id=user_id,
                character_id=character_id,
                task_type="proactive_chat",
                execute_at=execute_at,
            )
            if task:
                logger.info(
                    "已创建高好感主动消息任务 user=%s character=%s score=%.1f idle=%.1fmin chance=%.3f",
                    user_id,
                    character_id,
                    score,
                    idle_minutes,
                    chance,
                )
        except Exception:
            logger.error(
                "检查高好感主动消息候选失败 conversation=%s",
                getattr(conversation, "id", None),
                exc_info=True,
            )


def process_pending_tasks():
    """
    【已全面升级】处理所有到期任务的核心函数。
    """
    if not ENABLE_COMMUNITY_BACKEND:
        logger.info("JOB_TASK_PROC: 心灵社区后端已下线，跳过任务队列处理。")
        return

    due_tasks = ai_task_table.get_due_tasks(limit=10)
    if not due_tasks:
        return

    logger.info(f"JOB_TASK_PROC: 发现 {len(due_tasks)} 个到期任务，开始处理...")

    for task in due_tasks:
        try:
            with chat_db.atomic() as transaction:
                try:
                    is_locked = ai_task_table.update_task_status(task.id, 'processing')
                    if not is_locked:
                        continue

                    logger.info(f"-> 正在处理任务 {task.id} (类型: {task.task_type})")

                    # --- 任务类型分发 ---
                    if task.task_type in ('reply', 'proactive_chat'):
                        logger.debug(f"任务 {task.id}: 步骤1 - 开始获取上下文...")
                        now = datetime.now(BEIJING_TZ)
                        today = now.date()
                        character = ai_character_table.get_character_by_id(task.character_id)
                        if task.task_type == 'reply':
                            ai_status_table.clear_transient_offline_status(task.character_id)
                        current_status = ai_status_table.get_current_status(task.character_id)
                        history = community_chat_table.get_conversation_history(task.user_id, task.character_id, limit=50)
                        memory_context = community_memory_table.get_prompt_context(task.user_id, task.character_id)
                        full_day_schedule = ai_status_table.get_schedule_for_date(task.character_id, today)

                        if not character or history is None:
                            error_details = []
                            if not character:
                                error_details.append(f"角色(character)未找到 (ID: {task.character_id})")
                            if history is None:
                                error_details.append("聊天历史(history)查询失败，可能存在数据库错误")
                            logger.warning(f"任务 {task.id} 失败: 获取上下文不完整。缺失或错误的部分: {', '.join(error_details)}")
                            ai_task_table.update_task_status(task.id, 'failed')
                            continue

                        logger.debug(f"任务 {task.id}: 步骤1 - 上下文获取成功。")

                        status_context = build_response_status_context(
                            current_status=current_status,
                            user_id=task.user_id,
                            character_id=task.character_id,
                            now=now,
                        )

                        if task.task_type == 'proactive_chat' and status_context.get("response_mode") == "night_soft":
                            logger.info(f"任务 {task.id}: 当前为夜间/睡眠模式，跳过主动消息，避免打扰用户。")
                            community_chat_table.update_conversation_state(
                                user_id=task.user_id,
                                character_id=task.character_id,
                                state='CONTINUOUS',
                                resumes_at=None
                            )
                            ai_task_table.update_task_status(task.id, 'done')
                            continue

                        if task.task_type == 'reply':
                            structured_response = generate_ai_response(
                                character_profile=character.profile,
                                current_ai_status=status_context,
                                conversation_history=history,
                                full_day_schedule=full_day_schedule,
                                current_beijing_time=now,
                                memory_context=memory_context,
                            )
                        else: # proactive_chat
                            structured_response = generate_proactive_message(
                                character_profile=character.profile,
                                current_ai_status=status_context,
                                conversation_history=history,
                                memory_context=memory_context,
                            )

                        if not (structured_response and structured_response.messages):
                            logger.warning(f"任务 {task.id} 失败: AI模型返回了空内容。")
                            if task.task_type == 'reply':
                                try:
                                    ai_status_table.mark_character_offline(task.character_id, now=now)
                                except Exception:
                                    logger.error(
                                        f"任务 {task.id}: 标记角色 {task.character_id} 为短时离线失败。",
                                        exc_info=True,
                                    )
                            ai_task_table.update_task_status(task.id, 'failed')
                            continue
                        
                        # 3. 保存消息
                        for msg in structured_response.messages:
                            save_ai_message_from_worker(task.user_id, task.character_id, msg)
                            time.sleep(random.uniform(1.0, 2.5))

                        # 4. 日程只影响回复风格，不再允许暂停对话。
                        community_chat_table.update_conversation_state(
                            user_id=task.user_id,
                            character_id=task.character_id,
                            state='CONTINUOUS',
                            resumes_at=None
                        )

                        try:
                            queued = community_memory_table.queue_memory_update_if_needed(
                                task.user_id,
                                task.character_id,
                                ai_task_table,
                            )
                            if queued:
                                logger.info(f"已为任务 {task.id} 后续排队记忆更新任务。")
                        except Exception:
                            logger.error(
                                f"任务 {task.id} 排队记忆更新任务失败。",
                                exc_info=True,
                            )

                        if task.task_type == 'reply':
                            try:
                                affinity_queued = community_chat_table.queue_favorability_update_if_needed(
                                    task.user_id,
                                    task.character_id,
                                    ai_task_table,
                                )
                                if affinity_queued:
                                    logger.info(f"已为任务 {task.id} 后续排队好感度更新任务。")
                            except Exception:
                                logger.error(
                                    f"任务 {task.id} 排队好感度更新任务失败。",
                                    exc_info=True,
                                )
                        
                        ai_task_table.update_task_status(task.id, 'done')
                        logger.info(f"✅ 聊天任务 {task.id} 处理成功。")

                    elif task.task_type == 'affinity_update':
                        character = ai_character_table.get_character_by_id(task.character_id)
                        conversation = community_chat_table.get_conversation(task.user_id, task.character_id)
                        if not character or not conversation:
                            logger.warning(f"任务 {task.id} 失败: 缺少角色或会话，无法更新好感度。")
                            ai_task_table.update_task_status(task.id, 'failed')
                            continue

                        all_messages = parse_message_history(conversation.messages_history)
                        message_count = len(all_messages)
                        last_count = community_chat_table.get_last_favorability_update_message_count(conversation)
                        if message_count - last_count < AFFINITY_UPDATE_INTERVAL:
                            logger.info(f"任务 {task.id}: 消息数未满 {AFFINITY_UPDATE_INTERVAL}，跳过好感度更新。")
                            ai_task_table.update_task_status(task.id, 'done')
                            continue

                        recent_block = all_messages[last_count:message_count]
                        if not any(message.get("role") == "user" for message in recent_block):
                            logger.info(f"任务 {task.id}: 本批消息没有用户消息，跳过好感度更新。")
                            ai_task_table.update_task_status(task.id, 'done')
                            continue

                        memory_context = community_memory_table.get_prompt_context(task.user_id, task.character_id)
                        favorability_history = community_chat_table.get_favorability_history(
                            task.user_id,
                            task.character_id,
                        )
                        assessment = assess_community_affinity(
                            character_profile=character.profile,
                            current_score=float(conversation.favorability or 0.0),
                            recent_messages=recent_block,
                            favorability_history=favorability_history,
                            memory_context=memory_context,
                        )
                        delta = apply_affinity_delta(
                            float(conversation.favorability or 0.0),
                            assessment.base_delta,
                            character.profile,
                        )
                        new_score = max(0.0, min(100.0, float(conversation.favorability or 0.0) + delta))
                        modifiers = affinity_speed_modifiers(character.profile)
                        reason = f"{assessment.reason}（MBTI {modifiers['mbti'] or '未知'} 倍率后变化 {delta:+.1f}）"
                        community_chat_table.update_favorability(
                            conversation.id,
                            new_score,
                            reason,
                            delta=delta,
                            base_delta=assessment.base_delta,
                            message_count=message_count,
                            analysis=assessment.analysis,
                            affinity_note=assessment.affinity_note,
                            interaction_quality=assessment.interaction_quality,
                            proactive_hint=assessment.proactive_hint,
                        )
                        community_memory_table.update_profile_affinity_note(
                            task.user_id,
                            task.character_id,
                            assessment.affinity_note,
                        )
                        ai_task_table.update_task_status(task.id, 'done')
                        logger.info(
                            "✅ 好感度任务 %s 处理成功。score %.1f -> %.1f, delta %.1f",
                            task.id,
                            conversation.favorability,
                            new_score,
                            delta,
                        )

                    elif task.task_type == 'memory_update':
                        character = ai_character_table.get_character_by_id(task.character_id)
                        if not character:
                            logger.warning(f"任务 {task.id} 失败: 角色不存在，无法更新记忆。")
                            ai_task_table.update_task_status(task.id, 'failed')
                            continue

                        profile_updated, summaries_updated = community_memory_table.update_memory_for_conversation(
                            user_id=task.user_id,
                            character_id=task.character_id,
                            character_profile=character.profile,
                        )
                        ai_task_table.update_task_status(task.id, 'done')
                        logger.info(
                            "✅ 记忆任务 %s 处理成功。profile=%s summaries=%s",
                            task.id,
                            profile_updated,
                            summaries_updated,
                        )

                    elif task.task_type == 'friend_request_response':
                        # (好友请求处理逻辑保持不变)
                        character = ai_character_table.get_character_by_id(task.character_id)
                        friend_request = Friendship.get_or_none((Friendship.user == task.user_id) & (Friendship.character == task.character_id))

                        if not all([character, friend_request]):
                            logger.warning(f"任务 {task.id} 失败: 无法找到好友请求的完整信息。")
                            ai_task_table.update_task_status(task.id, 'failed')
                            continue
                        
                        decision_response = generate_friend_request_decision(
                            character_profile=character.profile,
                            user_verification_message=friend_request.verification_message
                        )
                        
                        if decision_response:
                            new_status = 'accepted' if decision_response.decision else 'rejected'
                            friendship_table.update_request_status(friend_request.id, new_status)
                            
                            initial_msg = None
                            if new_status == 'accepted' and decision_response.initial_message:
                                initial_msg = decision_response.initial_message
                                community_chat_table.add_message(user_id=task.user_id, character_id=task.character_id, role='user', content=friend_request.verification_message)
                                community_chat_table.add_message(user_id=task.user_id, character_id=task.character_id, role='ai', content=initial_msg)
                            
                            ai_task_table.update_task_status(task.id, 'done')
                            logger.info(f"✅ 好友请求任务 {task.id} 处理完成。")
                        else:
                            logger.warning(f"任务 {task.id} 失败: AI未能生成好友请求决策。")
                            ai_task_table.update_task_status(task.id, 'failed')

                except Exception as inner_e:
                    logger.error(f"🚨 任务 {task.id} 在事务处理中发生错误，事务将回滚。", exc_info=True)
                    transaction.rollback()
                    ai_task_table.update_task_status(task.id, 'failed')
                    
        except Exception as outer_e:
            logger.error(f"🚨 处理任务 {task.id} 时发生不可预知的严重错误。", exc_info=True)
            if task and task.id:
                try:
                    with chat_db.atomic():
                       ai_task_table.update_task_status(task.id, 'failed')
                except Exception as update_err:
                    logger.critical(f"!!!!!! 任务 {task.id} 状态更新失败，可能导致任务卡死: {update_err}")
            continue

# ---------------------------------------------------
# 主程序入口 (已升级)
# ---------------------------------------------------
if __name__ == "__main__":
    if not ENABLE_COMMUNITY_BACKEND:
        logger.info("心灵社区后端已下线，background_worker 不启动任何社区调度任务。")
        raise SystemExit(0)
    
    all_dbs = [user_db, chat_db, status_db]
    for db in all_dbs:
        if db.is_closed():
            db.connect()
            logger.info(f"数据库 {db.database} 已连接。")

    scheduler = BackgroundScheduler(timezone=BEIJING_TZ)

    # 任务1：每日23点生成第二天的日程
    scheduler.add_job(
        schedule_daily_status_generation, 
        trigger='cron', 
        hour=23, 
        minute=0,
        id='daily_status_generation_job',
        replace_existing=True
    )
    # 任务2：每10秒处理一次到期的任务队列
    scheduler.add_job(
        process_pending_tasks, 
        trigger='interval', 
        seconds=10,
        id='pending_task_processing_job',
        replace_existing=True
    )
    
    # --- 【核心新增】任务3：每分钟检查一次是否有AI该回来聊天了 ---
    scheduler.add_job(
        check_for_resumable_conversations,
        trigger='interval',
        minutes=1,
        id='resume_conversation_job',
        replace_existing=True
    )
    # 任务4：高好感关系在冷却后有概率主动发起自然问候
    scheduler.add_job(
        check_for_high_affinity_proactive_conversations,
        trigger='interval',
        minutes=30,
        id='high_affinity_proactive_job',
        replace_existing=True
    )
    # --- ---------------------------------------------------- ---
    
    logger.info("后台工作进程 (`background_worker`) 已启动。")
    logger.info("已注册的计划任务:")
    scheduler.print_jobs()
    
    scheduler.start()

    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("收到退出信号，正在关闭调度器...")
        scheduler.shutdown()
        logger.info("调度器已关闭。正在断开数据库连接...")
        for db in all_dbs:
            if not db.is_closed():
                db.close()
                logger.info(f"数据库 {db.database} 已断开。")
        logger.info("后台进程已安全退出。")
