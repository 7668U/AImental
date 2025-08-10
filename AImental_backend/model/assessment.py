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
from .user import User

# --- 静态配置 ---
ASSESSMENT_DATA_DIR = "assessment_data/"
TEST_DATA_DIR = "personality_test_data/"
# ---------------------------------------------------
# 1. Peewee 数据模型 (数据库表结构)
# ---------------------------------------------------

class Scale(Model):
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    short_name = CharField(max_length=50, unique=True, index=True)
    name = CharField(max_length=255)
    description = TextField()
    json_data = TextField()
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        database = assessment_db
        table_name = 'scales'

class UserAssessment(Model):
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    user = ForeignKeyField(User, backref='assessments', field='id', on_delete='CASCADE')
    scale = ForeignKeyField(Scale, backref='attempts', field='id', on_delete='SET NULL', null=True)
    answers = TextField()
    raw_score = FloatField(null=True)
    final_score = FloatField(null=True)
    result_level = CharField(max_length=255, null=True)
    result_interpretation = TextField(null=True)
    result_recommendation = TextField(null=True)
    completed_at = DateTimeField(default=datetime.now)

    class Meta:
        database = assessment_db
        table_name = 'user_assessments'

class PersonalityTest(Model):
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    short_name = CharField(max_length=50, unique=True, index=True)
    name = CharField(max_length=255)
    description = TextField()
    json_data = TextField()
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        database = assessment_db
        table_name = 'personality_tests'

class UserPersonalityTest(Model):
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    user = ForeignKeyField(User, backref='personality_tests', field='id', on_delete='CASCADE')
    test = ForeignKeyField(PersonalityTest, backref='attempts', field='id', on_delete='SET NULL', null=True)
    answers = TextField()
    scores_details = TextField()
    result_personality_id = CharField(max_length=50)
    result_college = CharField(max_length=255)
    result_major = CharField(max_length=255)
    result_interpretation = TextField()
    result_recommendation = TextField()
    completed_at = DateTimeField(default=datetime.now)

    class Meta:
        database = assessment_db
        table_name = 'user_personality_tests'

# ---------------------------------------------------
# 2. Pydantic 数据模型 (API接口数据结构)
# ---------------------------------------------------

class ScaleInfoResponse(BaseModel):
    id: str
    short_name: str
    name: str
    description: str
    class Config: from_attributes = True

class ScaleDetailResponse(ScaleInfoResponse):
    json_data: Dict[str, Any]

class SubmitAnswersRequest(BaseModel):
    scale_id: str
    answers: Dict[int, int]

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
    scale_info: Optional[ScaleInfoResponse] = None
    class Config: from_attributes = True

class PersonalityTestInfoResponse(BaseModel):
    id: str
    short_name: str
    name: str
    description: str
    class Config: from_attributes = True

class SubmitPersonalityTestRequest(BaseModel):
    test_id: str
    answers: Dict[int, str]

class UserPersonalityTestResponse(BaseModel):
    id: str
    user_id: str
    test_id: str
    scores_details: Dict[str, int]
    result_personality_id: str
    result_college: str
    result_major: str
    result_interpretation: str
    result_recommendation: str
    completed_at: datetime
    test_info: Optional[PersonalityTestInfoResponse] = None
    class Config: from_attributes = True

# ---------------------------------------------------
# 3. 数据表访问类 (封装所有数据库操作)
# ---------------------------------------------------

