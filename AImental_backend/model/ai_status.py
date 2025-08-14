# models/ai_status.py

from peewee import Model, AutoField, ForeignKeyField, CharField, DateTimeField
from datetime import datetime

# 导入你的AI角色模型，用于建立外键关系
from .ai_character import AICharacter

# 导入你在 db.py 中定义的状态数据库连接
# 建议为高频读写的status单独建一个db文件，如果流量不大也可以用主库
from db import status_db 

# --- Peewee Model ---
class AiStatus(Model):
    """
    Peewee模型: 记录并管理AI虚拟人的动态实时状态。
    这是整个异步交互和“生命感”模拟的核心。
    """
    id = AutoField()  # 自增主键
    
    # 关联到具体的AI角色
    character = ForeignKeyField(AICharacter, backref='statuses', field='id', on_delete='CASCADE')
    
    # 用于程序逻辑判断的状态分类
    status_category = CharField(max_length=50, index=True)
    
    # 用于前端展示的、富有人设的状态文本
    status_text = CharField(max_length=255)
    
    # 状态开始的精确时间
    start_time = DateTimeField(default=datetime.now)
    
    # 状态预计的结束时间
    end_time = DateTimeField()

    class Meta:
        database = status_db
        table_name = 'ai_status'

# --- Table Access Class (可选，但建议保持风格一致) ---
class AiStatusTable:
    def __init__(self, db):
        self.db = db
        # 确保应用启动时自动创建表
        self.db.create_tables([AiStatus])

    def create_status(self, character_id: str, category: str, text: str, end_time: datetime) -> AiStatus:
        """创建一个新的状态记录"""
        return AiStatus.create(
            character=character_id,
            status_category=category,
            status_text=text,
            end_time=end_time
        )

    def get_current_status(self, character_id: str) -> AiStatus | None:
        """获取一个角色当前未结束的最新状态"""
        now = datetime.now()
        status = AiStatus.select().where(
            (AiStatus.character == character_id) &
            (AiStatus.start_time <= now) &
            (AiStatus.end_time > now)
        ).order_by(AiStatus.start_time.desc()).first()
        return status

# --- 实例化 Table Access 对象 ---
ai_status_table = AiStatusTable(status_db)