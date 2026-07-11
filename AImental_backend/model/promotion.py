# models/promotion.py

import uuid
import json
from datetime import datetime
from collections import Counter
from typing import Optional, Dict, List, Any

# 1. 导入 Peewee, Pydantic 和数据库连接
from peewee import (
    Model, CharField, TextField, DateTimeField, ForeignKeyField, IntegerField
)
from pydantic import BaseModel, Field

# 🔴 重要：导入 promotion_db 连接实例 (请确保已在 db.py 中创建)
from db import promotion_db
# 🔴 重要：导入 User 模型，用于建立外键关联
from .user import User
from security.data_encryption import EncryptedTextField, blind_index

# ---------------------------------------------------
# 1. 问卷静态数据
# ---------------------------------------------------

# 👇 请将你完整的问卷 JSON 数据粘贴到这个字典中
test_data = {
  "test_info": {
    "id": "real-major-v1",
    "name": "测测你的“真实”专业",
    "description": "当代大学生活图鉴！15道题揭示你潜意识里真正的“专业”归属，快来康康你的隐藏身份吧！"
  },
  "personalities": [
    {
      "id": "p01",
      "college": "卷理学院",
      "major": "图书馆生态信息学",
      "college_motto": "知识的尽头是绩点，我们的尽头是图书馆。",
      "description": "核心课程：《图书馆座位锁定技巧》、《专注力与环境噪音隔离》、《从入门到精通：各科文献综述》",
      "recommendation": "生存指南：注意劳逸结合，偶尔也要看看窗外的世界，不要和书本融为一体了。"
    },
    {
      "id": "p02",
      "college": "卷理学院",
      "major": "应用行为规划学",
      "college_motto": "知识的尽头是绩点，我们的尽头是图书馆。",
      "description": "核心课程：《规划的艺术与实践》、《GTD时间管理法导论》、《多线程任务处理》",
      "recommendation": "生存指南：请学会接受“意外”，有时候计划赶不上变化也是一种别样的惊喜。"
    },
    {
      "id": "p03",
      "college": "卷理学院",
      "major": "知识资产管理学",
      "college_motto": "知识的尽头是绩点，我们的尽头是图书馆。",
      "description": "核心课程：《数字笔记软件通论》、《信息检索与高效整理》、《个人知识库（PKM）构建》",
      "recommendation": "生存指南：别忘了分享是知识增值的最佳途径，带带身边还在信息茧房里的朋友吧！"
    },
    {
      "id": "p04",
      "college": "寝室生命科学学院",
      "major": "寝室软装工程学",
      "college_motto": "宇宙的中心是我的床。",
      "description": "核心课程：《宿舍美学与空间利用》、《LED灯带应用与光污染防治》、《消费主义与种草拔草》",
      "recommendation": "生存指南：在改造寝室时，请务必先征得室友和宿管阿姨的同意。"
    },
    {
      "id": "p05",
      "college": "寝室生命科学学院",
      "major": "人类睡眠学",
      "college_motto": "宇宙的中心是我的床。",
      "description": "核心课程：《睡眠与梦境解析》、《生物钟调节导论》、《枕头与床垫的选购艺术》",
      "recommendation": "生存指南：你的生物钟可能和太阳不太同步，记得备好眼罩和耳塞。"
    },
    {
      "id": "p06",
      "college": "寝室生命科学学院",
      "major": "床域生态系统学",
      "college_motto": "宇宙的中心是我的床。",
      "description": "核心课程：《床上运动力学》、《懒人经济学原理》、《零食仓储与伸手可及的艺术》",
      "recommendation": "生存指南：偶尔清理一下“床域”环境，可能会有惊奇的考古发现。"
    },
    {
      "id": "p07",
      "college": "危机管理与精准决策学院",
      "major": "DDL应急学",
      "college_motto": "DDL是第一生产力，六十分是最高性价比。",
      "description": "核心课程：《拖延心理学与自我和解》、《24小时极限任务规划》、《咖啡因与护肝片的应用》",
      "recommendation": "生存指南：常备护肝片和咖啡因，它们是你最忠实的战友。"
    },
    {
      "id": "p08",
      "college": "危机管理与精准决策学院",
      "major": "及格科学与工程",
      "college_motto": "DDL是第一生产力，六十分是最高性价比。",
      "description": "核心课程：《考纲重点剖析》、《最小努力原则》、《风险评估与成绩预测》",
      "recommendation": "生存指南：请小心老师突然划重点或改变评分规则，那将是对你整个体系的降维打击。"
    },
    {
      "id": "p09",
      "college": "危机管理与精准决策学院",
      "major": "命理学",
      "college_motto": "DDL是第一生产力，六十分是最高性价比。",
      "description": "核心课程：《摆烂哲学》、《玄学与自我安慰》、《好运锦鲤的转发技巧》",
      "recommendation": "生存指南：转发锦鲤确实能带来好心情，但作业和考试还是得自己面对哦。"
    },
    {
      "id": "p10",
      "college": "互联网与计算机科学学院",
      "major": "时间黑洞学",
      "college_motto": "现实Offline，赛博Online。",
      "description": "核心课程：《短视频沉浸式体验》、《信息茧房的构建与突破》、《“再刷五分钟”心理学》",
      "recommendation": "生存指南：试试“番茄工作法”，也许能帮你从黑洞的引力中短暂逃逸。"
    },
    {
      "id": "p11",
      "college": "互联网与计算机科学学院",
      "major": "虚拟环境栖息学",
      "college_motto": "现实Offline，赛博Online。",
      "description": "核心课程：《游戏世界观与文化研究》、《团队协作与战术指挥》、《多巴胺奖赏机制概论》",
      "recommendation": "生存指南：在虚拟世界拯救艾泽拉斯的同时，别忘了现实世界的DDL也需要拯救。"
    },
    {
      "id": "p12",
      "college": "互联网与计算机科学学院",
      "major": "舆情传播学",
      "college_motto": "现实Offline，赛博Online。",
      "description": "核心课程：《吃瓜的正确姿势》、《网络热点追踪技术》、《表情包符号学》",
      "recommendation": "生存指南：吃瓜不信瓜，传谣需谨慎。保持独立思考，做个有态度的吃瓜群众。"
    }
  ],
  "questions": [
    {
      "order": 1,
      "text": "一个阳光明媚的周六下午，你没有课也没有作业，你会选择？",
      "options": [
        { "id": "a", "text": "去图书馆！泡在知识的海洋里才是最完美的周末。", "target_personality_id": "p01" },
        { "id": "b", "text": "拿出日程本，开始规划下周的学习和生活，把所有事都安排好。", "target_personality_id": "p02" },
        { "id": "c", "text": "整理电脑里的文件和笔记，确保个人知识库（PKM）保持最新状态。", "target_personality_id": "p03" },
        { "id": "d", "text": "给自己的小窝换上新的装饰画和床单，营造满满的幸福感。", "target_personality_id": "p04" }
      ]
    },
    {
      "order": 2,
      "text": "这学期你选修了一门课，但老师讲得非常催眠，你会？",
      "options": [
        { "id": "a", "text": "绝佳的补觉时机，正好可以弥补昨晚熬夜缺的觉。", "target_personality_id": "p05" },
        { "id": "b", "text": "拿出零食和饮料，在座位上开启“不动声色”的茶话会模式。", "target_personality_id": "p06" },
        { "id": "c", "text": "不慌，等到期末前一天晚上，我能把整本书都塞进脑子里。", "target_personality_id": "p07" },
        { "id": "d", "text": "只要能过就行。开始研究这门课的考勤和作业占比，计算最低通过成本。", "target_personality_id": "p08" }
      ]
    },
    {
      "order": 3,
      "text": "看到校园BBS上有人发帖讨论“你校最灵的许愿地”，你的第一反应是？",
      "options": [
        { "id": "a", "text": "马上去拜一拜，最近考试多，急需一些玄学力量加持。", "target_personality_id": "p09" },
        { "id": "b", "text": "点进去刷评论，结果被算法推荐了更多有趣视频，两个小时过去了。", "target_personality_id": "p10" },
        { "id": "c", "text": "许愿？不如开一局游戏，用实力在虚拟世界里赢取荣耀。", "target_personality_id": "p11" },
        { "id": "d", "text": "立刻截图发到群里，@所有人“速来吃瓜，前排围观！”", "target_personality_id": "p12" }
      ]
    },
    {
      "order": 4,
      "text": "当你感觉压力巨大、情绪低落时，最能治愈你的方式是？",
      "options": [
        { "id": "a", "text": "在图书馆找个安静的角落，读一本喜欢的书，让内心平静下来。", "target_personality_id": "p01" },
        { "id": "b", "text": "倒头就睡，没有什么是一场高质量的睡眠解决不了的。", "target_personality_id": "p05" },
        { "id": "c", "text": "转发锦鲤，或者找塔罗牌算一算，寻求一些神秘主义的安慰。", "target_personality_id": "p09" },
        { "id": "d", "text": "立刻打开待办事项清单，划掉几个已完成的任务，用成就感对抗压力。", "target_personality_id": "p02" }
      ]
    },
    {
      "order": 5,
      "text": "你的手机相册里，存得最多的照片类型是？",
      "options": [
        { "id": "a", "text": "各种零食的包装袋，和床上电脑桌的“生态系统”自拍。", "target_personality_id": "p06" },
        { "id": "b", "text": "短视频里看到的搞笑/生活小技巧截图，虽然“码了等于做了”。", "target_personality_id": "p10" },
        { "id": "c", "text": "各种课程的PPT、板书和资料，堪称移动的数字图书馆。", "target_personality_id": "p03" },
        { "id": "d", "text": "咖啡、能量饮料和“奋斗到天明”的桌面，都是DDL的见证。", "target_personality_id": "p07" }
      ]
    },
    {
      "order": 6,
      "text": "朋友约你出去玩，但你有点懒得动，最可能让你改变主意的理由是？",
      "options": [
        { "id": "a", "text": "“来我家开黑吧，我新买了机械键盘！”", "target_personality_id": "p11" },
        { "id": "b", "text": "“快来，我们一起把你宿舍的照片墙弄好，我买了好多好看的夹子！”", "target_personality_id": "p04" },
        { "id": "c", "text": "“去参加那个讲座吧，听说签个到就算平时分，性价比超高。”", "target_personality_id": "p08" },
        { "id": "d", "text": "“来吃瓜！我刚知道一个关于XXX的惊天大八卦！”", "target_personality_id": "p12" }
      ]
    },
    {
      "order": 7,
      "text": "一个理想的下午茶，对你来说应该是：",
      "options": [
        { "id": "a", "text": "一杯咖啡，一本书，在图书馆的窗边安静地度过。", "target_personality_id": "p01" },
        { "id": "b", "text": "躺在床上，一边吃零食，一边追剧，手边五米内应有尽有。", "target_personality_id": "p06" },
        { "id": "c", "text": "一边喝奶茶，一边和朋友激烈地讨论最新的游戏版本更新。", "target_personality_id": "p11" },
        { "id": "d", "text": "一边喝茶，一边整理本周的知识星球和RSS订阅源。", "target_personality_id": "p03" }
      ]
    },
    {
      "order": 8,
      "text": "临近期末，你的复习状态更接近于：",
      "options": [
        { "id": "a", "text": "困了就睡，绝不硬撑，相信睡眠会帮助大脑巩固记忆。", "target_personality_id": "p05" },
        { "id": "b", "text": "根本停不下来，手机里收藏的“学习妙招”短视频比复习资料还多。", "target_personality_id": "p10" },
        { "id": "c", "text": "精心打扮一番，化上“考试必过锦鲤妆”，在寝室里营造出满满的复习仪式感。", "target_personality_id": "p04" },
        { "id": "d", "text": "严格按照之前制定的复习计划表推进，每天的任务都清晰明确。", "target_personality_id": "p02" }
      ]
    },
    {
      "order": 9,
      "text": "对于“摆烂”这个词，你的理解是？",
      "options": [
        { "id": "a", "text": "这是一种顺应天命的哲学，是与自己和解的智慧。", "target_personality_id": "p09" },
        { "id": "b", "text": "这是DDL来临前的蓄力阶段，是暴风雨前的宁静。", "target_personality_id": "p07" },
        { "id": "c", "text": "这是在互联网信息海洋里冲浪时，必然会抵达的精神港湾。", "target_personality_id": "p12" },
        { "id": "d", "text": "我只求六十分万岁，多一分都浪费，这不叫摆烂，叫精准控制。", "target_personality_id": "p08" }
      ]
    },
    {
      "order": 10,
      "text": "你的信息管理方式更偏向于：",
      "options": [
        { "id": "a", "text": "所有信息都在图书馆的书架上，分门别类，井井有条。", "target_personality_id": "p01" },
        { "id": "b", "text": "大脑就是我最好的收藏夹，虽然有点乱，但DDL前总能奇迹般地找到。", "target_personality_id": "p07" },
        { "id": "c", "text": "刷到就是学到，我的大脑已经被短视频塑造成了信息瀑布流。", "target_personality_id": "p10" },
        { "id": "d", "text": "睡眠是最好的信息处理器，一觉醒来，重要的事自然会浮现。", "target_personality_id": "p05" }
      ]
    },
    {
      "order": 11,
      "text": "如果可以获得一种超能力，你希望是？",
      "options": [
        { "id": "a", "text": "拥有一个永远会自动执行的“人生计划”助手。", "target_personality_id": "p02" },
        { "id": "b", "text": "点石成金，但只为了把考试成绩单上的59分变成60分。", "target_personality_id": "p08" },
        { "id": "c", "text": "拥有千里眼和顺风耳，第一时间吃遍全网的瓜。", "target_personality_id": "p12" },
        { "id": "d", "text": "在床上创造一个独立时空，吃喝玩乐都不需要下床。", "target_personality_id": "p06" }
      ]
    },
    {
      "order": 12,
      "text": "你在社交媒体上最活跃的时刻通常是？",
      "options": [
        { "id": "a", "text": "当有新的笔记软件或信息整理技巧出现时，积极参与讨论和分享。", "target_personality_id": "p03" },
        { "id": "b", "text": "在各种祈福、抽奖、星座运势下留言，希望获得好运。", "target_personality_id": "p09" },
        { "id": "c", "text": "晒出自己新装饰的寝室一角或新入手的提升幸福感的小物件。", "target_personality_id": "p04" },
        { "id": "d", "text": "当喜欢的游戏发布新内容或有大型电竞赛事时。", "target_personality_id": "p11" }
      ]
    },
    {
      "order": 13,
      "text": "毕业论文致谢部分，你最想感谢的是？",
      "options": [
        { "id": "a", "text": "图书馆的每一位管理员和那个你最常坐的座位。", "target_personality_id": "p01" },
        { "id": "b", "text": "那些陪你精准计算学分、研究及格线的“战友们”。", "target_personality_id": "p08" },
        { "id": "c", "text": "你的床，感谢它在你无数个不想奋斗的日子里提供的无私怀抱。", "target_personality_id": "p06" },
        { "id": "d", "text": "你的化妆品和好看的衣服们，它们给了你面对一切的勇气。", "target_personality_id": "p04" }
      ]
    },
    {
      "order": 14,
      "text": "“deadline是第一生产力”这句话，你认为：",
      "options": [
        { "id": "a", "text": "不，周密的计划才是。我从不让自己陷入需要deadline来拯救的境地。", "target_personality_id": "p02" },
        { "id": "b", "text": "是的，但转发锦鲤也是。运气和努力同样重要。", "target_personality_id": "p09" },
        { "id": "c", "text": "错，短视频才是。它能让我忘掉deadline，从而获得暂时的快乐。", "target_personality_id": "p10" },
        { "id": "d", "text": "简直是真理！没有deadline，我的潜力可能永远无法被激发。", "target_personality_id": "p07" }
      ]
    },
    {
      "order": 15,
      "text": "你桌面/床头一定不能少的东西是？",
      "options": [
        { "id": "a", "text": "一套分类清晰的文件收纳盒和标签机。", "target_personality_id": "p03" },
        { "id": "b", "text": "你最喜欢的明星/博主的吃瓜汇总和表情包。", "target_personality_id": "p12" },
        { "id": "c", "text": "一个让你最有安全感的抱枕或眼罩。", "target_personality_id": "p05" },
        { "id": "d", "text": "你最喜欢的游戏的手办或者海报。", "target_personality_id": "p11" }
      ]
    }
  ]
}



