# models/ai_status.py

from peewee import Model, AutoField, ForeignKeyField, CharField, DateTimeField, IntegerField, fn
from datetime import datetime, date
import pytz

# 导入你的AI角色模型，用于建立外键关系
from .ai_character import AICharacter

# 导入你在 db.py 中定义的状态数据库连接
from db import status_db 

# 定义北京时区，方便在本文件中统一使用
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# --- Peewee Model (已升级) ---
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
    start_time = DateTimeField(default=lambda: datetime.now(BEIJING_TZ))
    
    # 状态预计的结束时间
    end_time = DateTimeField()

    # AI生成日程时会提供这个值，用于决定回复延迟
    reply_delay_minutes = IntegerField(default=5, help_text="当前状态下建议的回复延迟分钟数")

    # --- 【核心新增】专注等级 ---
    focus_level = CharField(
        max_length=20, 
        default='LOW', 
        help_text="活动的专注等级: UNINTERRUPTIBLE, HIGH, LOW, AVAILABLE"
    )
    # --- ---------------------- ---

    class Meta:
        database = status_db
        table_name = 'ai_status'

# --- Table Access Class (已升级) ---
class AiStatusTable:
    def __init__(self, db):
        self.db = db
        # 确保应用启动时自动创建表
        # 注意: Peewee 在表已存在时不会重复创建，但在模型有字段增删时，需要手动迁移。
        # 对于开发阶段，最简单的方式是删除旧的 status.db 文件让它重建。
        self.db.create_tables([AiStatus])

    def create_status(self, character_id: str, category: str, text: str, start_time: datetime, end_time: datetime, reply_delay_minutes: int, focus_level: str) -> AiStatus:
        """
        【已升级】创建一个新的状态记录，现在包含 focus_level 参数。
        """
        return AiStatus.create(
            character=character_id,
            status_category=category,
            status_text=text,
            start_time=start_time,
            end_time=end_time,
            reply_delay_minutes=reply_delay_minutes,
            focus_level=focus_level # <-- 新增
        )

    def get_current_status(self, character_id: str) -> AiStatus | None:
        """
        获取一个角色当前未结束的最新状态，使用正确的时区。
        (此函数逻辑无需修改)
        """
        # 使用带时区的当前时间进行查询
        now = datetime.now(BEIJING_TZ)
        status = AiStatus.select().where(
            (AiStatus.character == character_id) &
            (AiStatus.start_time <= now) &
            (AiStatus.end_time > now)
        ).order_by(AiStatus.start_time.desc()).first()
        return status

    def has_schedule_for_date(self, character_id: str, target_date: date) -> bool:
        """
        检查指定角色在特定日期是否已有任何状态记录。
        (此函数逻辑无需修改)
        """
        query = AiStatus.select().where(
            (AiStatus.character == character_id) &
            (fn.DATE(AiStatus.start_time) == target_date)
        ).exists()
        
        return query

# --- 实例化 Table Access 对象 ---
ai_status_table = AiStatusTable(status_db)
