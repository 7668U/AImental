# model/assessment.py

import uuid
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from peewee import Model, CharField, IntegerField, DateTimeField, TextField, ForeignKeyField, FloatField
from pydantic import BaseModel, Field

from db import assessment_db
from .user import User  # 假设 User 模型可以从 .user 导入

# --- 静态配置 ---
ASSESSMENT_DATA_DIR = "assessment_data/"

# ---------------------------------------------------
# 1. Peewee 数据模型 (数据库表结构)
# ---------------------------------------------------

class Scale(Model):
    """量表定义表 (题库总表)"""
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    short_name = CharField(max_length=50, unique=True, index=True, help_text="量表的唯一简称, 如 'PHQ-9'")
    name = CharField(max_length=255, help_text="量表的全称")
    description = TextField(help_text="对量表的简短描述")
    category = CharField(max_length=50, index=True, default='专业测试', help_text="前端分类: '专业测试' 或 '趣味测试'")
    assessment_type = CharField(max_length=50, index=True, default='scoring', help_text="后端类型: 'scoring' (打分) 或 'categorical' (分类)")
    json_data = TextField(help_text="存储量表完整结构(题目、选项、计分规则、解释)的JSON字符串")
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        database = assessment_db
        table_name = 'scales'

class UserAssessment(Model):
    """用户测评记录表"""
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    user = ForeignKeyField(User, backref='assessments', field='id', on_delete='CASCADE')
    scale = ForeignKeyField(Scale, backref='attempts', field='id', on_delete='SET NULL', null=True)
    answers = TextField(help_text="用户提交的答案详情 (JSON字符串)")
    raw_score = FloatField(null=True, help_text="原始总分")
    final_score = FloatField(null=True, help_text="最终标准分 (如果适用)")
    result_level = CharField(max_length=255, null=True, help_text="结果等级或分类名, 如 '轻度抑郁' 或 '图书馆生态信息学'")
    result_interpretation = TextField(null=True, help_text="对结果的详细文字解释")
    result_recommendation = TextField(null=True, help_text="给用户的建议")
    result_details = TextField(null=True, help_text="存储额外结果详情的JSON字符串")
    
    completed_at = DateTimeField(default=datetime.now, help_text="测评完成时间")

    class Meta:
        database = assessment_db
        table_name = 'user_assessments'

# ---------------------------------------------------
# 2. Pydantic 数据模型 (API接口数据结构)
# ---------------------------------------------------

class ScaleInfoResponse(BaseModel):
    id: str
    short_name: str
    name: str
    description: str
    category: str
    assessment_type: str
    class Config:
        from_attributes = True

class ScaleDetailResponse(ScaleInfoResponse):
    json_data: Dict[str, Any]

