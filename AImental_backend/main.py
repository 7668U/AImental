# main.py

from fastapi import FastAPI, Depends
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

# Load environment variables
load_dotenv()

# --- 1. Import Database Connections ---
from db import all_dbs, user_db, chat_db, assessment_db, status_db, feedback_db, promotion_db
from model.airplane import airplane_db  # 【新增】导入纸飞机数据库

# --- 2. Import All Peewee Models ---
from model.user import User
from model.chat import Chat
from model.assessment import Scale, UserAssessment
from model.status import Checkin
from model.analysis import Analysis  # 【新增】导入 Analysis 模型
from model.history_analysis import HistoryAnalysis
from model.feedback import Feedback  # 【新增】导入 Feedback 模型
from model.promotion import TestRecord  # 【新增】导入 promotion_table
from model.airplane import PaperAirplane, paper_airplane_table  # 【修改】导入纸飞机模型和表实例和默认数据函数

# ✅ 按新风格导入 Note 模块（Table 实例 + 模型）
from model.note import note_table, Notebook, NoteItem

# --- 3. Import All Routers ---
from router import user as user_router
from router import chat as chat_router
from router import assessment as assessment_router
from router import status as status_router
from router import system as system_router
from router import analysis as analysis_router  # 【新增】导入 analysis 路由
from router import history_analysis as history_analysis_router  # 【新增】导入 history_analysis 路由
from router import feedback as feedback_router  # 【新增】导入 feedback 路由
from router import promotion as promotion_router  # 【新增】导入 promotion 路由
from router import airplane as airplane_router  # 【新增】导入纸飞机路由
from router import note as note_router  # Added note_router

# ---------------------------------------------------
# FastAPI Application Instance
# ---------------------------------------------------
app = FastAPI(
    title="AI Psychologist API",
    description="The backend API for the AI Psychologist WeChat Mini Program.",
    version="1.0.0",
)

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ---------------------------------------------------
# Application Startup and Shutdown Events
# ---------------------------------------------------

@app.on_event("startup")
def on_startup():
    """
    Safely connects to databases, binds models, and creates tables.
    """
    # 【修改】将 Analysis 模型添加到映射中，并把 Notebook/NoteItem 纳入统一初始化流程
    model_db_mapping = {
        User: user_db,
        Feedback: feedback_db,   # 【新增】Feedback 模型使用 feedback_db
        Chat: chat_db,
        Scale: assessment_db,
        UserAssessment: assessment_db,
        HistoryAnalysis: assessment_db,
        Checkin: status_db,
        Analysis: status_db,     # Analysis 数据也存在 status_db 中
        TestRecord: promotion_db,
        PaperAirplane: airplane_db,

        # ✅ 新增：记事簿相关模型走与其它模型相同的初始化流程
        Notebook: note_table.db,
        NoteItem: note_table.db,
    }

    print("🚀 Starting database initialization...")
    for model, db in model_db_mapping.items():
        if db.is_closed():
            db.connect()

        try:
            # 与你原有风格一致：bind + create_tables（已存在则跳过）
            model.bind(db, bind_refs=False, bind_backrefs=False)
            db.create_tables([model])
            print(f"✅ Table '{model._meta.table_name}' is ready in DB '{db.database}'")
        except Exception as e:
            print(f"❌ Error during table setup for '{model._meta.table_name}': {e}")

    # ❌【删除】旧版的 note_model.create_tables()（新风格里已不存在）
    # print("🚀 Initializing cabinet database...")
    # note_model.create_tables()
    # print("✅ Cabinet database tables are ready!")

    print("✨ Database initialization process complete!")

    # --- 5. Seed Default Data ---
    print("🚀 Checking if default data seeding is needed...")
    paper_airplane_table.add_default_airplanes_if_needed()
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

app.include_router(user_router.router, prefix=API_PREFIX)
app.include_router(chat_router.router, prefix=API_PREFIX)
app.include_router(assessment_router.router, prefix=API_PREFIX)
app.include_router(status_router.router, prefix=API_PREFIX)
app.include_router(system_router.router, prefix=API_PREFIX)
app.include_router(analysis_router.router, prefix=API_PREFIX)           # 【新增】注册 analysis 路由
app.include_router(history_analysis_router.router, prefix=API_PREFIX)   # 【新增】注册 history_analysis 路由
app.include_router(feedback_router.router, prefix=API_PREFIX)           # 【新增】注册 feedback 路由
app.include_router(promotion_router.router, prefix=API_PREFIX)          # 【新增】注册 promotion 路由
app.include_router(airplane_router.router, prefix=API_PREFIX)           # 【新增】注册纸飞机路由
app.include_router(note_router.router, prefix=API_PREFIX)               # Added note router

# ---------------------------------------------------
# Root endpoint for health checks
# ---------------------------------------------------
@app.get("/", tags=["Root"])
def read_root():
    """
    A simple root endpoint to confirm the API is running.
    """
    return {"message": "Welcome to the AI Psychologist API! Visit /docs for documentation."}
