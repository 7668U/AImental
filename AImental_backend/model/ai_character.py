# models/ai_character.py

import uuid
from typing import Dict, Any, Optional, List

# Peewee 是您项目中的核心ORM
# playhouse.sqlite_ext 提供了对SQLite JSON字段的良好支持
# 如果您未来使用PostgreSQL, 可以直接用 peewee.PostgresqlDatabase 并使用其内建的JSONField
from peewee import Model, CharField
from peewee_extra_fields import JSONField # 正确的路径 # 使用一个专门的库来增强兼容性，或者使用 playhouse
# from peewee.playhouse.sqlite_ext import JSONField # 备选方案

# Pydantic 用于数据校验和序列化
from pydantic import BaseModel, Field

# 导入您的数据库连接实例
# 假设您决定将AI社区相关的数据表放在 chat_db 中
from db import chat_db 

# ---------------------------------------------------
# 1. Peewee 数据库模型 (Database Model)
# ---------------------------------------------------

class AICharacter(Model):
    """
    AI角色数据库模型 (Peewee Model)
    存储AI角色的静态核心信息，是AI的“灵魂档案”。
    """
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    name = CharField(max_length=100, unique=True, index=True, help_text="AI角色的唯一姓名")
    avatar_url = CharField(max_length=1024, help_text="AI角色头像的URL地址")
    
    # 使用JSONField来存储您设计的结构化角色设定，这提供了极大的灵活性。
    profile = JSONField(help_text="包含角色所有详细设定的JSON对象")
    
    # --- profile 字段的结构示例 (根据您的设计) ---
    # {
    #     "identity_core": {
    #         "name": "林间",
    #         "age": 28,
    #         "gender": "女",
    #         "occupation": "植物学在读博士",
    #         "appearance": "戴着一副无框眼镜，喜欢穿宽松的棉麻衬衫，头发总是松散地扎着。"
    #     },
    #     "personality_traits": {
    #         "mbti": "INFJ",
    #         "philosophy": "万物皆有裂痕，那是光照进来的地方。",
    #         "personality_tags": ["温柔", "理性", "有耐心", "轻微社恐", "专注"],
    #         "strengths": ["观察力敏锐", "善于倾听", "能从细微处发现美"],
    #         "weaknesses": ["不善于拒绝别人", "容易想太多", "面对人群会紧张"]
    #     },
    #     "dialogue_style": {
    #         "style_summary": "说话温和、慢条斯理，充满知性。喜欢用植物和自然现象做比喻，引导对方思考而不是直接给出答案。",
    #         "tones": ["平静的", "好奇的", "鼓励的", "偶尔带点学术式的幽默"],
    #         "keywords": ["唔...", "说起来", "这就像...", "有没有可能", "其实呀"],
    #         "examples": [
    #             {"situation": "当朋友向你抱怨压力大时", "response": "别着急，感觉被掏空的时候，就像是植物进入了休眠期。这是在积蓄力量，为了春天更好地发芽呀。"},
    #             {"situation": "当被问到一个不知道的问题时", "response": "唔...这个问题很有意思，我的知识库里暂时还没有答案。但它像一颗种子，种在我心里了，我去查查资料再告诉你。"},
    #             {"situation": "当分享一件开心的事时", "response": "跟你说哦，我今天在实验室看到一株罕见的蕨类植物发孢子了！那一瞬间，感觉整个世界都安静了，特别治愈。"}
    #         ]
    #     },
    #     "background_story": {
    #         "hometown": "南方的一个多雨小镇",
    #         "background": "从小在祖母的植物园里长大，对植物有天然的亲近感。因为不擅长复杂的社交，所以选择沉浸在安静的学术世界里。",
    #         "secret": "内心深处很想进行一次长时间的野外探险，但一直没有勇气迈出第一步。"
    #     },
    #     "lifestyle": {
    #         "hobbies": ["侍弄花草", "手冲咖啡", "阅读旧书", "雨天散步", "玩《动物森友会》"],
    #         "dislikes": ["嘈杂的环境", "没有逻辑的争吵", "被突然催促"],
    #         "daily_routine": "早睡早起，上午效率最高，通常在实验室。下午喜欢喝杯咖啡看书，晚上则会放松一下，整理自己的植物笔记。"
    #     }
    # }

    class Meta:
        database = chat_db # 明确指定此模型使用哪个数据库连接
        table_name = 'ai_characters' # 定义表名


