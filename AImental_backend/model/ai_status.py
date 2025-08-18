# models/ai_status.py

from peewee import Model, AutoField, ForeignKeyField, CharField, DateTimeField, IntegerField, fn
from datetime import datetime, date
import pytz

# 导入你的AI角色模型，用于建立外键关系
from .ai_character import AICharacter

# 导入你在 db.py 中定义的状态数据库连接
from db import status_db 
from logger_config import logger # <--- 【新增】导入您的日志记录器
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
        【已增加调试日志】
        获取一个角色当前未结束的最新状态，并打印详细的查询过程。
        """
        # --- 【调试日志 1】: 打印收到的参数 ---
        logger.info(f"--- [get_current_status DEBUG] 1. 函数开始执行，接收到的 character_id: '{character_id}'")

        # --- 【调试日志 2】: 打印用于查询的时间 ---
        now = datetime.now(BEIJING_TZ)
        logger.info(f"--- [get_current_status DEBUG] 2. 用于查询的当前北京时间 (now): {now.isoformat()}")

        # --- 【核心步骤】: 先构建查询对象，但不立即执行 ---
        query = AiStatus.select().where(
            (AiStatus.character == character_id) &
            (AiStatus.start_time <= now) &
            (AiStatus.end_time > now)
        ).order_by(AiStatus.start_time.desc())

        # --- 【调试日志 3 & 4】: 打印Peewee生成的真实SQL语句和参数 ---
        # 这可以让我们看到ORM背后到底在做什么
        try:
            sql, params = query.sql()
            logger.info(f"--- [get_current_status DEBUG] 3. 生成的SQL语句: {sql}")
            logger.info(f"--- [get_current_status DEBUG] 4. SQL语句的参数: {params}")
        except Exception as e:
            logger.error(f"--- [get_current_status DEBUG] 获取SQL语句失败: {e}")

        # --- 【核心步骤】: 现在执行查询 ---
        status = query.first()

        # --- 【调试日志 5】: 打印最终从数据库返回的结果 ---
        logger.info(f"--- [get_current_status DEBUG] 5. 数据库查询执行完毕，返回的结果是: {status}")

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
    def get_schedule_for_date(self, character_id: str, target_date: date) -> list:
        """
        【新增】获取指定角色在特定一整天的所有日程安排。
        返回一个按开始时间排序的 AiStatus 对象列表。
        """
        start_of_day = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=BEIJING_TZ)
        end_of_day = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=BEIJING_TZ)
        print(f"获取 {character_id} 在 {target_date} 的日程安排...")
        print(f"开始时间: {start_of_day}, 结束时间: {end_of_day}")
        query = (AiStatus
                .select()
                .where(
                    (AiStatus.character == character_id) &
                    (AiStatus.start_time >= start_of_day) &
                    (AiStatus.end_time <= end_of_day)
                )
                .order_by(AiStatus.start_time))
        print(f"查询结果: {query.count()} 条记录")
        print("查询结果:", query)  
        # 将查询结果转换为字典列表，方便后续处理
        schedule_list = []
        for status in query:
            # --- 【核心修复】 ---
            start_time_str = ''
            if status.start_time:  # 首先确保不是None
                try:
                    # 检查类型，如果是字符串则解析，如果是datetime则直接使用
                    dt_obj = status.start_time if isinstance(status.start_time, datetime) else datetime.fromisoformat(str(status.start_time))
                    start_time_str = dt_obj.strftime('%H:%M')
                except (ValueError, TypeError):
                    # 如果解析失败，记录一个警告，但程序不崩溃
                    logger.warning(f"无法解析的日期时间格式: {status.start_time}")

            end_time_str = ''
            if status.end_time:  # 同样处理 end_time
                try:
                    # 检查类型，如果是字符串则解析，如果是datetime则直接使用
                    dt_obj = status.end_time if isinstance(status.end_time, datetime) else datetime.fromisoformat(str(status.end_time))
                    end_time_str = dt_obj.strftime('%H:%M')
                except (ValueError, TypeError):
                    logger.warning(f"无法解析的日期时间格式: {status.end_time}")
            # --- ---------------- ---
            print(f"状态记录: {status.id}, 开始时间: {status.start_time}, 结束时间: {status.end_time}, 分类: {status.status_category}, 描述: {status.status_text}, 专注等级: {status.focus_level}")
            schedule_list.append({
                "start_time": start_time_str,
                "end_time": end_time_str,
                "status_category": status.status_category,
                "status_description": status.status_text,
                "focus_level": status.focus_level
            })

        return schedule_list
# --- 实例化 Table Access 对象 ---
ai_status_table = AiStatusTable(status_db)