class SubmitAnswersRequest(BaseModel):
    scale_id: str
    answers: Dict[str, str] 

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
    result_details: Optional[Dict[str, Any]] = None
    completed_at: datetime
    scale_info: Optional[ScaleInfoResponse] = None
    scale_details: Optional[Dict[str, Any]] = None

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
        self.initialize_scales_from_json()

    def initialize_scales_from_json(self):
        """
        【修改版】从 /assessment_data/ 文件夹读取JSON文件并加载到数据库。
        如果数据库中已存在同名short_name的量表，则会跳过该文件。
        """
        print("🔍 Starting scale initialization from JSON files...")
        if not os.path.exists(ASSESSMENT_DATA_DIR):
            print(f"⚠️ Directory '{ASSESSMENT_DATA_DIR}' not found. Skipping initialization.")
            return

        for filename in os.listdir(ASSESSMENT_DATA_DIR):
            if filename.endswith(".json"):
                # 1. 从文件名直接获取 short_name (例如 'phq-9.json' -> 'phq-9')
                short_name_from_file = filename[:-5]

                # 2. 查询数据库，检查该 short_name 是否已存在
                # Peewee的 .get_or_none() 方法非常适合这个场景
                if Scale.get_or_none(Scale.short_name == short_name_from_file):
                    # 3. 如果已存在，打印信息并跳过
                    print(f"ℹ️ Scale '{short_name_from_file}' already exists. Skipping file '{filename}'.")
                    continue
                
                # 4. 如果不存在，执行加载和创建逻辑
                print(f"➕ Scale '{short_name_from_file}' not found. Loading from '{filename}'...")
                filepath = os.path.join(ASSESSMENT_DATA_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        scale_info = data.get('scale_info', {})
                        
                        # 为确保数据一致性，我们优先使用文件名作为short_name
                        # 并使用 create() 方法，因为它明确表示创建新记录
                        Scale.create(
                            short_name=short_name_from_file,
                            name=scale_info.get('name', 'N/A'),
                            description=scale_info.get('description', ''),
                            category=scale_info.get('category', '专业测试'),
                            assessment_type=scale_info.get('assessment_type', 'scoring'),
                            json_data=json.dumps(data, ensure_ascii=False)
                        )
                        print(f"✅ Scale '{short_name_from_file}' loaded successfully.")
                except Exception as e:
                    # 增加错误处理，防止因单个文件格式错误导致整个初始化中断
                    print(f"❌ Error processing file {filename}: {e}")

        print("✨ Scale initialization complete.")
    def get_all_scales(self) -> List[Scale]:
        return list(Scale.select(
            Scale.id, Scale.short_name, Scale.name, Scale.description, Scale.category, Scale.assessment_type
        ))
        
    def get_scale_by_id(self, scale_id: str) -> Optional[Scale]:
        return Scale.get_or_none(Scale.id == scale_id)

    def _calculate_scoring_result(self, request_answers: Dict[str, Any], scale_data: Dict) -> Dict:
        """处理打分测试的计分逻辑"""
        rules = scale_data.get('scale_info', {}).get('scoring_rules', {})
        interpretations = scale_data.get('interpretations', [])
        raw_score = sum(float(v) for v in request_answers.values())
        
        final_score = raw_score * rules.get('multiplier', 1)
        # ... 其他打分逻辑 ...

        result = {"raw_score": raw_score, "final_score": final_score, "result_details": None}
        for interp in interpretations:
            if interp.get('min_score', -1) <= final_score <= interp.get('max_score', float('inf')):
                result.update({
                    "result_level": interp.get('level'),
                    "result_interpretation": interp.get('interpretation', ''),
                    "result_recommendation": interp.get('recommendation', ''),
                })
                break
        return result

    def _calculate_categorical_result(self, request_answers: Dict[str, str], scale_data: Dict) -> Dict:
        """处理分类测试的计分逻辑"""
        questions = scale_data.get('questions', [])
        interpretations = scale_data.get('interpretations', {})
        questions_dict = {str(q['order']): q for q in questions}
        
        personality_counts = {}
        for q_order, option_id in request_answers.items():
            question = questions_dict.get(q_order)
            if not question: continue
            
            selected_option = next((opt for opt in question.get('options', []) if opt['id'] == option_id), None)
            
            if selected_option:
                target_id = selected_option.get('target_personality_id')
                if target_id:
                    personality_counts[target_id] = personality_counts.get(target_id, 0) + 1
        
        if not personality_counts:
            return {
                "result_level": "无法确定",
                "result_interpretation": "您的答案无法匹配到任何结果，请重试。",
                "result_recommendation": "", "result_details": None
            }

        final_personality_id = max(personality_counts, key=personality_counts.get)
        final_result = interpretations.get(final_personality_id, {})
        
        # 【已补全】从这里开始是之前缺失的代码
        return {
            "raw_score": None,
            "final_score": None,
            "result_level": final_result.get('major'),
            "result_interpretation": final_result.get('description'),
            "result_recommendation": final_result.get('recommendation'),
            "result_details": {
                "college": final_result.get('college'),
                "college_motto": final_result.get('college_motto'),
                # 【已修正】从 final_result 中安全地获取 image_url
                "image_url": final_result.get('image_url') 
            }
        }

    def create_user_assessment(self, user_id: str, request_data: SubmitAnswersRequest) -> Optional[UserAssessment]:
        """核心方法：根据量表类型进行评分，并创建测评记录"""
        scale = self.get_scale_by_id(request_data.scale_id)
        if not scale:
            return None
            
        scale_data = json.loads(scale.json_data)
        
        result_data = {}
        if scale.assessment_type == 'scoring':
            result_data = self._calculate_scoring_result(request_data.answers, scale_data)
        elif scale.assessment_type == 'categorical':
            result_data = self._calculate_categorical_result(request_data.answers, scale_data)
        else:
            raise ValueError(f"Unsupported assessment type: {scale.assessment_type}")
        
        user_assessment = UserAssessment.create(
            user=user_id,
            scale=scale.id,
            answers=json.dumps(request_data.answers, ensure_ascii=False),
            raw_score=result_data.get('raw_score'),
            final_score=result_data.get('final_score'),
            result_level=result_data.get('result_level'),
            result_interpretation=result_data.get('result_interpretation'),
            result_recommendation=result_data.get('result_recommendation'),
            result_details=json.dumps(result_data.get('result_details'), ensure_ascii=False) if result_data.get('result_details') else None
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