class AssessmentTables:
    def __init__(self, db_connection):
        self.db = db_connection
        self.db.create_tables([Scale, UserAssessment])
        self.initialize_scales_from_json()

    def initialize_scales_from_json(self):
        if not os.path.exists(ASSESSMENT_DATA_DIR): return
        for filename in os.listdir(ASSESSMENT_DATA_DIR):
            if filename.endswith(".json"):
                filepath = os.path.join(ASSESSMENT_DATA_DIR, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    scale_info = data.get('scale_info', {})
                    short_name = scale_info.get('short_name')
                    if not short_name: continue
                    Scale.replace(
                        short_name=short_name,
                        name=scale_info.get('name', 'N/A'),
                        description=scale_info.get('description', ''),
                        json_data=json.dumps(data, ensure_ascii=False)
                    ).execute()

    def get_all_scales(self) -> List[Scale]:
        return list(Scale.select(Scale.id, Scale.short_name, Scale.name, Scale.description))
        
    def get_scale_by_id(self, scale_id: str) -> Optional[Scale]:
        return Scale.get_or_none(Scale.id == scale_id)
        
    def get_scale_by_short_name(self, short_name: str) -> Optional[Scale]:
        return Scale.get_or_none(Scale.short_name == short_name)

    def create_user_assessment(self, user_id: str, request_data: SubmitAnswersRequest) -> Optional[UserAssessment]:
        scale = self.get_scale_by_id(request_data.scale_id)
        if not scale: return None
            
        scale_data = json.loads(scale.json_data)
        rules = scale_data.get('scale_info', {}).get('scoring_rules', {})
        interpretations = scale_data.get('interpretations', [])

        raw_score = sum(request_data.answers.values())
        
        final_score = raw_score * rules.get('multiplier', 1)
        if rules.get('post_action') == 'to_integer': final_score = int(final_score)
        elif rules.get('post_action') == 'round': final_score = round(final_score)

        result_level, final_interpretation = "N/A", {}
        for interp in interpretations:
            if interp.get('min_score', -1) <= final_score <= interp.get('max_score', float('inf')):
                result_level, final_interpretation = interp.get('level'), interp
                break
        
        return UserAssessment.create(
            user=user_id, scale=scale.id,
            answers=json.dumps(request_data.answers, ensure_ascii=False),
            raw_score=raw_score, final_score=final_score, result_level=result_level,
            result_interpretation=final_interpretation.get('interpretation', ''),
            result_recommendation=final_interpretation.get('recommendation', '')
        )

    def get_assessments_by_user(self, user_id: str) -> List[UserAssessment]:
        """获取一个用户的所有测评历史记录"""
        # 【优化】关联查询出量表名称，方便后续格式化
        return list(UserAssessment.select(UserAssessment, Scale.name.alias('scale_name'))
                                .join(Scale, on=(UserAssessment.scale == Scale.id))
                                .where(UserAssessment.user == user_id)
                                .order_by(UserAssessment.completed_at.desc()))

    def get_assessment_by_id(self, record_id: str) -> Optional[UserAssessment]:
        return UserAssessment.get_or_none(UserAssessment.id == record_id)

    def delete_user_assessment(self, user_id: str, record_id: str) -> bool:
        query = UserAssessment.delete().where((UserAssessment.id == record_id) & (UserAssessment.user == user_id))
        return query.execute() > 0

assessment_tables = AssessmentTables(assessment_db)

class PersonalityTestTables:
    def __init__(self, db_connection):
        self.db = db_connection
        self.db.create_tables([PersonalityTest, UserPersonalityTest])
        self.initialize_personality_tests_from_json()

    def initialize_personality_tests_from_json(self):
        if not os.path.exists(TEST_DATA_DIR): return
        for filename in os.listdir(TEST_DATA_DIR):
            if filename.endswith(".json"):
                filepath = os.path.join(TEST_DATA_DIR, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    info = data.get('test_info', {})
                    short_name = info.get('id')
                    if not short_name: continue
                    PersonalityTest.replace(
                        short_name=short_name, name=info.get('name', 'N/A'),
                        description=info.get('description', ''),
                        json_data=json.dumps(data, ensure_ascii=False)
                    ).execute()

    def get_all_personality_tests(self) -> List[PersonalityTest]:
        return list(PersonalityTest.select(PersonalityTest.id, PersonalityTest.short_name, PersonalityTest.name, PersonalityTest.description))

    def get_personality_test_by_id(self, test_id: str) -> Optional[PersonalityTest]:
        return PersonalityTest.get_or_none(PersonalityTest.id == test_id)

    def create_user_personality_test(self, user_id: str, request_data: SubmitPersonalityTestRequest) -> Optional[UserPersonalityTest]:
        test = self.get_personality_test_by_id(request_data.test_id)
        if not test: return None

        test_data, personalities, questions = json.loads(test.json_data), {}, {}
        personalities = {p['id']: p for p in test_data.get('personalities', [])}
        questions = {q['order']: q for q in test_data.get('questions', [])}
        if not personalities or not questions: raise ValueError(f"Invalid JSON data for test {test.id}")

        scores = {p_id: 0 for p_id in personalities.keys()}
        for q_order, option_id in request_data.answers.items():
            question = questions.get(int(q_order))
            if not question: continue
            chosen_option = next((opt for opt in question.get('options', []) if opt['id'] == option_id), None)
            if chosen_option and 'target_personality_id' in chosen_option:
                if (target_id := chosen_option['target_personality_id']) in scores:
                    scores[target_id] += 1

        result_id = max(scores, key=scores.get)
        if not (result_details := personalities.get(result_id)): raise ValueError(f"Result ID {result_id} not found")

        return UserPersonalityTest.create(
            user=user_id, test=test.id,
            answers=json.dumps(request_data.answers, ensure_ascii=False),
            scores_details=json.dumps(scores, ensure_ascii=False),
            result_personality_id=result_id,
            result_college=result_details.get('college', 'N/A'),
            result_major=result_details.get('major', 'N/A'),
            result_interpretation=result_details.get('description', ''),
            result_recommendation=result_details.get('recommendation', '')
        )

    def get_personality_tests_by_user(self, user_id: str) -> List[UserPersonalityTest]:
        """获取一个用户的所有人格测试历史记录"""
        # 【优化】同样进行关联查询
        return list(UserPersonalityTest.select(UserPersonalityTest, PersonalityTest.name.alias('test_name'))
                                     .join(PersonalityTest, on=(UserPersonalityTest.test == PersonalityTest.id))
                                     .where(UserPersonalityTest.user == user_id)
                                     .order_by(UserPersonalityTest.completed_at.desc()))

    def get_personality_test_by_record_id(self, record_id: str) -> Optional[UserPersonalityTest]:
        return UserPersonalityTest.get_or_none(UserPersonalityTest.id == record_id)
    
    def delete_user_personality_test(self, user_id: str, record_id: str) -> bool:
        query = UserPersonalityTest.delete().where((UserPersonalityTest.id == record_id) & (UserPersonalityTest.user == user_id))
        return query.execute() > 0
    
personality_test_manager = PersonalityTestTables(assessment_db)
