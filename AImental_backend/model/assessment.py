# model/assessment.py

import uuid
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

# 1. 导入 Peewee 和 Pydantic 的必要组件
from peewee import Model, CharField, IntegerField, DateTimeField, TextField, ForeignKeyField, FloatField
from pydantic import BaseModel, Field

# 2. 导入数据库连接和外部模型
from db import assessment_db
from .user import User  # 假设 User 模型可以从 .user 导入

# --- 静态配置 ---
ASSESSMENT_DATA_DIR = "assessment_data/"

# ---------------------------------------------------
# 1. Peewee 数据模型 (数据库表结构)
# ---------------------------------------------------

class Scale(Model):
    """
    量表定义表 (题库总表)。
    存储所有心理测评量表的静态定义数据。
    """
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    short_name = CharField(max_length=50, unique=True, index=True, help_text="量表的唯一简称, 如 'PHQ-9'")
    name = CharField(max_length=255, help_text="量表的全称")
    description = TextField(help_text="对量表的简短描述")
    # 直接将量表的完整JSON结构存储起来，极大提高灵活性
    json_data = TextField(help_text="存储量表完整结构(题目、选项、计分规则、解释)的JSON字符串")
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        database = assessment_db
        table_name = 'scales'

class UserAssessment(Model):
    """
    用户测评记录表。
    存储用户每一次完成测评的具体记录。
    """
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    # 外键，关联到具体的用户和量表
    user = ForeignKeyField(User, backref='assessments', field='id', on_delete='CASCADE')
    scale = ForeignKeyField(Scale, backref='attempts', field='id', on_delete='SET NULL', null=True)
    
    # 存储用户答案的JSON字符串, e.g., '{"q1_order": 1, "q2_order": 3, ...}'
    answers = TextField(help_text="用户提交的答案详情")
    
    # 存储分数和结果
    raw_score = FloatField(null=True, help_text="原始总分")
    final_score = FloatField(null=True, help_text="最终标准分 (如果适用)")
    result_level = CharField(max_length=255, null=True, help_text="结果等级, 如 '轻度抑郁' 或 '安全型'")
    result_interpretation = TextField(null=True, help_text="对结果的详细文字解释")
    result_recommendation = TextField(null=True, help_text="给用户的建议")
    
    completed_at = DateTimeField(default=datetime.now, help_text="测评完成时间")

    class Meta:
        database = assessment_db
        table_name = 'user_assessments'

# ---------------------------------------------------
# 2. Pydantic 数据模型 (API接口数据结构)
# ---------------------------------------------------

# 用于API返回的量表基本信息模型
class ScaleInfoResponse(BaseModel):
    id: str
    short_name: str
    name: str
    description: str
    
    class Config:
        from_attributes = True

# 用于API返回的量表完整详情模型
class ScaleDetailResponse(ScaleInfoResponse):
    # 将json_data字段解析为Python字典返回给前端
    json_data: Dict[str, Any]

# 用户提交答案的请求体模型
class SubmitAnswersRequest(BaseModel):
    scale_id: str
    # 答案格式：{题目order: 选项score}，例如 {1: 3, 2: 1, ...}
    answers: Dict[int, int] 

# 用户测评记录的返回模型
class UserAssessmentResponse(BaseModel):
    id: str
    user_id: str
    scale_id: str
    answers: Dict[str, Any]
    raw_score: Optional[float] = None
    final_score: Optional[float] = None
    result_level: Optional[str] = None
    result_interpretation: Optional[str] = None
    result_recommendation: Optional[str] = None
    completed_at: datetime
    scale_info: Optional[ScaleInfoResponse] = None # 附带量表基本信息

    class Config:
        from_attributes = True

# ---------------------------------------------------
# 3. 数据表访问类 (封装所有数据库操作)
# ---------------------------------------------------

