# AImental_backend/model/airplane.py

import peewee as pw
from peewee import Model, CharField, TextField, DateTimeField, ForeignKeyField
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

# 1. 导入共享的数据库连接实例和基础模型
from .user import User

# --- Database Setup ---
# 我们将纸飞机的数据存储在一个新的专用数据库中
airplane_db = pw.SqliteDatabase('db/paper_airplane.db')

# ---------------------------------------------------
# 1. Peewee ORM Models (已更新)
# ---------------------------------------------------

class PaperAirplane(Model):
    """
    Peewee模型，定义了 'paper_airplanes' 表的结构。
    【已移除】移除了 status 字段。
    """
    id = pw.AutoField()  # 自动增长的整数主键
    user = ForeignKeyField(User, backref='paper_airplanes', field='id', on_delete='CASCADE')
    message = TextField()
    create_time = DateTimeField(default=datetime.now)

    class Meta:
        database = airplane_db
        table_name = 'paper_airplanes'

class UserPickedAirplane(Model):
    """
    【新增】记录用户捡到纸飞机关系的模型。
    """
    user = ForeignKeyField(User, backref='picked_airplanes', field='id', on_delete='CASCADE')
    airplane = ForeignKeyField(PaperAirplane, backref='picked_by_users', field='id', on_delete='CASCADE')
    picked_time = DateTimeField(default=datetime.now)

    class Meta:
        database = airplane_db
        table_name = 'user_picked_airplanes'
        primary_key = pw.CompositeKey('user', 'airplane')


# ---------------------------------------------------
# 2. Pydantic Models for API Data Validation
# ---------------------------------------------------

class PaperAirplaneCreate(BaseModel):
    """
    用于创建纸飞机的请求体模型。
    """
    message: str

class PaperAirplaneResponse(BaseModel):
    """
    用于API响应的纸飞机数据模型。
    """
    id: int
    message: str
    create_time: datetime

    class Config:
        from_attributes = True

# ---------------------------------------------------
# 3. Database Table Access Class (已更新)
# ---------------------------------------------------

