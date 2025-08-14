import time
from datetime import datetime, timedelta, date
import random
import asyncio
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
from generate_community_response import generate_ai_response
from generate_friend_response import generate_friend_request_decision

# 【核心】导入我们全局配置好的日志记录器
from logger_config import logger

# 定义北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# --- Redis 同步客户端 ---
try:
    # 【改动】使用decode_responses=True，让Redis返回字符串而不是字节
    redis_client_sync = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client_sync.ping()
    # 【改动】使用 logger.info 替代 print
    logger.info("✅ 后台工作进程已成功连接到Redis。")
except redis.exceptions.ConnectionError as e:
    # 【改动】使用 logger.error 替代 print
    logger.error(f"❌ 后台工作进程无法连接到Redis: {e}")
    redis_client_sync = None

# ---------------------------------------------------
# 核心工作函数 (Jobs for the Scheduler)
# ---------------------------------------------------

# background_worker.py

def push_message_to_user_from_worker(user_id: str, character_id: str, message_content: str):
    """
    【“用户窥视”策略版】
    一个同步函数，负责将AI的回复存入数据库，然后打包一个包含“最新会话摘要”的
    情报包，通过Redis发布出去。
    """
    if not redis_client_sync:
        logger.warning("Redis未连接，无法推送消息。")
        return

    # 步骤1：保存新消息。
    # 我们刚刚修改过的 add_message 函数会自动将 user_has_peeked 设为 False，
    # 并返回包含了这个最新状态的会话对象。
    new_msg_record = community_chat_table.add_message(
        user_id=user_id,
        character_id=character_id,
        role='ai',
        content=message_content
    )

    if not new_msg_record:
        logger.error(f"保存来自角色 {character_id} 的消息失败，无法推送。")
        return

    # 步骤2：准备“会话列表摘要”数据，这是给 chat-list 页面用的。
    # 这个摘要现在包含了正确的未读状态。
    chat_summary_data = {
        "character_id": new_msg_record.character.id,
        "character_name": new_msg_record.character.name,
        "character_avatar_url": new_msg_record.character.avatar_url,
        "last_message_snippet": new_msg_record.last_message_snippet,
        "last_message_timestamp": new_msg_record.last_message_timestamp,
        # 【核心】根据我们新的 user_has_peeked 字段计算未读状态
        # 因为 AI 刚发了消息，user_has_peeked 是 False，所以 not user_has_peeked 就是 True
        "unread": not new_msg_record.user_has_peeked, 
        "favorability": new_msg_record.favorability
    }
    
    # 步骤3：准备“单条消息”数据，这是给 chat-interface 页面用的。
    message_data = ChatMessageModel(
        role='ai',
        content=message_content,
        timestamp=new_msg_record.last_message_timestamp
    ).model_dump()
    
    # 步骤4：构造最终的、包含所有信息的载荷(payload)
    payload = {
        "type": "new_message",
        "from_character_id": character_id,
        "message": message_data,
        "chat_summary": chat_summary_data
    }
    
    # 步骤5：通过Redis发布
    channel = f"ws_channel:{user_id}"
    redis_client_sync.publish(channel, json.dumps(payload))
    logger.debug(f"已通过Redis频道 '{channel}' 发布了包含完整摘要的消息。")
            
def push_friend_request_result_from_worker(user_id: str, character_id: str, status: str, initial_message: Optional[str] = None):
    """
    一个同步函数，负责将好友请求的结果通过Redis发布出去。
    """
    if not redis_client_sync:
        # 【改动】使用 logger.warning 替代 print
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
    # 【改动】使用 logger.debug 替代 print
    logger.debug(f"已通过Redis频道 '{channel}' 发布好友请求结果")
    
