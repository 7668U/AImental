# background_worker.py

import time
from datetime import datetime, timedelta, date
import random
import json
from typing import Optional

# 导入 APScheduler
from apscheduler.schedulers.background import BackgroundScheduler
import pytz 
import redis

# --- 导入我们项目的所有组件 ---
from db import chat_db, status_db, user_db
from model.ai_character import ai_character_table
from model.ai_status import ai_status_table
from model.ai_task import ai_task_table
from model.friendship import friendship_table, Friendship
from model.chat_community import community_chat_table, ChatMessageModel

# --- 导入AI能力生成器 ---
from generate_ai_status import generate_daily_schedule
# 【重要】从 generate_community_response 导入两个函数
from generate_community_response import generate_ai_response, generate_proactive_message
from generate_friend_response import generate_friend_request_decision

# 导入我们全局配置好的日志记录器
from logger_config import logger

# 定义北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# --- Redis 同步客户端 ---
try:
    redis_client_sync = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client_sync.ping()
    logger.info("✅ 后台工作进程已成功连接到Redis。")
except redis.exceptions.ConnectionError as e:
    logger.error(f"❌ 后台工作进程无法连接到Redis: {e}")
    redis_client_sync = None

# ---------------------------------------------------
# 核心工作函数 (Jobs for the Scheduler)
# ---------------------------------------------------

def push_message_to_user_from_worker(user_id: str, character_id: str, message_content: str):
    """
    一个同步函数，负责将AI的回复存入数据库，然后打包一个包含“最新会话摘要”的
    情报包，通过Redis发布出去。(此函数逻辑保持不变)
    """
    if not redis_client_sync:
        logger.warning("Redis未连接，无法推送消息。")
        return

    new_msg_record = community_chat_table.add_message(
        user_id=user_id,
        character_id=character_id,
        role='ai',
        content=message_content
    )

    if not new_msg_record:
        logger.error(f"保存来自角色 {character_id} 的消息失败，无法推送。")
        return

    chat_summary_data = {
        "character_id": new_msg_record.character.id,
        "character_name": new_msg_record.character.name,
        "character_avatar_url": new_msg_record.character.avatar_url,
        "last_message_snippet": new_msg_record.last_message_snippet,
        "last_message_timestamp": new_msg_record.last_message_timestamp,
        "unread": not new_msg_record.user_has_peeked, 
        "favorability": new_msg_record.favorability
    }
    
    message_data = ChatMessageModel(
        role='ai',
        content=message_content,
        timestamp=new_msg_record.last_message_timestamp
    ).model_dump()
    
    payload = {
        "type": "new_message",
        "from_character_id": character_id,
        "message": message_data,
        "chat_summary": chat_summary_data
    }
    
    channel = f"ws_channel:{user_id}"
    redis_client_sync.publish(channel, json.dumps(payload))
    logger.debug(f"已通过Redis频道 '{channel}' 发布了包含完整摘要的消息。")
            
def push_friend_request_result_from_worker(user_id: str, character_id: str, status: str, initial_message: Optional[str] = None):
    """
    将好友请求的结果通过Redis发布出去。(此函数逻辑保持不变)
    """
    if not redis_client_sync:
        logger.warning("Redis未连接，无法推送好友请求结果。")
        return

    payload = {
        "type": "friend_request_result",
        "from_character_id": character_id,
        "status": status,
        "initial_message": initial_message
    }
    
    channel = f"ws_channel:{user_id}"
    redis_client_sync.publish(channel, json.dumps(payload))
    logger.debug(f"已通过Redis频道 '{channel}' 发布好友请求结果")
    