class PaperAirplaneTable:
    """
    封装了所有与 'paper_airplanes' 表相关的数据库操作。
    """
    def __init__(self, db_connection):
        self.db = db_connection
        # 【已更新】确保在服务启动时能自动创建两个表
        self.db.create_tables([PaperAirplane, UserPickedAirplane])

    def throw_airplane(self, user_id: str, message: str) -> PaperAirplane:
        """
        创建一个新的纸飞机并存入数据库。
        """
        airplane = PaperAirplane.create(
            user=user_id,
            message=message
        )
        return airplane

    def get_available_airplanes(self, current_user_id: str, limit: int = 6) -> list[PaperAirplane]:
        """
        【新增】获取当前用户可以捡的纸飞机列表（非自己发布，且未捡过）。
        """
        # 子查询：找出当前用户已经捡过的所有纸飞机的ID
        picked_airplanes_query = (UserPickedAirplane
                                  .select(UserPickedAirplane.airplane)
                                  .where(UserPickedAirplane.user == current_user_id))

        # 主查询：找出所有不由当前用户发布、且ID不在已捡取列表中的纸飞机
        query = (PaperAirplane
                 .select()
                 .where(
                     (PaperAirplane.user != current_user_id) &
                     (PaperAirplane.id.not_in(picked_airplanes_query))
                 )
                 .order_by(pw.fn.Random())
                 .limit(limit))
        
        return list(query)

    def record_airplane_pickup(self, user_id: str, airplane_id: int) -> bool:
        """
        【新增】记录用户捡起特定纸飞机的行为。
        如果记录已存在，则返回 False。
        """
        try:
            UserPickedAirplane.create(
                user=user_id,
                airplane=airplane_id # Peewee will handle the foreign key object or ID
            )
            return True
        except pw.IntegrityError:
            # Record already exists (user already picked this airplane)
            return False
        except Exception as e:
            print(f"Error recording airplane pickup: {e}")
            return False

    def pickup_random_airplane(self, current_user_id: str) -> Optional[PaperAirplane]:
        """
        【已废弃】随机拾取一个当前用户未捡到过的、且非自己发布的纸飞机。
        这是一个原子操作，确保不会重复拾取。
        此方法在新设计中不再使用，但保留以防万一。
        """
        with self.db.atomic() as transaction:
            try:
                # 子查询：找出当前用户已经捡过的所有纸飞机的ID
                picked_airplanes_query = (UserPickedAirplane
                                          .select(UserPickedAirplane.airplane)
                                          .where(UserPickedAirplane.user == current_user_id))

                # 主查询：找出所有不由当前用户发布、且ID不在已捡取列表中的纸飞机
                query = (PaperAirplane
                         .select()
                         .where(
                             (PaperAirplane.user != current_user_id) &
                             (PaperAirplane.id.not_in(picked_airplanes_query))
                         )
                         .order_by(pw.fn.Random()) 
                         .limit(1))
                
                airplane_to_pick = query.get_or_none()

                if airplane_to_pick:
                    # 如果找到了，就在关系表中创建一条新的拾取记录
                    UserPickedAirplane.create(
                        user=current_user_id,
                        airplane=airplane_to_pick
                    )
                    return airplane_to_pick
                else:
                    # 如果没有找到（可能所有飞机都捡完了），返回 None
                    return None
            except Exception as e:
                transaction.rollback()
                print(f"Error during pickup_random_airplane: {e}")
                return None

    def get_my_airplanes(self, user_id: str, page: int = 1, page_size: int = 10) -> list[PaperAirplane]:
        """
        获取指定用户发布的所有纸飞机（按时间倒序分页）。
        """
        query = (PaperAirplane
                 .select() 
                 .where(PaperAirplane.user == user_id)
                 .order_by(PaperAirplane.create_time.desc())
                 .paginate(page, page_size))
        
        return list(query)

    def add_default_airplanes_if_needed(self):
        """
        检查数据库，如果没有任何纸飞机，就添加10条默认数据。
        """
        # 1. 检查纸飞机数据库是否已有数据
        if PaperAirplane.select().count() > 0:
            return

        print("Paper airplane database is empty. Checking for existing users to seed data...")

        # 2. 查找或创建系统用户
        from .user import User, UserTable, user_db # Import UserTable and user_db
        SYSTEM_USER_OPENID = "system_paper_airplane_user"
        SYSTEM_USER_NICKNAME = "纸飞机系统"

        # Ensure user_db is connected for this operation
        if user_db.is_closed():
            user_db.connect()

        system_user = User.get_or_none(User.openid == SYSTEM_USER_OPENID)
        if not system_user:
            print(f"System user '{SYSTEM_USER_NICKNAME}' not found. Creating it...")
            # Temporarily instantiate UserTable to create user
            # This is a bit hacky, ideally UserTable methods would be static or passed
            # But given the current structure, this is the most direct way.
            temp_user_table = UserTable(user_db) 
            system_user = temp_user_table.create_user(
                openid=SYSTEM_USER_OPENID,
                nickname=SYSTEM_USER_NICKNAME,
                avatar_url="/static/avatars/default.png" # Or a specific system avatar
            )
            if not system_user:
                print("Failed to create system user. Cannot seed default airplanes.")
                return
            print(f"System user '{SYSTEM_USER_NICKNAME}' created with ID: {system_user.id}")
        else:
            print(f"Found existing system user '{SYSTEM_USER_NICKNAME}' with ID: {system_user.id}")

        # Ensure user_db is closed if it was opened just for this
        if not user_db.is_closed():
            user_db.close()

        # 3. 定义10条默认消息
        default_messages = [
            "今天天气真好，希望你的心情也像这阳光一样灿烂。",
            "如果你感到疲惫，记得停下来歇一歇。世界不赶你，你也不要太赶自己。",
            "刚刚吃到了一块超棒的蛋糕，小小的幸福感能点亮一整天！",
            "希望捡到这个纸飞机的你，今晚能做个好梦。",
            "有时候，迷路是为了发现新的风景。别怕，继续走下去。",
            "分享一个秘密：我喜欢在雨天听着音乐看书，感觉整个世界都安静了。",
            "“每一个不曾起舞的日子，都是对生命的辜负。”——尼采。与你共勉。",
            "别忘了抬头看看天，今天的云很特别。",
            "送你一句咒语：‘一切都会好起来的’。默念三遍，祝你今天顺利。",
            "嘿，陌生人，感谢你捡起了我的纸飞机。愿你被这个世界温柔以待。"
        ]

        # 4. 使用系统用户作为作者，插入数据
        with self.db.atomic():
            for msg in default_messages:
                PaperAirplane.create(
                    user=system_user,
                    message=msg
                )
        
        print(f"Successfully seeded {len(default_messages)} default paper airplanes.")


# --- Instantiate the table access object ---
# 使用我们新创建的 airplane_db 连接
paper_airplane_table = PaperAirplaneTable(airplane_db)