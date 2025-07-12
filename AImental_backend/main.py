# main.py

from fastapi import FastAPI
from dotenv import load_dotenv


load_dotenv() 
# Import all database connection objects from db.py
from db import all_dbs, user_db, chat_db, assessment_db, status_db

# Import all your Peewee models from the 'model' directory
from model.user import User
from model.chat import Chat
from model.assessment import Assessment
from model.status import Checkin

# Import all the individual routers from your 'router' directory
from router import user as user_router
from router import chat as chat_router
from router import assessment as assessment_router
from router import status as status_router
from fastapi.middleware.cors import CORSMiddleware # 1. 导入CORS中间件
import os
from fastapi.staticfiles import StaticFiles # 1. 导入这个

# ---------------------------------------------------
# 1. Create the main FastAPI application instance
# ---------------------------------------------------
app = FastAPI(
    title="AI Psychologist API",
    description="The backend API for the AI Psychologist WeChat Mini Program.",
    version="1.0.0",
)

# 2. 在这里添加 CORS 中间件配置
app.add_middleware(
    CORSMiddleware,
    # 允许所有来源的请求。对于本地开发，使用 "*" 是最简单的。
    # 如果您未来要部署到线上，可以将其改为您的前端域名。
    allow_origins=["*"], 
    # 允许所有HTTP方法 (GET, POST, etc.)
    allow_methods=["*"],
    # 允许所有请求头, 包括像 "Authorization" 这样的自定义头部
    allow_headers=["*"],
)

# 这会创建一个 'static' 文件夹（如果它不存在的话）
if not os.path.exists("static"):
    os.makedirs("static")
# 这句代码的意思是：当浏览器访问 /static/... 路径时，
# FastAPI会去项目的 static/ 文件夹里找对应的文件
app.mount("/static", StaticFiles(directory="static"), name="static")
# ---------------------------------------------------
# 2. Register startup and shutdown events
# ---------------------------------------------------

@app.on_event("startup")
def on_startup():
    """
    This function now safely connects to databases, binds models, and creates tables.
    """
    model_db_mapping = {
        User: user_db,
        Chat: chat_db,
        Assessment: assessment_db,
        Checkin: status_db,
    }
    
    print("🚀 Starting database initialization...")
    for model, db in model_db_mapping.items():
        # The fix is here: We check if the connection is closed before connecting.
        if db.is_closed():
            db.connect()
        
        # The rest of the logic remains the same
        try:
            model.bind(db, bind_refs=False, bind_backrefs=False)
            db.create_tables([model])
            # I've moved the success print inside the 'try' block for more accurate logging
            print(f"✅ Table '{model._meta.table_name}' is ready in DB '{db.database}'")
        except Exception as e:
            print(f"❌ Error during table setup for '{model._meta.table_name}': {e}")
            
    print("✨ Database initialization process complete!")

@app.on_event("shutdown")
def on_shutdown():
    """
    This function runs when the application shuts down.
    It safely disconnects from all databases.
    """
    print("👋 Closing all database connections...")
    for db in all_dbs:
        if not db.is_closed():
            db.close()
    print("💤 All connections closed.")

# ---------------------------------------------------
# 3. Mount all the sub-routers
# ---------------------------------------------------
API_PREFIX = "/api/v1"

app.include_router(user_router.router, prefix=API_PREFIX)
app.include_router(chat_router.router, prefix=API_PREFIX)
app.include_router(assessment_router.router, prefix=API_PREFIX)
app.include_router(status_router.router, prefix=API_PREFIX)

# ---------------------------------------------------
# 4. Define a root endpoint for health checks
# ---------------------------------------------------

@app.get("/", tags=["Root"])
def read_root():
    """
    A simple root endpoint to confirm the API is running.
    """
    return {"message": "Welcome to the AI Psychologist API! Visit /docs for documentation."}