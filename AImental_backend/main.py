from fastapi import FastAPI, Request
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from fastapi.responses import FileResponse
from datetime import date, datetime, timedelta
import pytz

# Load environment variables
load_dotenv()
from feature_flags import ENABLE_COMMUNITY_BACKEND

# --- 1. 导入数据库连接 (保持不变) ---
from db import all_dbs, user_db, chat_db, assessment_db, status_db, feedback_db, promotion_db, airplane_db, note_db

# --- 2. 导入所有模型 (保持不变) ---
from model.user import User
from model.chat import Chat
from model.assessment import Scale, UserAssessment
from model.status import Checkin
from model.analysis import Analysis
from model.emotion_color_card import EmotionColorCardCache
from model.history_analysis import HistoryAnalysis
from model.feedback import Feedback
from model.promotion import TestRecord
from model.airplane import PaperAirplane, paper_airplane_table
from model.note import note_table, NoteItem
if ENABLE_COMMUNITY_BACKEND:
    from model.ai_character import AICharacter, ai_character_table
    from model.ai_status import AiStatus, ai_status_table
    from model.ai_task import AITask
    from model.chat_community import CommunityChat, community_chat_table
    from model.community_memory import CharacterUserMemory, CommunityHistorySummary
    from model.friendship import Friendship
    from generate_ai_status import generate_daily_schedule

# --- 3. 导入所有路由 (保持不变) ---
from router import user as user_router
from router import chat as chat_router
from router import assessment as assessment_router
from router import status as status_router
from router import system as system_router
from router import analysis as analysis_router
from router import history_analysis as history_analysis_router
from router import feedback as feedback_router
from router import promotion as promotion_router
from router import airplane as airplane_router
from router import note as note_router
if ENABLE_COMMUNITY_BACKEND:
    from router import ai_community as ai_community_router

