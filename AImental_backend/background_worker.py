# background_worker.py
import time
from datetime import datetime, timedelta, date
import random

# 导入 APScheduler，一个强大且轻量的任务调度库
from apscheduler.schedulers.background import BackgroundScheduler
import pytz # 用于处理时区

# --- 导入我们项目的所有组件 ---

# 1. 数据库连接 (确保导入所有需要用到的db实例)
from db import chat_db, status_db, user_db

# 2. 数据表管理类 (Table Access Objects)
from model.ai_character import ai_character_table
from model.ai_status import ai_status_table
from model.ai_task import ai_task_table
from model.chat_community import community_chat_table

# 3. AI能力生成器 (AI Generation Functions)
from generate_ai_status import generate_daily_schedule
from generate_community_response import generate_ai_response

# ---------------------------------------------------
# 核心工作函数 (Jobs for the Scheduler)
# ---------------------------------------------------

def schedule_daily_status_generation():
    """
    【每日规划任务】
    为所有AI角色生成第二天的完整行程。
    这个函数会被调度器设置为在每天固定的时间点执行一次。
    """
    target_date = date.today() + timedelta(days=1)
    print(f"[{datetime.now()}] JOB_STATUS_GEN: 开始为所有角色生成 {target_date} 的日程...")

    all_characters = ai_character_table.get_all_characters()
    for character in all_characters:
        try:
            print(f"  -> 正在处理角色: {character.name} ({character.id})")
            # a. 准备历史数据 (这里简化为摘要，实际可以从status表演化)
            # TODO: 实现一个函数，从ai_status表中查询过去7天的记录并生成摘要
            historical_summary = "这是一个过去七天的活动摘要示例，需要从数据库动态生成。"
            
            # b. 调用状态生成器
            daily_schedule = generate_daily_schedule(
                character_profile=character.profile,
                historical_summary=historical_summary,
                target_date=target_date
            )
            
            # c. 将生成的日程写入数据库
            if daily_schedule:
                for activity in daily_schedule.activities:
                    start_dt = datetime.strptime(f"{target_date} {activity.start_time}", "%Y-%m-%d %H:%M")
                    end_dt = datetime.strptime(f"{target_date} {activity.end_time}", "%Y-%m-%d %H:%M")
                    
                    ai_status_table.create_status(
                        character_id=character.id,
                        category=activity.category,
                        title=activity.description[:20], # 自动截取简短标题
                        description=activity.description,
                        delay_minutes=random.randint(5, 60), # TODO: 也可以让AI生成延迟
                        start_time=start_dt,
                        end_time=end_dt
                    )
                print(f"  ✅ 成功为 {character.name} 创建了 {len(daily_schedule.activities)} 条日程。")
            else:
                print(f"  ❌ 为 {character.name} 生成日程失败。")

        except Exception as e:
            print(f"  🚨 处理角色 {character.name} 时发生严重错误: {e}")
            continue # 即使一个角色失败，也要继续处理下一个


def process_pending_tasks():
    """
    【即时任务处理】
    高频率执行，获取并处理到期的任务（如回复用户）。
    """
    # print(f"[{datetime.now()}] JOB_TASK_PROC: 正在检查到期任务...")
    due_tasks = ai_task_table.get_due_tasks(limit=10) # 一次最多处理10个，防止拥堵
    
    if not due_tasks:
        return # 没有任务，直接返回

    print(f"[{datetime.now()}] JOB_TASK_PROC: 发现 {len(due_tasks)} 个到期任务，开始处理...")

    for task in due_tasks:
        try:
            # 关键步骤：立刻将任务标记为“处理中”，防止被其他进程重复获取
            is_locked = ai_task_table.update_task_status(task.id, 'processing')
            if not is_locked:
                print(f"  - 任务 {task.id} 可能已被其他进程锁定，跳过。")
                continue

            print(f"  -> 正在处理任务 {task.id} (类型: {task.task_type})")

            # --- 根据任务类型分发处理 ---
            if task.task_type == 'reply':
                # 1. 获取回复所需的全部上下文信息
                character = ai_character_table.get_character_by_id(task.character_id)
                current_status = ai_status_table.get_current_status(task.character_id)
                history = community_chat_table.get_conversation_history(task.user_id, task.character_id, limit=50)

                if not all([character, current_status]):
                    print(f"  ❌ 无法获取角色 {task.character_id} 的完整信息，任务失败。")
                    ai_task_table.update_task_status(task.id, 'failed')
                    continue
                
                # 2. 调用回复生成器
                structured_response = generate_ai_response(
                    character_profile=character.profile,
                    current_ai_status={
                        "status_title": current_status.status_title,
                        "status_description": current_status.status_description
                    },
                    conversation_history=history
                )

                # 3. 处理并发送回复
                if structured_response:
                    for message_content in structured_response.messages:
                        # a. 将AI的回复写入聊天记录
                        community_chat_table.add_message(
                            user_id=task.user_id,
                            character_id=task.character_id,
                            role='ai',
                            content=message_content
                        )
                        # b. TODO: 在此调用真实的消息推送服务 (如微信推送)
                        print(f"    >> 推送给用户 {task.user_id}: {message_content}")
                        time.sleep(random.uniform(1.5, 3.0)) # 模拟真实打字和网络延迟

                # 4. 任务完成
                ai_task_table.update_task_status(task.id, 'done')
                print(f"  ✅ 任务 {task.id} 处理完成。")

            # elif task.task_type == 'proactive_chat':
                # TODO: 在此处理主动发起聊天的逻辑
                # pass

        except Exception as e:
            print(f"  🚨 处理任务 {task.id} 时发生严重错误: {e}")
            ai_task_table.update_task_status(task.id, 'failed')
            continue

# ---------------------------------------------------
# 主程序入口 (Main Execution Block)
# ---------------------------------------------------
if __name__ == "__main__":
    
    # --- 1. 连接所有数据库 ---
    # 确保所有需要用到的数据库都已连接
    all_dbs = [user_db, chat_db, status_db]
    for db in all_dbs:
        if db.is_closed():
            db.connect()
            print(f"Database {db.database} connected.")

    # --- 2. 设置并启动调度器 ---
    # 定义时区为北京时间
    beijing_tz = pytz.timezone('Asia/Shanghai')
    
    scheduler = BackgroundScheduler(timezone=beijing_tz)

    # 添加“每日状态规划”任务，每天23:00执行
    scheduler.add_job(
        schedule_daily_status_generation, 
        trigger='cron', 
        hour=23, 
        minute=0,
        id='daily_status_generation_job',
        replace_existing=True
    )

    # 添加“即时任务处理”任务，每10秒执行一次
    scheduler.add_job(
        process_pending_tasks, 
        trigger='interval', 
        seconds=10,
        id='pending_task_processing_job',
        replace_existing=True
    )
    
    print("后台工作进程 (`background_worker`) 已启动。")
    print("已注册的任务:")
    scheduler.print_jobs()
    
    scheduler.start()

    # --- 3. 保持主线程运行 ---
    # 使用一个循环来保持脚本持续运行，直到手动中断 (Ctrl+C)
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("收到退出信号，正在关闭调度器...")
        scheduler.shutdown()
        print("调度器已关闭。正在断开数据库连接...")
        for db in all_dbs:
            if not db.is_closed():
                db.close()
                print(f"Database {db.database} disconnected.")
        print("后台进程已安全退出。")