# ---------------------------------------------------
# 2. Peewee & Pydantic 模型
# ---------------------------------------------------

class TestRecord(Model):
    """Peewee模型，对应数据库中的 'test_records' 表"""
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    session_id = CharField(max_length=36, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    # 关键：关联到用户表的外键。
    # null=True 表示这条记录初始可以没有对应的用户（即匿名状态）。
    user = ForeignKeyField(User, backref='test_records', null=True)
    
    result_personality_id = EncryptedTextField(
        purpose="test_records.result_personality_id",
        null=True,
    )
    status = CharField(max_length=20, default='IN_PROGRESS') # e.g., IN_PROGRESS, COMPLETED, CLAIMED
    answers_json = EncryptedTextField(
        purpose="test_records.answers_json",
        null=True,
    )
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    def save(self, *args, **kwargs):
        """重写save方法，自动更新updated_at字段"""
        self.updated_at = datetime.now()
        return super(TestRecord, self).save(*args, **kwargs)

    class Meta:
        database = promotion_db
        table_name = 'test_records'


class TestResultResponseModel(BaseModel):
    """最终结果页的响应模型，包含完整的人格信息"""
    id: str = Field(..., description="人格/专业ID")
    college: str = Field(..., description="所属学院")
    major: str = Field(..., description="专业名称")
    college_motto: str = Field(..., description="学院口号")
    description: str = Field(..., description="核心课程描述")
    recommendation: str = Field(..., description="生存指南")


SOUL_DRINK_ASSET_BASE = (
    "https://assets.feelyourself.cn/miniprogram/assets/v1/"
    "pkgAssessment/images/drink-ti"
)

SOUL_DRINK_RESULTS = {
    "STJ": {"drink": "无糖乌龙茶", "result_card": f"{SOUL_DRINK_ASSET_BASE}/result-cards/stj-unsweetened-oolong-tea.jpg"},
    "STP": {"drink": "青柠电解质水", "result_card": f"{SOUL_DRINK_ASSET_BASE}/result-cards/stp-lime-electrolyte-water.jpg"},
    "SFJ": {"drink": "热奶茶", "result_card": f"{SOUL_DRINK_ASSET_BASE}/result-cards/sfj-hot-milk-tea.jpg"},
    "SFP": {"drink": "蜜桃气泡水", "result_card": f"{SOUL_DRINK_ASSET_BASE}/result-cards/sfp-peach-sparkling-water.jpg"},
    "NTJ": {"drink": "冷萃黑咖啡", "result_card": f"{SOUL_DRINK_ASSET_BASE}/result-cards/ntj-cold-brew-black-coffee.jpg"},
    "NTP": {"drink": "特调鸡尾酒", "result_card": f"{SOUL_DRINK_ASSET_BASE}/result-cards/ntp-special-cocktail.jpg"},
    "NFJ": {"drink": "蜂蜜柚子茶", "result_card": f"{SOUL_DRINK_ASSET_BASE}/result-cards/nfj-honey-grapefruit-tea.jpg"},
    "NFP": {"drink": "缤纷水果茶", "result_card": f"{SOUL_DRINK_ASSET_BASE}/result-cards/nfp-colorful-fruit-tea.jpg"},
}

SOUL_DRINK_SCORE_MAP = [
    {"A": {"N": 2}, "B": {"N": 1}, "C": {"S": 1}, "D": {"S": 2}},
    {"A": {"N": 1}, "B": {"S": 1}},
    {"A": {"N": 1}, "B": {"S": 1}},
    {"A": {"S": 1}, "B": {"N": 1}},
    {"A": {"N": 1}, "B": {"S": 1}},
    {"A": {"F": 1}, "B": {"T": 1}},
    {"A": {"T": 1}, "B": {"F": 1}},
    {"A": {"T": 1}, "B": {"F": 1}},
    {"A": {"F": 1}, "B": {"T": 1}},
    {"A": {"F": 1}, "B": {"T": 1}},
    {"A": {"J": 1}, "B": {"P": 1}},
    {"A": {"P": 2}, "B": {"P": 1}, "C": {"J": 1}, "D": {"J": 2}},
    {"A": {"J": 1}, "B": {"P": 1}},
    {"A": {"P": 1}, "B": {"J": 1}},
    {"A": {"J": 1}, "B": {"P": 1}},
]


class SoulDrinkRecord(Model):
    """H5 灵魂饮料测试的匿名记录。"""
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    visitor_token = EncryptedTextField(purpose="soul_drink_records.visitor_token")
    visitor_token_lookup = CharField(max_length=64, unique=True, index=True, null=True)
    status = CharField(max_length=20, default='IN_PROGRESS')
    current_index = IntegerField(default=0)
    answers_json = EncryptedTextField(
        purpose="soul_drink_records.answers_json",
        null=True,
    )
    scores_json = EncryptedTextField(
        purpose="soul_drink_records.scores_json",
        null=True,
    )
    result_type = EncryptedTextField(
        purpose="soul_drink_records.result_type",
        null=True,
    )
    result_drink = EncryptedTextField(
        purpose="soul_drink_records.result_drink",
        null=True,
    )
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)
    completed_at = DateTimeField(null=True)

    def save(self, *args, **kwargs):
        self.updated_at = datetime.now()
        return super(SoulDrinkRecord, self).save(*args, **kwargs)

    class Meta:
        database = promotion_db
        table_name = 'soul_drink_records'