def schedule_daily_status_generation():
    """
    【每日规划任务】为所有AI角色生成第二天的完整行程。
    """
    target_date = date.today() + timedelta(days=1)
    # 【改动】使用 logger.info 替代 print
    logger.info(f"JOB_STATUS_GEN: 开始为所有角色生成 {target_date} 的日程...")

    all_characters = ai_character_table.get_all_characters()
    for character in all_characters:
        try:
            # 【改动】使用 logger.info 替代 print
            logger.info(f"-> 正在处理角色: {character.name} ({character.id})")
            # a. 准备历史数据
            # TODO: 实现一个函数，从ai_status表中查询过去7天的记录并生成摘要
            recent_history = [
                {"date": (date.today() - timedelta(days=1)).strftime('%Y-%m-%d'), "summary": "全天在实验室整理数据，晚上阅读了关于苔藓植物的文献直到深夜。"}
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
                    
                    ai_status_table.create_status(
                        character_id=character.id,
                        category=activity['status_category'],
                        text=activity['status_description'],
                        start_time=start_dt,
                        end_time=end_dt,
                        # 【重要】确保这个参数被传递，它来自您的 generate_ai_status.py
                        reply_delay_minutes=activity.get('reply_delay_minutes', 5) 
                    )
                # 【改动】使用 logger.info 替代 print
                logger.info(f"✅ 成功为 {character.name} 创建了 {len(daily_schedule)} 条日程。")
            else:
                # 【改动】使用 logger.warning 替代 print
                logger.warning(f"❌ 为 {character.name} 生成日程失败。")

        except Exception as e:
            # 【改动】使用 logger.error 替代 print，并记录完整错误信息
            logger.error(f"🚨 处理角色 {character.name} 时发生严重错误: {e}", exc_info=True)
            continue


def process_pending_tasks():
    """
    【真正终极无敌完整版】
    - 完整保留了'reply'和'friend_request_response'的所有逻辑。
    - 为所有分支添加了详细的哨兵日志和错误捕获。
    - 使用数据库事务确保操作的原子性。
    """
    if not redis_client_sync:
        return

    due_tasks = ai_task_table.get_due_tasks(limit=10)
    if not due_tasks:
        return

    logger.info(f"JOB_TASK_PROC: 发现 {len(due_tasks)} 个到期任务，开始处理...")

    for task in due_tasks:
        try:
            # 【健壮性】为每个任务的处理过程都包裹一个数据库事务
            with chat_db.atomic() as transaction:
                try:
                    is_locked = ai_task_table.update_task_status(task.id, 'processing')
                    if not is_locked:
                        continue

                    logger.info(f"-> 正在处理任务 {task.id} (类型: {task.task_type})")

                    # --- 任务类型分发 ---
                    if task.task_type == 'reply':
                        # --- 【哨兵日志 1】检查上下文获取 ---
                        logger.debug(f"任务 {task.id}: 步骤1 - 开始获取上下文...")
                        character = ai_character_table.get_character_by_id(task.character_id)
                        current_status = ai_status_table.get_current_status(task.character_id)
                                            # ========================= 【新增的详细状态检查日志】 =========================
                        if current_status:
                            # 如果成功获取到状态，就打印它的所有关键信息
                            logger.debug(
                                f"【状态检查】任务 {task.id}: 成功获取到当前状态。\n"
                                f"    - 状态ID: {current_status.id}\n"
                                f"    - 状态分类: {current_status.status_category}\n"
                                f"    - 状态文本: {current_status.status_text}\n"
                                f"    - 开始时间: {current_status.start_time}\n"
                                f"    - 结束时间: {current_status.end_time}\n"
                                f"    - 当前时间: {datetime.now(BEIJING_TZ)}"
                            )
                        else:
                            # 如果没有获取到，就明确地告诉我们它返回了 None
                            logger.debug(f"【状态检查】任务 {task.id}: 未获取到任何当前状态 (get_current_status 返回 None)。")
                        history = community_chat_table.get_conversation_history(task.user_id, task.character_id, limit=30)
                        
                        if not all([character, current_status, history is not None]):
                            logger.warning(f"任务 {task.id} 失败: 获取上下文不完整。 "
                                         f"角色: {'OK' if character else '缺失'}, "
                                         f"状态: {'OK' if current_status else '缺失'}, "
                                         f"历史: {'OK' if history is not None else '缺失'}")
                            ai_task_table.update_task_status(task.id, 'failed')
                            continue
                        logger.debug(f"任务 {task.id}: 步骤1 - 上下文获取成功。")

                        # --- 【哨兵日志 2】检查AI响应生成 ---
                        logger.debug(f"任务 {task.id}: 步骤2 - 开始调用AI生成回复...")
                        structured_response = None
                        try:
                            structured_response = generate_ai_response(
                                character_profile=character.profile,
                                current_ai_status={"status_description": current_status.status_text},
                                conversation_history=history
                            )
                        except Exception as llm_error:
                            logger.error(f"任务 {task.id} 失败: 调用AI模型(generate_ai_response)时发生异常: {llm_error}", exc_info=True)
                            ai_task_table.update_task_status(task.id, 'failed')
                            continue
                        
                        if not (structured_response and structured_response.messages):
                            logger.warning(f"任务 {task.id} 失败: AI模型返回了空内容或无效结构。")
                            ai_task_table.update_task_status(task.id, 'failed')
                            continue
                        logger.debug(f"任务 {task.id}: 步骤2 - AI成功生成 {len(structured_response.messages)} 条回复。")

                        # --- 【哨兵日志 3】检查消息推送 ---
                        logger.debug(f"任务 {task.id}: 步骤3 - 开始推送 {len(structured_response.messages)} 条消息...")
                        for i, message_content in enumerate(structured_response.messages):
                            logger.debug(f"任务 {task.id}: 推送第 {i+1} 条消息...")
                            push_message_to_user_from_worker(task.user_id, task.character_id, message_content)
                            time.sleep(random.uniform(1.0, 2.5))
                        
                        logger.debug(f"任务 {task.id}: 步骤3 - 消息推送完成。")

                        ai_task_table.update_task_status(task.id, 'done')
                        logger.info(f"✅ 回复任务 {task.id} 处理成功。")
                    
                    elif task.task_type == 'friend_request_response':
                        logger.debug(f"任务 {task.id}: 步骤1 - 开始处理好友请求...")
                        character = ai_character_table.get_character_by_id(task.character_id)
                        friend_request = Friendship.get_or_none((Friendship.user == task.user_id) & (Friendship.character == task.character_id))

                        if not all([character, friend_request]):
                            logger.warning(f"任务 {task.id} 失败: 无法找到好友请求的完整信息。")
                            ai_task_table.update_task_status(task.id, 'failed')
                            continue
                        logger.debug(f"任务 {task.id}: 步骤1 - 好友请求信息获取成功。")
                        
                        logger.debug(f"任务 {task.id}: 步骤2 - 开始调用AI生成决策...")
                        decision_response = None
                        try:
                            decision_response = generate_friend_request_decision(
                                character_profile=character.profile,
                                user_verification_message=friend_request.verification_message
                            )
                        except Exception as llm_error:
                            logger.error(f"任务 {task.id} 失败: 调用AI模型(generate_friend_request_decision)时发生异常: {llm_error}", exc_info=True)
                            ai_task_table.update_task_status(task.id, 'failed')
                            continue

                        if decision_response:
                            logger.debug(f"任务 {task.id}: 步骤2 - AI决策生成成功。")
                            new_status = 'accepted' if decision_response.decision else 'rejected'
                            friendship_table.update_request_status(friend_request.id, new_status)
                            logger.info(f"任务 {task.id}: AI决定: {new_status}。好友关系数据库已更新。")

                            initial_msg = None
                            if new_status == 'accepted' and decision_response.initial_message:
                                initial_msg = decision_response.initial_message
                                community_chat_table.add_message(
                                    user_id=task.user_id, character_id=task.character_id,
                                    role='user', content=friend_request.verification_message
                                )
                                community_chat_table.add_message(
                                    user_id=task.user_id, character_id=task.character_id,
                                    role='ai', content=initial_msg
                                )
                                logger.info(f"任务 {task.id}: 初始聊天记录创建完毕。")
                            
                            push_friend_request_result_from_worker(
                                user_id=task.user_id,
                                character_id=task.character_id,
                                status=new_status,
                                initial_message=initial_msg
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
# 主程序入口 (Main Execution Block)
# ---------------------------------------------------
if __name__ == "__main__":
    
    all_dbs = [user_db, chat_db, status_db]
    for db in all_dbs:
        if db.is_closed():
            db.connect()
            # 【改动】使用 logger.info 替代 print
            logger.info(f"数据库 {db.database} 已连接。")

    scheduler = BackgroundScheduler(timezone=BEIJING_TZ)

    scheduler.add_job(
        schedule_daily_status_generation, 
        trigger='cron', 
        hour=23, 
        minute=0,
        id='daily_status_generation_job',
        replace_existing=True
    )
    scheduler.add_job(
        process_pending_tasks, 
        trigger='interval', 
        seconds=10,
        id='pending_task_processing_job',
        replace_existing=True
    )
    
    # 【改动】使用 logger.info 替代 print
    logger.info("后台工作进程 (`background_worker`) 已启动。")
    logger.info("已注册的计划任务:")
    # Apscheduler 的 print_jobs 会直接输出到 stdout，这里我们保留它用于直观查看
    scheduler.print_jobs()
    
    scheduler.start()

    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        # 【改动】使用 logger.info 替代 print
        logger.info("收到退出信号，正在关闭调度器...")
        scheduler.shutdown()
        logger.info("调度器已关闭。正在断开数据库连接...")
        for db in all_dbs:
            if not db.is_closed():
                db.close()
                logger.info(f"数据库 {db.database} 已断开。")
        logger.info("后台进程已安全退出。")