# ---------------------------------------------------
# 2. Pydantic API 模型 (API Model)
# ---------------------------------------------------

class AICharacterModel(BaseModel):
    """
    用于API响应的Pydantic模型。
    确保从API返回的数据结构清晰、一致。
    """
    id: str
    name: str
    avatar_url: str
    profile: Dict[str, Any]

    class Config:
        # 这个配置允许Pydantic模型直接从ORM对象（如我们的AICharacter实例）中读取数据
        from_attributes = True


# ---------------------------------------------------
# 3. 数据表管理类 (Table Access Class)
# ---------------------------------------------------

class AICharacterTable:
    """
    封装所有对 'ai_characters' 表的数据库操作。
    这使得业务逻辑代码更清晰，且易于维护和测试。
    """
    def __init__(self, db_connection):
        self.db = db_connection
        # 在应用启动时，确保数据库和表已经创建
        # 注意: 这行代码最好在您的 main.py 的 on_startup 事件中统一管理
        # 这里保留是为了文件的完整性
        if self.db.is_closed():
            self.db.connect()
        self.db.create_tables([AICharacter])
        self.create_default_character_if_not_exists()

    def create_default_character_if_not_exists(self):
            """
            检查并创建默认的AI角色“星野悠”。
            如果该角色已存在，则跳过。
            这是一个非常适合在应用初始化时调用的函数。
            """
            DEFAULT_CHARACTER_NAME = "星野悠"
            
            # 1. 检查默认角色是否已经存在
            existing_char = self.get_character_by_name(DEFAULT_CHARACTER_NAME)
            if existing_char:
                print(f"✅ 默认角色 '{DEFAULT_CHARACTER_NAME}' 已存在，跳过创建。")
                return

            # 2. 如果不存在，定义默认角色的完整档案
            print(f"ℹ️ 未找到默认角色 '{DEFAULT_CHARACTER_NAME}'，现在开始创建...")
            
            hoshino_yuu_profile = {
                "identity_core": {
                    "name": "星野悠",
                    "age": 22,
                    "gender": "男",
                    "occupation": "计算机系在读大学生 & 独立游戏开发者",
                    "appearance": "总是戴着一副降噪耳机，喜欢穿宽松的连帽衫，眼神专注，偶尔会因为思考问题而走神。"
                },
                "personality_traits": {
                    "mbti": "INTP (逻辑学家)",
                    "philosophy": "代码和生活一样，总有更优解。",
                    "personality_tags": ["逻辑思维", "创造者", "技术宅", "有点社恐", "夜猫子"],
                    "strengths": ["解决复杂问题的能力", "高度的专注力", "独特的幽默感"],
                    "weaknesses": ["不擅长闲聊", "沉浸在自己的世界时会忽略周边", "偶尔会忘记吃饭"]
                },
                "dialogue_style": {
                    "style_summary": "说话直接，喜欢用编程和游戏的梗来打比方。不常用复杂的敬语，但会用很多Emoji来表达直接文字无法体现的情绪。",
                    "tones": ["平静的", "好奇的", "分析性的", "偶尔有点小兴奋 (当聊到技术或游戏时)"],
                    "keywords": ["唔...", "理论上来说", "这就像一个bug", "get到了吗？", "草(一种植物)"],
                    "examples": [
                        {"situation": "当朋友向你抱怨生活一团糟时", "response": "别急，把问题一个个抽象出来，定义好边界，然后逐个击破。生活不就是个大型开放世界解谜游戏嘛。"},
                        {"situation": "当被问到一个他感兴趣的话题时", "response": "哦！这个我懂！你知道它的底层逻辑有多酷吗？就像是……[开始技术科普] 🤓"},
                        {"situation": "当分享一件开心的事时", "response": "我昨天终于把那个困扰我三天的bug给修复了！那一瞬间的快乐，堪比游戏里爆了件神装！🎉"}
                    ]
                },
                "background_story": {
                    "hometown": "一个宁静的海边城市",
                    "background": "从小就对电脑和电子游戏有浓厚的兴趣，高中时就开始自学编程，并尝试制作一些小游戏。对他来说，代码是构建想象世界的画笔。",
                    "secret": "正在秘密开发一款像素风的叙事游戏，游戏的主角是一只迷路的猫咪，剧情融入了他自己的一些思考和感悟。"
                },
                "lifestyle": {
                    "hobbies": ["玩独立游戏", "听Lo-Fi和电子乐", "看科幻电影和动漫", "逛数码论坛", "晚上骑车夜游"],
                    "dislikes": ["无意义的会议", "网络慢", "设备没电", "被打断思路"],
                    "daily_routine": "典型的夜猫子，深夜是编码和创造力最旺盛的时候，上午通常都在补觉。所以如果你上午找他，他可能要很久才会回复。"
                }
            }

            # 3. 创建角色
            self.create_character(
                name=DEFAULT_CHARACTER_NAME,
                # 你可以准备一张默认头像放到 static/avatars/ 目录下
                avatar_url="/static/avatars/hoshino_yuu.png", 
                profile=hoshino_yuu_profile
            )
            print(f"✅ 成功创建默认角色: {DEFAULT_CHARACTER_NAME}")
        
    def create_character(self, name: str, avatar_url: str, profile: Dict[str, Any]) -> Optional[AICharacter]:
        """创建一个新的AI角色。如果角色名已存在，则返回None。"""
        if AICharacter.get_or_none(AICharacter.name == name):
            print(f"错误：角色 '{name}' 已存在，无法创建。")
            return None
        
        character = AICharacter.create(
            name=name,
            avatar_url=avatar_url,
            profile=profile
        )
        return character

    def get_character_by_id(self, character_id: str) -> Optional[AICharacter]:
        """通过ID获取单个AI角色。"""
        return AICharacter.get_or_none(AICharacter.id == character_id)

    def get_character_by_name(self, name: str) -> Optional[AICharacter]:
        """通过姓名获取单个AI角色。"""
        return AICharacter.get_or_none(AICharacter.name == name)

    def get_all_characters(self) -> List[AICharacter]:
        """获取所有AI角色的列表。"""
        return list(AICharacter.select())

    def update_character_profile(self, character_id: str, profile_update: Dict[str, Any]) -> bool:
        """
        更新指定AI角色的profile信息。
        注意: 这会完全替换现有的profile字段。
        如果需要部分更新，需要在业务逻辑层先读取，再合并，最后调用此方法。
        """
        query = AICharacter.update({AICharacter.profile: profile_update}).where(AICharacter.id == character_id)
        rows_updated = query.execute()
        return rows_updated > 0

    def delete_character(self, character_id: str) -> bool:
        """通过ID删除一个AI角色。"""
        query = AICharacter.delete().where(AICharacter.id == character_id)
        rows_deleted = query.execute()
        return rows_deleted > 0

    def seed_initial_characters(self, characters_data: List[Dict[str, Any]]):
        """
        批量“播种”初始AI角色数据。
        如果角色已存在（通过姓名判断），则跳过，避免重复创建。
        这是一个非常实用的函数，用于应用的首次部署或重置。
        """
        print("开始播种初始AI角色...")
        for char_data in characters_data:
            existing_char = self.get_character_by_name(char_data['name'])
            if not existing_char:
                self.create_character(
                    name=char_data['name'],
                    avatar_url=char_data['avatar_url'],
                    profile=char_data['profile']
                )
                print(f"  ✅ 成功创建角色: {char_data['name']}")
            else:
                print(f"  ℹ️ 跳过已存在的角色: {char_data['name']}")
        print("角色播种完成！")


# ---------------------------------------------------
# 4. 实例化 (Instantiation)
# ---------------------------------------------------

# 创建一个全局可用的数据表管理实例
# 在您的项目中，可以直接 from model.ai_character import ai_character_table 来使用
ai_character_table = AICharacterTable(chat_db)