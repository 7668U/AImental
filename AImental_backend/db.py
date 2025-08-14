# db.py
import peewee as pw
import os

# --- 数据库文件目录 ---
# 确保数据库文件夹存在
DB_DIRECTORY = "db"
os.makedirs(DB_DIRECTORY, exist_ok=True)

# --- 数据库连接实例定义 ---
# 这个文件是所有数据库连接的唯一来源，保持了项目结构的清晰。

# 1. 用户核心数据库
# 存储用户账户信息、好友关系等核心数据
user_db = pw.SqliteDatabase(os.path.join(DB_DIRECTORY, 'user_account.db'))

# 2. 社区与聊天数据库
# 存储AI社区的聊天记录、AI任务队列、AI角色定义等
chat_db = pw.SqliteDatabase(os.path.join(DB_DIRECTORY, 'community_chat.db'))

# 3. AI状态数据库
# 高频读写AI的实时状态，单独存放可以提升性能，避免锁住主聊天库
status_db = pw.SqliteDatabase(os.path.join(DB_DIRECTORY, 'ai_status.db'))

# 4. 您项目中已有的其他数据库
# 保留您原有的数据库结构，确保其他功能不受影响
assessment_db = pw.SqliteDatabase(os.path.join(DB_DIRECTORY, 'psychological_assessment.db'))
feedback_db = pw.SqliteDatabase(os.path.join(DB_DIRECTORY, 'feedback.db'))
promotion_db = pw.SqliteDatabase(os.path.join(DB_DIRECTORY, 'promotion.db'))
cabinet_db = pw.SqliteDatabase(os.path.join(DB_DIRECTORY, 'cabinet.db'))
# 假设 airplane_db 和 note_db 也是独立的
airplane_db = pw.SqliteDatabase(os.path.join(DB_DIRECTORY, 'airplane.db'))
note_db = pw.SqliteDatabase(os.path.join(DB_DIRECTORY, 'note.db'))


# --- 统一管理列表 ---
# 创建一个包含所有数据库连接的列表。
# 这使得在 main.py 的启动和关闭事件中，可以方便地用一个循环来管理所有连接。
all_dbs = [
    user_db, 
    chat_db, 
    status_db,
    assessment_db, 
    feedback_db, 
    promotion_db, 
    cabinet_db,
    airplane_db,
    note_db
]

print("db.py: All database connection objects created.")