# ---------------------------------------------------
# 3. Table Access Class (数据库操作封装)
# ---------------------------------------------------

class PromotionTable:
    """封装所有针对 'test_records' 表的数据库操作"""
    def __init__(self, db_connection):
        self.db = db_connection
        self.db.create_tables([TestRecord])
        if not test_data.get("personalities"):
             print("⚠️ 警告: 'test_data' 为空，请在 models/promotion.py 中填充它。")

    def create_test_session(self) -> Optional[TestRecord]:
        """创建一个新的测试会话记录。"""
        try:
            return TestRecord.create()
        except Exception as e:
            print(f"创建测试会话失败: {e}")
            return None

    def get_test_record_by_session(self, session_id: str) -> Optional[TestRecord]:
        """通过 session_id 获取测试记录"""
        return TestRecord.get_or_none(TestRecord.session_id == session_id)

    def submit_test_answers(self, session_id: str, answers: List[Dict[str, str]]) -> Optional[str]:
        """提交用户答案，计算并存储最终结果。"""
        record = self.get_test_record_by_session(session_id)
        if not record or record.status != 'IN_PROGRESS':
            return None

        personality_ids = [ans.get("target_personality_id") for ans in answers if ans.get("target_personality_id")]
        if not personality_ids:
            return None

        id_counts = Counter(personality_ids)
        final_result_id = id_counts.most_common(1)[0][0]
        
        record.result_personality_id = final_result_id
        record.answers_json = json.dumps(answers)
        record.status = 'COMPLETED'
        record.save()
        
        return final_result_id

    def link_user_to_session(self, session_id: str, user_id: str) -> Optional[TestRecord]:
        """将一个已登录的用户ID关联到一个已完成的测试会话上。"""
        record = self.get_test_record_by_session(session_id)
        
        if not record or record.status != 'COMPLETED':
            return None
        
        record.user = user_id
        record.status = 'CLAIMED'
        record.save()
        
        return record

    def get_result_by_user_id(self, user_id: str) -> Optional[TestRecord]:
        """根据用户ID，获取他/她最近一次认领的测试结果。"""
        return TestRecord.select().where(
            TestRecord.user == user_id, 
            TestRecord.status == 'CLAIMED'
        ).order_by(TestRecord.created_at.desc()).first()

    def get_personality_details(self, personality_id: str) -> Optional[Dict[str, Any]]:
        """从静态数据中查找并返回完整的人格信息"""
        if not test_data.get("personalities"): return None
        return next((p for p in test_data["personalities"] if p.get("id") == personality_id), None)


