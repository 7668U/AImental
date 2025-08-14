# main.py

from fastapi import FastAPI, Depends
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from fastapi.responses import FileResponse
# Load environment variables
load_dotenv()

# --- 1. Import Database Connections ---
# 您的 db.py 已更新，包含了所有数据库连接，此处无需改动。
from db import all_dbs, user_db, chat_db, assessment_db, status_db, feedback_db, promotion_db, airplane_db, note_db

# --- 2. Import All Peewee Models ---
# 您原有的模型
from model.user import User
from model.chat import Chat
from model.assessment import Scale, UserAssessment
from model.status import Checkin
from model.analysis import Analysis
from model.history_analysis import HistoryAnalysis
from model.feedback import Feedback
from model.promotion import TestRecord
from model.airplane import PaperAirplane, paper_airplane_table
from model.note import note_table, NoteItem

# --- 【新增】导入AI社区功能的所有新模型 ---
from model.ai_character import AICharacter
from model.ai_status import AiStatus
from model.ai_task import AITask
from model.chat_community import CommunityChat
from model.friendship import Friendship
# -----------------------------------------

# --- 3. Import All Routers ---
# 您原有的路由
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

# --- 【新增】导入AI社区功能的路由 ---
from router import ai_community as ai_community_router
# ------------------------------------


# ---------------------------------------------------
# FastAPI Application Instance
# ---------------------------------------------------
app = FastAPI(
    title="AI Psychologist API",
    description="The backend API for the AI Psychologist WeChat Mini Program, now with an AI Community!",
    version="1.1.0",
)

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 静态文件挂载 ---
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

if not os.path.exists("images"):
    os.makedirs("images")
app.mount("/images", StaticFiles(directory="images"), name="images")



# --- 在这里添加以下代码 ---

# 1. 挂载静态文件目录
# 这会让所有在 "root" 文件夹下的文件 (如 main.js) 都可以通过 /root/... 的URL被访问
app.mount("/root", StaticFiles(directory="root"), name="root")

# 2. 创建一个根路由来提供 index.html
# 这样当用户访问 http://127.0.0.1:8000/ 时，就会直接看到你的测试页面
@app.get("/", response_class=FileResponse)
async def read_index():
    return "root/index.html"
# ---------------------------------------------------
# Application Startup and Shutdown Events
# ---------------------------------------------------

@app.on_event("startup")
def on_startup():
    """
    Safely connects to databases, binds models, and creates tables.
    """
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
        TestRecord: promotion_db,
        PaperAirplane: airplane_db,
        NoteItem: note_db,

        # --- 【新增】将新的AI社区模型与它们的数据库连接进行映射 ---
        AICharacter: chat_db,
        CommunityChat: chat_db,
        AITask: chat_db,
        AiStatus: status_db,
        Friendship: user_db,
        # --------------------------------------------------------
    }

    print("🚀 Starting database initialization...")
    for model, db in model_db_mapping.items():
        if db.is_closed():
            db.connect()
        try:
            # Peewee的bind方法用于将模型类与数据库实例在运行时动态绑定
            model.bind(db, bind_refs=False, bind_backrefs=False)
            db.create_tables([model])
            print(f"✅ Table '{model._meta.table_name}' is ready in DB '{os.path.basename(db.database)}'")
        except Exception as e:
            print(f"❌ Error during table setup for '{model._meta.table_name}': {e}")
    print("✨ Database initialization process complete!")

    print("🚀 Checking if default data seeding is needed...")
    paper_airplane_table.add_default_airplanes_if_needed()
    # TODO: 您可以在这里添加一个用于“播种”初始AI角色的函数调用
    # from data.initial_characters import seed_characters
    # seed_characters()
    print("✨ Seeding process complete!")


@app.on_event("shutdown")
def on_shutdown():
    """
    Safely disconnects from all databases.
    """
    print("👋 Closing all database connections...")
    for db in all_dbs:
        if not db.is_closed():
            db.close()
    print("💤 All connections closed.")

# ---------------------------------------------------
# Mount all the sub-routers
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

# --- 【新增】挂载AI社区功能的API路由 ---
app.include_router(ai_community_router.router, prefix=API_PREFIX)
# ---------------------------------------

# ---------------------------------------------------
# Root endpoint for health checks
# # ---------------------------------------------------
# @app.get("/", tags=["Root"])
# def read_root():
#     """
#     A simple root endpoint to confirm the API is running.
#     """
#     return {"message": "Welcome to the AI Psychologist API! Visit /docs for documentation."}
