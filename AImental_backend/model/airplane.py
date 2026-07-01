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

class UserCollectedAirplane(Model):
    """
    记录用户收进飞机篓的纸飞机。
    """
    user = ForeignKeyField(User, backref='collected_airplanes', field='id', on_delete='CASCADE')
    airplane = ForeignKeyField(PaperAirplane, backref='collected_by_users', field='id', on_delete='CASCADE')
    asset_number = CharField(max_length=16, null=True)
    asset_path = CharField(max_length=255, null=True)
    collected_time = DateTimeField(default=datetime.now)

    class Meta:
        database = airplane_db
        table_name = 'user_collected_airplanes'
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
    asset_number: Optional[str] = None
    asset_path: Optional[str] = None
    collected_time: Optional[datetime] = None

    class Config:
        from_attributes = True

class PaperAirplaneCollect(BaseModel):
    """
    收进飞机篓时记录当时使用的纸飞机素材。
    """
    asset_number: Optional[str] = None
    asset_path: Optional[str] = None

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
        self.db.create_tables([PaperAirplane, UserPickedAirplane, UserCollectedAirplane])
        self._ensure_collected_asset_columns()

    def _ensure_collected_asset_columns(self):
        """
        给已存在的飞机篓关系表补充素材记忆字段。
        """
        table_name = UserCollectedAirplane._meta.table_name
        existing_columns = {column.name for column in self.db.get_columns(table_name)}

        if 'asset_number' not in existing_columns:
            self.db.execute_sql(f'ALTER TABLE {table_name} ADD COLUMN asset_number VARCHAR(16)')

        if 'asset_path' not in existing_columns:
            self.db.execute_sql(f'ALTER TABLE {table_name} ADD COLUMN asset_path VARCHAR(255)')

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

    def collect_airplane(
        self,
        user_id: str,
        airplane_id: int,
        asset_number: Optional[str] = None,
        asset_path: Optional[str] = None
    ) -> Optional[dict]:
        """
        将已捡起的纸飞机收进当前用户的飞机篓。
        """
        airplane = PaperAirplane.get_or_none(PaperAirplane.id == airplane_id)
        if not airplane or str(airplane.user_id) == str(user_id):
            return None

        has_picked = UserPickedAirplane.get_or_none(
            (UserPickedAirplane.user == user_id) &
            (UserPickedAirplane.airplane == airplane_id)
        )
        if not has_picked:
            return None

        try:
            collected, created = UserCollectedAirplane.get_or_create(
                user=user_id,
                airplane=airplane_id,
                defaults={
                    'asset_number': asset_number,
                    'asset_path': asset_path
                }
            )

            if not created and (asset_number or asset_path):
                should_save = False
                if asset_number and not collected.asset_number:
                    collected.asset_number = asset_number
                    should_save = True
                if asset_path and not collected.asset_path:
                    collected.asset_path = asset_path
                    should_save = True
                if should_save:
                    collected.save()

            return self._serialize_collected_airplane(collected)
        except Exception as e:
            print(f"Error collecting airplane: {e}")
            return None

    def get_collected_airplanes(self, user_id: str, page: int = 1, page_size: int = 20) -> list[dict]:
        """
        获取当前用户收进飞机篓的纸飞机。
        """
        query = (UserCollectedAirplane
                 .select(UserCollectedAirplane, PaperAirplane)
                 .join(PaperAirplane)
                 .where(UserCollectedAirplane.user == user_id)
                 .order_by(UserCollectedAirplane.collected_time.desc())
                 .paginate(page, page_size))

        return [self._serialize_collected_airplane(collected) for collected in query]

    def discard_collected_airplane(self, user_id: str, airplane_id: int) -> bool:
        """
        从当前用户的飞机篓中移除一架纸飞机，不删除原始纸飞机内容。
        """
        deleted_count = (UserCollectedAirplane
                         .delete()
                         .where(
                             (UserCollectedAirplane.user == user_id) &
                             (UserCollectedAirplane.airplane == airplane_id)
                         )
                         .execute())
        return deleted_count > 0

    def _serialize_collected_airplane(self, collected: UserCollectedAirplane) -> dict:
        airplane = collected.airplane
        return {
            'id': airplane.id,
            'message': airplane.message,
            'create_time': airplane.create_time,
            'asset_number': collected.asset_number,
            'asset_path': collected.asset_path,
            'collected_time': collected.collected_time
        }

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
                # 考研
                "今天又是背了忘忘了背的一天，政治好难啊，希望明年能上岸。",
                "图书馆关门了，回寝室的路上风好冷，但愿这一切都值得。",
                "看到研友们都那么拼，我一点也不敢松懈。加油，一战成硕！",
                "专业课的真题刷了三遍了，感觉还是没底，有点焦虑。",
                "今天奖励了自己一杯咖啡，明天继续战斗！考研人，永不认输！",
                "倒计时XX天，感觉时间越来越不够用了。",
                "刚刚在楼道里把肖四又背了一遍，希望考试的时候都能想起来。",

                # 找工作
                "今天又投了十几份简历，已读不回是常态，心态有点崩。",
                "刚结束一场面试，感觉自己表现得不太好，唉。",
                "终于拿到一个offer了！虽然不是最想去的，但总算有保底了。",
                "为了做作品集，熬了好几个通宵，头发都掉了一大把。",
                "穿上西装感觉自己像个大人了，但心里还是慌慌的。",
                "群面也太可怕了，全是些大佬，我就是个小菜鸡。",

                # 谈恋爱
                "今天跟ta吵架了，其实也不是什么大事，但就是觉得好委屈。",
                "异地恋真的好辛苦，现在就想抱抱ta。",
                "ta刚刚给我点了外卖，还备注了好多我爱吃的东西，好幸福。",
                "我们在一起一周年啦，希望未来还有很多很多年。",
                "喜欢一个人是藏不住的，看到ta就会忍不住笑。",
                "不知道我们能走多远，但现在，我很珍惜。",

                # 吃了美食
                "这家新开的火锅店也太好吃了吧！毛肚绝了！",
                "今天终于吃到了心心念念的蛋糕，甜食果然能治愈一切。",
                "自己做的晚饭，卖相不怎么样，但味道还不错，有家的感觉。",
                "深夜放毒，刚点了一份烧烤，减肥是不可能减肥的。",
                "嗦了一碗螺蛳粉，感觉整个灵魂都升华了。",

                # 上课/考试
                "早上第一节是高数课，我坐在第一排，但还是听不懂…",
                "四六级又要来了，我的单词书还停留在第一页。",
                "明天就要月考了，啥也没复习，准备裸考了。",
                "教资的面试好紧张啊，希望能一次过！拜托拜托！",
                "艺考这条路好难走，每天画画画到手抽筋，希望能有个好结果。",
                "下周就要交论文了，我的文档还是空的。",
                "上课好无聊啊，老师在上面讲，我在下面神游。",

                # 兼职/工作日常
                "今天去当家教，那个小朋友真的好聪明，一道题讲一遍就会了。",
                "给小朋友上钢琴课，发现他比我有天赋多了，我这个老师压力好大。",
                "兼职的工资发了，可以去买之前看上的那件衣服了！",
                "今天带的小朋友太调皮了，一节课下来我嗓子都哑了。",
                "作为一个钢琴老师，最开心的就是看到学生从弹不响到弹出流畅的曲子。",
                "这周的兼职结束了，虽然累，但感觉很充实。",

                # 看风景/旅行
                "今天爬山了，山顶的风好大，风景也超美！",
                "在海边，什么都不用想，就听着海浪声发呆，真好。",
                "旅行的意义，可能就是从自己待腻的地方，去看别人待腻的地方吧。",
                "夕阳也太温柔了，你看到了吗？",
                "订好了下个月去旅行的机票，已经开始期待了！",
                "古镇的夜景很美，但商业气息也有点重。",
                "在路上，遇见了各种各样的人，听了好多故事。",

                # 平平无奇的碎碎念
                "今天天气真好，晒了被子，晚上睡觉一定很舒服。",
                "耳机里放着喜欢的歌，感觉走路都带感了。",
                "有点想家了，想吃我妈做的饭。",
                "今天没什么特别的事发生，是普通但安心的一天。",
                "好烦，宿舍的热水器又坏了。",
                "最近在追一部剧，太上头了，根本停不下来。",
                "希望捡到这个瓶子的人，今天过得开心。",
                "突然就觉得好累，什么都不想干。",
                "今天在路上看到一只很可爱的柯基，屁股圆滚滚的。",
                "这个世界晚安。",
                "如果扔个瓶子许愿能成真就好了。",
                "人为什么要上班/上学啊？",
                "今天的云很特别，像一只大大的棉花糖。",
                "又失眠了，有人和我一样吗？",
                "听说明天要降温了，我的厚衣服还没拿出来。",
                "无聊，扔个瓶子玩玩。",
                "嘿，陌生人，祝你做个好梦。",
                "今天发工资了，但还完花呗就没了。",
                "好想中彩票啊。",
                "今天也要努力生活呀！",
                "打了一下午游戏，脖子好酸。",
                "只是想找个地方说说话。",
                "我的猫又在我键盘上睡觉了，拿它没办法。",
                "水逆退散！",
                "分享一首歌给你，希望你喜欢。",
                "今天喝到了一杯很好喝的奶茶，小确幸。",
                "下雨天最适合睡觉了。",
                "感觉自己好渺小啊。",
                "加油啊，屏幕那边的陌生人。",
                "这个瓶子会漂到哪里去呢？真好奇。",
                "秘密都藏在海里。",
                "希望明天会是晴天。",
                "刚刚不小心把水杯打翻了，今天真是倒霉的一天。",
                "今天的月亮好亮。",
                "别不开心啦，一切都会好起来的。",
                "平平淡淡才是真。",
                "如果捡到我，就对我笑一下吧。",
                "晚安。"
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