class AssessmentTables:
    """封装所有与测评相关的数据库操作"""
    def __init__(self, db_connection):
        self.db = db_connection
        self.db.create_tables([Scale, UserAssessment])
        # self.initialize_scales_from_json()
    # --- Scale (题库) 相关方法 ---

    def initialize_scales_from_json(self):
        """
        从 /assessment_data/ 文件夹读取所有 .json 文件，
        并将其内容创建或更新到 Scale 数据库表中。
        这是一个幂等操作，可以重复执行。
        """
        print("🔍 Starting scale initialization from JSON files...")
        if not os.path.exists(ASSESSMENT_DATA_DIR):
            print(f"⚠️ Directory '{ASSESSMENT_DATA_DIR}' not found. Skipping initialization.")
            return

        for filename in os.listdir(ASSESSMENT_DATA_DIR):
            if filename.endswith(".json"):
                filepath = os.path.join(ASSESSMENT_DATA_DIR, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    scale_info = data.get('scale_info', {})
                    short_name = scale_info.get('short_name')
                    
                    if not short_name:
                        print(f"❌ Skipping {filename}: 'short_name' not found in 'scale_info'.")
                        continue
                    
                    # 使用 Peewee 的 replace 方法，实现存在即更新，不存在即插入
                    Scale.replace(
                        short_name=short_name,
                        name=scale_info.get('name', 'N/A'),
                        description=scale_info.get('description', ''),
                        json_data=json.dumps(data, ensure_ascii=False) # 存为JSON字符串
                    ).execute()
                    print(f"✅ Scale '{short_name}' has been loaded/updated from {filename}.")
        print("✨ Scale initialization complete.")


    def get_all_scales(self) -> List[Scale]:
        """
        获取所有可用量表的列表。
        【优化】使用 .select() 只获取前端列表展示所必需的字段，以提高效率。
        """
        return list(Scale.select(
            Scale.id, 
            Scale.short_name, 
            Scale.name, 
            Scale.description
        ))
        
    def get_scale_by_id(self, scale_id: str) -> Optional[Scale]:
        """根据主键ID获取单个量表定义"""
        return Scale.get_or_none(Scale.id == scale_id)
        
    def get_scale_by_short_name(self, short_name: str) -> Optional[Scale]:
        """根据简称获取单个量表定义"""
        return Scale.get_or_none(Scale.short_name == short_name)

    # --- UserAssessment (用户记录) 相关方法 ---

    def create_user_assessment(self, user_id: str, request_data: SubmitAnswersRequest) -> Optional[UserAssessment]:
        """
        核心方法：接收用户答案，进行评分，并创建一条测评记录。
        """
        scale = self.get_scale_by_id(request_data.scale_id)
        if not scale:
            return None # 或者抛出异常
            
        # 1. 解析计分逻辑
        scale_data = json.loads(scale.json_data)
        rules = scale_data.get('scale_info', {}).get('scoring_rules', {})
        questions = {q['order']: q for q in scale_data.get('questions', [])}
        interpretations = scale_data.get('interpretations', [])

        # 2. 计算分数 (此处为简化版，需根据rules扩展)
        raw_score = 0
        final_score = 0
        result_level = "N/A" # 默认值
        
        # 简单加总逻辑 (可扩展为处理反向计分, 乘系数, 分组等)
        for q_order, choice_score in request_data.answers.items():
            # 这里可以加入更复杂的逻辑，比如检查is_reverse_scored
            raw_score += choice_score
        
        # 示例：处理乘系数和取整/四舍五入
        final_score = raw_score * rules.get('multiplier', 1)
        if rules.get('post_action') == 'to_integer':
            final_score = int(final_score)
        elif rules.get('post_action') == 'round':
            final_score = round(final_score)

        # 3. 匹配结果解释
        final_interpretation = {}
        for interp in interpretations:
            if interp.get('min_score', -1) <= final_score <= interp.get('max_score', float('inf')):
                result_level = interp.get('level')
                final_interpretation = interp
                break
        
        # 4. 创建数据库记录
        user_assessment = UserAssessment.create(
            user=user_id,
            scale=scale.id,
            answers=json.dumps(request_data.answers, ensure_ascii=False),
            raw_score=raw_score,
            final_score=final_score,
            result_level=result_level,
            result_interpretation=final_interpretation.get('interpretation', ''),
            result_recommendation=final_interpretation.get('recommendation', '')
        )
        return user_assessment

    def get_assessments_by_user(self, user_id: str) -> List[UserAssessment]:
        """获取一个用户的所有测评历史记录"""
        return list(UserAssessment.select().where(UserAssessment.user == user_id).order_by(UserAssessment.completed_at.desc()))

    def get_assessment_by_id(self, record_id: str) -> Optional[UserAssessment]:
        """根据记录ID获取单条测评结果"""
        return UserAssessment.get_or_none(UserAssessment.id == record_id)

    def delete_user_assessment(self, user_id: str, record_id: str) -> bool:
        """删除一条属于特定用户的测评记录"""
        query = UserAssessment.delete().where(
            (UserAssessment.id == record_id) & (UserAssessment.user == user_id)
        )
        deleted_rows = query.execute()
        return deleted_rows > 0

# --- 实例化数据表访问对象 ---
assessment_tables = AssessmentTables(assessment_db)