# ---------------------------------------------------
# FastAPI 应用实例
# ---------------------------------------------------
app = FastAPI(
    title="AI Psychologist API",
    description="The backend API for the AI Psychologist WeChat Mini Program, now with an AI Community!",
    version="1.2.0",  # 版本升级！
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 静态文件挂载 (保持不变) ---
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

if not os.path.exists("images"):
    os.makedirs("images")
app.mount("/images", StaticFiles(directory="images"), name="images")

if not os.path.exists("root"):
    os.makedirs("root")
app.mount("/root", StaticFiles(directory="root"), name="root")

@app.get("/", response_class=FileResponse)
async def read_index():
    return "root/index.html"

# =================================================================
# --- 【核心终极修复】数据库连接管理中间件 ---
# =================================================================
@app.middleware("http")
async def db_connection_middleware(request: Request, call_next):
    """
    这个中间件是解决问题的关键。
    它会在每一个API请求进来时，为所有数据库建立连接。
    在请求处理完毕后，无论成功或失败，都会关闭所有连接。
    这强制FastAPI在每次请求时都从数据库文件重新读取状态，
    从而能“看到”后台worker进程对数据库的修改。
    """
    try:
        for db in all_dbs:
            if db.is_closed():
                db.connect()
        response = await call_next(request)
    finally:
        for db in all_dbs:
            if not db.is_closed():
                db.close()
    return response

# ---------------------------------------------------
# 应用启动事件
# ---------------------------------------------------


def check_and_generate_today_schedules():
    """
    【已修正并增加重试机制版】
    在系统启动时，检查所有AI角色是否已生成当天的日程。
    如果首次生成失败，会自动重试一次。
    强制使用北京时间来定义“今天”。
    """
    if not ENABLE_COMMUNITY_BACKEND:
        print("ℹ️ [Startup Check]: 心灵社区后端已下线，跳过AI角色日程检查与生成。")
        return

    # --- 【核心修正】在这里统一定义“今天” ---
    BEIJING_TZ = pytz.timezone('Asia/Shanghai')
    today_in_beijing = datetime.now(BEIJING_TZ).date()
    # --- ------------------------------------ ---

    print(f"🤖 [Startup Check]: 正在检查AI角色在北京时间 {today_in_beijing} 的日程...")
    
    all_characters = ai_character_table.get_all_characters()
    if not all_characters:
        print("ℹ️ [Startup Check]: 未发现任何AI角色，跳过日程检查。")
        return

    for character in all_characters:
        try:
            has_today_schedule = ai_status_table.has_schedule_for_date(character.id, today_in_beijing)
            
            if has_today_schedule:
                print(f"✅ 角色 '{character.name}' 在 {today_in_beijing} 的日程已存在，无需生成。")
                continue

            print(f"⚠️ 角色 '{character.name}' 缺少 {today_in_beijing} 的日程，现在开始生成...")
            
            yesterday_in_beijing = today_in_beijing - timedelta(days=1)
            recent_history = [
                {"date": yesterday_in_beijing.strftime('%Y-%m-%d'), "summary": "昨天似乎是休息的一天。"}
            ]
            
            # --- 【核心修改点：增加重试逻辑】 ---
            daily_schedule = None
            max_attempts = 2  # 设置最大尝试次数（首次 + 1次重试）
            for attempt in range(max_attempts):
                print(f"   [第 {attempt + 1}/{max_attempts} 次尝试] 正在为 '{character.name}' 生成日程...")
                
                # 调用生成函数
                generated_data = generate_daily_schedule(
                    character_profile=character.profile,
                    recent_history=recent_history,
                    target_date=today_in_beijing
                )
                
                # 检查生成结果是否有效（不为None且不为空列表）
                if generated_data:
                    daily_schedule = generated_data
                    print(f"   [第 {attempt + 1} 次尝试] 成功获取到日程。")
                    break  # 成功，跳出重试循环
                else:
                    print(f"   [第 {attempt + 1} 次尝试] 生成失败。")
            # --- 【重试逻辑结束】 ---

            if daily_schedule:
                for activity in daily_schedule:
                    start_dt = BEIJING_TZ.localize(datetime.strptime(f"{today_in_beijing} {activity['start_time']}", "%Y-%m-%d %H:%M"))
                    end_dt = BEIJING_TZ.localize(datetime.strptime(f"{today_in_beijing} {activity['end_time']}", "%Y-%m-%d %H:%M"))
                    
                    ai_status_table.create_status(
                        character_id=character.id,
                        category=activity['status_category'],
                        text=activity['status_description'],
                        start_time=start_dt,
                        end_time=end_dt,
                        reply_delay_minutes=activity.get('reply_delay_minutes', 5),
                        focus_level=activity.get('focus_level', 'LOW') 
                    )
                print(f"✅ 成功为 '{character.name}' 补生成了 {len(daily_schedule)} 条今日日程。")

            else:
                # 只有在所有尝试都失败后，才打印这条最终的失败信息
                print(f"❌ 经过 {max_attempts} 次尝试后，为 '{character.name}' 补生成今日日程仍然失败。")

        except Exception as e:
            print(f"🚨 在为角色 '{character.name}' 检查或生成日程时发生严重错误: {e}")

@app.on_event("startup")
def on_startup():
    """
    【最终修正版】
    应用启动时，此函数只负责一次性的初始化工作，如创建表和播种数据。
    它会临时连接数据库，完成工作后立即断开，将后续的连接管理完全交给中间件。
    """
    # 1. 定义所有模型与它们对应的数据库连接
    # (这个映射字典在你原来的代码里已经是正确的)
    model_db_mapping = {
        # 您原有的模型映射
        User: user_db,
        Feedback: feedback_db,
        Chat: chat_db,
        Scale: assessment_db,
        UserAssessment: assessment_db,
        HistoryAnalysis: assessment_db,
        Checkin: status_db,
        Analysis: status_db,
        EmotionColorCardCache: status_db,
        TestRecord: promotion_db,
        PaperAirplane: airplane_db,
        NoteItem: note_db,
    }
    if ENABLE_COMMUNITY_BACKEND:
        model_db_mapping.update({
            # AI社区模型映射
            AICharacter: chat_db,
            CommunityChat: chat_db,
            CharacterUserMemory: chat_db,
            CommunityHistorySummary: chat_db,
            AITask: chat_db,
            AiStatus: status_db,
            Friendship: chat_db,
        })

    # 2. 【核心步骤1】在所有操作开始前，为每个【唯一】的数据库对象建立临时连接
    print("🚀 [Startup]: 正在建立临时数据库连接...")
    for db in all_dbs:
        if db.is_closed():
            db.connect()
    print("✅ [Startup]: 临时数据库连接已建立。")

    # 3. 【核心步骤2】现在数据库都已连接，安全地执行所有一次性启动任务
    print("🚀 [Startup]: 开始创建数据库表...")
    for model, db in model_db_mapping.items():
        try:
            db.create_tables([model], safe=True)
            print(f"✅ 表 '{model._meta.table_name}' 已准备就绪。")
        except Exception as e:
            print(f"❌ 创建表 '{model._meta.table_name}' 时发生错误: {e}")
    print("✨ [Startup]: 所有数据库表创建完成！")

    try:
        updated_rows = (User
                        .update({User.allow_ai_read_data: True})
                        .where(User.allow_ai_read_data == False)
                        .execute())
        print(f"✅ [Startup]: 已将 {updated_rows} 个用户的个性化陪伴权限默认开启。")
    except Exception as e:
        print(f"❌ 初始化个性化陪伴权限时发生错误: {e}")

    if ENABLE_COMMUNITY_BACKEND:
        try:
            reset_rows = community_chat_table.reset_uninitialized_favorability()
            print(f"✅ [Startup]: 已将 {reset_rows} 个未初始化社区会话好感度重置为 0。")
        except Exception as e:
            print(f"❌ 初始化社区会话好感度时发生错误: {e}")

    print("🚀 [Startup]: 开始执行数据播种和日程检查...")
    paper_airplane_table.add_default_airplanes_if_needed()
    if ENABLE_COMMUNITY_BACKEND:
        ai_character_table.create_default_character_if_not_exists() # 确保默认角色存在
        check_and_generate_today_schedules()
    else:
        print("ℹ️ [Startup]: 心灵社区后端已下线，跳过AI角色播种与日程补生成。")
    print("✨ [Startup]: 数据播种和日程检查完成！")

    # 4. 【核心步骤3】在启动任务的最后，关闭所有临时连接
    print("💤 [Startup]: 正在关闭临时数据库连接...")
    for db in all_dbs:
        if not db.is_closed():
            db.close()
    print("👍 [Startup]: 服务准备就绪！连接已交由中间件按需管理。")

# 【改动】移除 on_shutdown 事件，因为中间件已完美处理连接关闭，不再需要全局关闭钩子。

# ---------------------------------------------------
# 挂载所有路由 (保持不变)
# ---------------------------------------------------
API_PREFIX = "/api/v1"

# 您原有的路由
app.include_router(user_router.router, prefix=API_PREFIX)
app.include_router(chat_router.router, prefix=API_PREFIX)
app.include_router(assessment_router.router, prefix=API_PREFIX)
app.include_router(status_router.router, prefix=API_PREFIX)
app.include_router(system_router.router, prefix=API_PREFIX)
app.include_router(analysis_router.router, prefix=API_PREFIX)
app.include_router(history_analysis_router.router, prefix=API_PREFIX)
app.include_router(feedback_router.router, prefix=API_PREFIX)
app.include_router(promotion_router.router, prefix=API_PREFIX)
app.include_router(airplane_router.router, prefix=API_PREFIX)
app.include_router(note_router.router, prefix=API_PREFIX)
# AI社区路由：通过 ENABLE_COMMUNITY_BACKEND 控制是否注册社区接口。
if ENABLE_COMMUNITY_BACKEND:
    app.include_router(ai_community_router.router, prefix=API_PREFIX)