class SoulDrinkTable:
    """封装灵魂饮料 H5 匿名记录的数据库操作。"""

    def __init__(self, db_connection):
        self.db = db_connection
        if not self.db.table_exists(SoulDrinkRecord._meta.table_name):
            self.db.create_tables([SoulDrinkRecord], safe=True)
        existing_columns = {
            column.name
            for column in self.db.get_columns(SoulDrinkRecord._meta.table_name)
        }
        if "visitor_token_lookup" not in existing_columns:
            self.db.execute_sql(
                "ALTER TABLE soul_drink_records "
                "ADD COLUMN visitor_token_lookup VARCHAR(64)"
            )
        self.db.execute_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS soul_drink_token_lookup "
            "ON soul_drink_records(visitor_token_lookup)"
        )
        for record in SoulDrinkRecord.select().where(
            SoulDrinkRecord.visitor_token_lookup.is_null(True)
        ):
            record.visitor_token_lookup = blind_index(
                record.visitor_token,
                "soul_drink_records.visitor_token",
            )
            record.save(only=[SoulDrinkRecord.visitor_token_lookup])

    def get_or_create_session(self, visitor_token: Optional[str] = None) -> SoulDrinkRecord:
        if visitor_token:
            record = self.get_by_token(visitor_token)
            if record:
                return record
        token = visitor_token or str(uuid.uuid4())
        return SoulDrinkRecord.create(
            visitor_token=token,
            visitor_token_lookup=blind_index(
                token,
                "soul_drink_records.visitor_token",
            ),
        )

    def get_by_token(self, visitor_token: str) -> Optional[SoulDrinkRecord]:
        lookup = blind_index(
            visitor_token,
            "soul_drink_records.visitor_token",
        )
        return SoulDrinkRecord.get_or_none(
            SoulDrinkRecord.visitor_token_lookup == lookup
        )

    def save_progress(self, visitor_token: str, answers: List[Optional[str]], current_index: int) -> Optional[SoulDrinkRecord]:
        record = self.get_by_token(visitor_token)
        if not record:
            return None

        record.answers_json = json.dumps(answers, ensure_ascii=False)
        record.current_index = max(0, min(current_index, len(SOUL_DRINK_SCORE_MAP) - 1))
        if record.status != 'COMPLETED':
            record.status = 'IN_PROGRESS'
        record.save()
        return record

    def complete(self, visitor_token: str, answers: List[str]) -> Optional[SoulDrinkRecord]:
        record = self.get_by_token(visitor_token)
        if not record:
            return None

        calculated = self.calculate_result(answers)
        result = SOUL_DRINK_RESULTS.get(calculated["type"])
        if not result:
            return None

        record.answers_json = json.dumps(answers, ensure_ascii=False)
        record.scores_json = json.dumps(calculated["scores"], ensure_ascii=False)
        record.result_type = calculated["type"]
        record.result_drink = result["drink"]
        record.current_index = len(SOUL_DRINK_SCORE_MAP) - 1
        record.status = 'COMPLETED'
        record.completed_at = datetime.now()
        record.save()
        return record

    def restart(self, visitor_token: str) -> Optional[SoulDrinkRecord]:
        record = self.get_by_token(visitor_token)
        if not record:
            return None

        record.status = 'IN_PROGRESS'
        record.current_index = 0
        record.answers_json = None
        record.scores_json = None
        record.result_type = None
        record.result_drink = None
        record.completed_at = None
        record.save()
        return record

    def serialize(self, record: SoulDrinkRecord) -> Dict[str, Any]:
        answers = []
        scores = None
        if record.answers_json:
            try:
                answers = json.loads(record.answers_json)
            except json.JSONDecodeError:
                answers = []
        if record.scores_json:
            try:
                scores = json.loads(record.scores_json)
            except json.JSONDecodeError:
                scores = None

        result = SOUL_DRINK_RESULTS.get(record.result_type or "")
        return {
            "visitor_token": record.visitor_token,
            "status": record.status,
            "current_index": record.current_index,
            "answers": answers,
            "scores": scores,
            "result_type": record.result_type,
            "result_drink": record.result_drink,
            "result_card": result["result_card"] if result else None,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
            "completed_at": record.completed_at,
        }

    @staticmethod
    def calculate_result(answers: List[str]) -> Dict[str, Any]:
        scores = {"S": 0, "N": 0, "T": 0, "F": 0, "J": 0, "P": 0}
        for index, answer in enumerate(answers):
            if index >= len(SOUL_DRINK_SCORE_MAP):
                continue
            option_scores = SOUL_DRINK_SCORE_MAP[index].get(answer)
            if not option_scores:
                continue
            for key, value in option_scores.items():
                if key not in scores:
                    continue
                try:
                    scores[key] += int(value)
                except (TypeError, ValueError):
                    continue

        result_type = (
            ("S" if scores["S"] > scores["N"] else "N")
            + ("T" if scores["T"] > scores["F"] else "F")
            + ("J" if scores["J"] > scores["P"] else "P")
        )
        return {"scores": scores, "type": result_type}

# ---------------------------------------------------
# 4. 实例化 Table Access 对象
# ---------------------------------------------------
promotion_table = PromotionTable(promotion_db)
soul_drink_table = SoulDrinkTable(promotion_db)