def schedule_daily_status_generation():
    """
    【已升级】为所有AI角色生成第二天的完整行程，并保存 focus_level。
    """
    target_date = date.today() + timedelta(days=1)
    logger.info(f"JOB_STATUS_GEN: 开始为所有角色生成 {target_date} 的日程...")

    all_characters = ai_character_table.get_all_characters()
    for character in all_characters:
        try:
            logger.info(f"-> 正在处理角色: {character.name} ({character.id})")
            # a. 准备历史数据 (未来可扩展)
            recent_history = [
                {"date": (date.today() - timedelta(days=1)).strftime('%Y-%m-%d'), "summary": "昨天似乎是休息的一天。"}
            ]
            
            # b. 调用状态生成器
            daily_schedule = generate_daily_schedule(
                character_profile=character.profile,
                recent_history=recent_history
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


def process_pending_tasks():
    """
    【已全面升级】处理所有到期任务的核心函数。
    """
    if not redis_client_sync:
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
                    if task.task_type == 'reply' or task.task_type == 'proactive_chat':
                        # 1. 获取上下文
                        character = ai_character_table.get_character_by_id(task.character_id)
                        current_status = ai_status_table.get_current_status(task.character_id)
                        history = community_chat_table.get_conversation_history(task.user_id, task.character_id, limit=30)
                        
                    if task.task_type == 'reply':
                        # --- 【哨兵日志 1】检查上下文获取 ---
                        logger.debug(f"任务 {task.id}: 步骤1 - 开始获取上下文...")
                        character = ai_character_table.get_character_by_id(task.character_id)
                        current_status = ai_status_table.get_current_status(task.character_id)
                        history = community_chat_table.get_conversation_history(task.user_id, task.character_id, limit=30)
                        
                        # ========================= 【核心调试修改】 =========================
                        if not all([character, current_status, history is not None]):
                            # 创建一个详细的错误诊断消息
                            error_details = []
                            if not character:
                                error_details.append(f"角色(character)未找到 (ID: {task.character_id})")
                            if not current_status:
                                error_details.append(f"当前状态(current_status)未找到 (角色ID: {task.character_id})，可能是日程未生成或已过期")
                            if history is None:
                                error_details.append("聊天历史(history)查询失败，可能存在数据库错误")
                            
                            # 记录包含了具体原因的警告
                            logger.warning(f"任务 {task.id} 失败: 获取上下文不完整。缺失或错误的部分: {', '.join(error_details)}")
                            
                            ai_task_table.update_task_status(task.id, 'failed')
                            continue
                        # =================================================================

                        logger.debug(f"任务 {task.id}: 步骤1 - 上下文获取成功。")
                        
                        # 2. 调用AI生成回复
                        status_context = {
                            "status_description": current_status.status_text,
                            "focus_level": current_status.focus_level
                        }
                        
                        if task.task_type == 'reply':
                            structured_response = generate_ai_response(
                                character_profile=character.profile,
                                current_ai_status=status_context,
                                conversation_history=history
                            )
                        else: # proactive_chat
                            structured_response = generate_proactive_message(
                                character_profile=character.profile,
                                current_ai_status=status_context,
                                conversation_history=history
                            )

                        if not (structured_response and structured_response.messages):
                            logger.warning(f"任务 {task.id} 失败: AI模型返回了空内容。")
                            ai_task_table.update_task_status(task.id, 'failed')
                            continue
                        
                        # 3. 推送消息
                        for msg in structured_response.messages:
                            push_message_to_user_from_worker(task.user_id, task.character_id, msg)
                            time.sleep(random.uniform(1.0, 2.5))

                        # 4. 【核心】根据AI指令更新对话微观状态
                        control = structured_response.control
                        delay_minutes = control.next_delay_minutes
                        
                        # 【硬规则】延迟上限器
                        if current_status.focus_level == 'HIGH' and delay_minutes > 20:
                            logger.warning(f"AI为HIGH专注状态请求了过长延迟({delay_minutes}分钟)，系统强制修正为10分钟。")
                            delay_minutes = 10
                        
                        if control.next_state == 'PAUSE_CHAT':
                            resume_time = datetime.now(BEIJING_TZ) + timedelta(minutes=delay_minutes)
                            community_chat_table.update_conversation_state(
                                user_id=task.user_id, character_id=task.character_id,
                                state='PAUSED', resumes_at=resume_time
                            )
                            logger.info(f"任务 {task.id}: AI决定暂停对话，预计在 {resume_time} 回归。")
                        else: # CONTINUE_CHAT
                            community_chat_table.update_conversation_state(
                                user_id=task.user_id, character_id=task.character_id,
                                state='CONTINUOUS', resumes_at=None
                            )
                        
                        ai_task_table.update_task_status(task.id, 'done')
                        logger.info(f"✅ 聊天任务 {task.id} 处理成功。")

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
                            
                            push_friend_request_result_from_worker(
                                user_id=task.user_id, character_id=task.character_id,
                                status=new_status, initial_message=initial_msg
                            )
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
