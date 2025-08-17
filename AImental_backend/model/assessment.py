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
    instructions: Optional[str] = None  # <--- 在这里添加 instructions 字段
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
        # self.db.drop_tables([Scale, UserAssessment], safe=True)
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

    # --- ▼▼▼ 在这里添加下面的新方法 ▼▼▼ ---
    def get_formatted_scale_details_by_id(self, scale_id: str) -> Optional[Dict[str, Any]]:
        """
        【新增】获取并格式化单个量表详情，专为API响应设计。
        这个方法会解析 json_data，提取出 instructions 和题目等信息，
        并整合成一个扁平的字典返回。
        """
        scale = self.get_scale_by_id(scale_id)
        if not scale:
            return None

        # 解析存储在数据库中的JSON字符串
        try:
            full_data = json.loads(scale.json_data)
        except json.JSONDecodeError:
            # 如果JSON格式错误，返回基础信息并忽略附加数据
            full_data = {}

        scale_info = full_data.get('scale_info', {})

        # 组装前端需要的最终数据结构
        response_data = {
            "id": scale.id,
            "short_name": scale.short_name,
            "name": scale.name,
            "description": scale.description,
            "category": scale.category,
            "assessment_type": scale.assessment_type,
            # 从解析后的JSON中提取 instructions
            "instructions": scale_info.get('instructions'),
            # 同时也可以把题目和选项带上，供测试页面使用
            "questions": full_data.get('questions', []),
            "choices": full_data.get('choices', [])
        }
        return response_data
    def get_all_scales(self) -> List[Scale]:
        return list(Scale.select(
            Scale.id, Scale.short_name, Scale.name, Scale.description, Scale.category, Scale.assessment_type
        ))
        
    def get_scale_by_id(self, scale_id: str) -> Optional[Scale]:
        return Scale.get_or_none(Scale.id == scale_id)

    def _calculate_scoring_result(self, request_answers: Dict[str, Any], scale_data: Dict) -> Dict:
        """【修改版】处理打分测试的计分逻辑，支持反向计分和谎言量表"""
        rules = scale_data.get('scale_info', {}).get('scoring_rules', {})
        interpretations = scale_data.get('interpretations', [])
        
        # 1. 获取计分规则
        # 兼容 "reverse_scoring_items" 和 "reverse_scored_items" 两种可能的拼写
        reverse_items = set(rules.get('reverse_scoring_items', []) + rules.get('reverse_scored_items', []))
        
        # 新增：获取谎言量表题目，如果JSON中定义了的话
        lie_scale_items = set(rules.get('lie_scale_items', []))

        raw_score = 0
        # 2. 遍历用户答案进行计分
        for q_order_str, score_str in request_answers.items():
            try:
                q_order = int(q_order_str)
                score = float(score_str)
            except (ValueError, TypeError):
                continue # 如果题目序号或分数不是数字，则跳过

            # 3. 如果是谎言量表题目，则不计入总分
            if q_order in lie_scale_items:
                continue

            # 4. 应用反向计分逻辑
            if q_order in reverse_items:
                # 对于SEI的 "像我"(1分) / "不像我"(0分) 体系，反向计分就是用最高分1减去得分
                # "像我"(得1分) -> 1 - 1 = 0分
                # "不像我"(得0分) -> 1 - 0 = 1分
                raw_score += (1 - score)
            else:
                # 正常计分
                raw_score += score
                
        # 5. 最终分数计算 (例如乘以系数等，当前用不上但保留)
        final_score = raw_score * rules.get('multiplier', 1)

        result = {"raw_score": raw_score, "final_score": final_score, "result_details": None}
        
        # 6. 匹配分数解释
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
        """【最终完善版】处理分类测试的计分逻辑，支持多种计分模型"""
        
        rules = scale_data.get('scale_info', {}).get('scoring_rules', {})
        scoring_type = rules.get('type')
        interpretations = scale_data.get('interpretations', [])

        # ==============================================================================
        # 规则 1: 处理 ECR 问卷的 "subscale_average_2d" (二维度平均分)
        # ==============================================================================
        if scoring_type == 'subscale_average_2d':
            # ... (这部分代码保持不变) ...
            subscale_scores = {"焦虑": [], "回避": []}
            questions_map = {str(q['order']): q for q in scale_data.get('questions', [])}
            choices_map = {str(c.get('id')): c.get('score', 0) for c in scale_data.get('choices', [])}

            for q_order_str, option_id in request_answers.items():
                question = questions_map.get(q_order_str)
                if not question: continue
                
                score = choices_map.get(option_id)
                if score is None: continue

                subscale = question.get('subscale')
                if question.get('reverse_scored'):
                    score = 8 - score
                if subscale in subscale_scores:
                    subscale_scores[subscale].append(score)

            avg_anxiety = sum(subscale_scores["焦虑"]) / len(subscale_scores["焦虑"]) if subscale_scores["焦虑"] else 0
            avg_avoidance = sum(subscale_scores["回避"]) / len(subscale_scores["回避"]) if subscale_scores["回避"] else 0
            
            anxiety_level = "高焦虑" if avg_anxiety > 4 else "低焦虑"
            avoidance_level = "高回避" if avg_avoidance > 4 else "低回避"
            condition_str = f"{anxiety_level} & {avoidance_level}"
            
            final_result_model = next((m for m in rules.get('model', []) if m['condition'] == condition_str), None)
            
            if final_result_model:
                result_level = final_result_model.get('level')
                interpretation_data = next((i for i in interpretations if i.get('level') == result_level), {})
                return {
                    "raw_score": None, "final_score": None, "result_level": result_level,
                    "result_interpretation": interpretation_data.get('interpretation', ''),
                    "result_recommendation": interpretation_data.get('recommendation', ''),
                    "result_details": { "anxiety_score": round(avg_anxiety, 2), "avoidance_score": round(avg_avoidance, 2), "condition": condition_str }
                }
            return {"result_level": "无法确定类型", "result_interpretation": "计算结果无法匹配到任何预设类型。"}

        # ==============================================================================
        # 规则 2: 处理 AAS 问卷的 "dominant_subscale" (优势维度总分) - 【已修正】
        # ==============================================================================
        elif scoring_type == 'dominant_subscale':
            # ✅ 关键修正：先创建一个从选项ID到分数的映射字典
            choices_map = {str(c.get('id')): c.get('score', 0) for c in scale_data.get('choices', [])}
            if not choices_map:
                return {"result_level": "配置错误", "result_interpretation": "问卷选项(choices)未定义或缺少ID。"}

            subscale_names = rules.get('subscales', [])
            subscale_scores = {name: 0 for name in subscale_names}
            questions_map = {str(q['order']): q for q in scale_data.get('questions', [])}
            
            # 这里的 `option_id` 现在被正确地理解为选项ID，而不是分数
            for q_order_str, option_id in request_answers.items():
                question = questions_map.get(q_order_str)
                if not question: continue

                # ✅ 关键修正：通过选项ID从映射中查找正确的分数
                score = choices_map.get(option_id)
                if score is None: 
                    continue # 如果ID无效，则跳过

                subscale = question.get('subscale')
                if subscale in subscale_scores:
                    subscale_scores[subscale] += score
            
            if not any(s > 0 for s in subscale_scores.values()):
                return {"result_level": "无法计算", "result_interpretation": "所有维度得分均为0，请检查提交数据。"}
            
            result_level = max(subscale_scores, key=subscale_scores.get)
            interpretation_data = next((i for i in interpretations if i.get('level') == result_level), {})
            
            return {
                "raw_score": None, "final_score": None, "result_level": result_level,
                "result_interpretation": interpretation_data.get('interpretation', ''),
                "result_recommendation": interpretation_data.get('recommendation', ''),
                "result_details": subscale_scores
            }
            
        # ==============================================================================
        # 规则 3 (默认): 处理 MBTI 和其他简单“投票计数”型问卷
        # ==============================================================================
        else:
            # (这部分代码保持不变)
            questions = scale_data.get('questions', [])
            if questions:
                first_question = questions[0]
                first_option = first_question.get('options', [{}])[0]
                first_target_id = first_option.get('target_personality_id', '')
                if first_target_id.startswith('mbti:'):
                    return self._calculate_mbti_dimensional_result(request_answers, scale_data)

            questions_dict = {str(q['order']): q for q in questions}
            interpretations_obj = scale_data.get('interpretations', {})
            personality_counts = {}
            
            for q_order, option_id in request_answers.items():
                question = questions_dict.get(q_order)
                if not question or not question.get('options'): continue
                
                selected_option = next((opt for opt in question.get('options', []) if opt.get('id') == option_id), None)
                
                if selected_option:
                    target_id = selected_option.get('target_personality_id')
                    if target_id:
                        personality_counts[target_id] = personality_counts.get(target_id, 0) + 1
            
            if not personality_counts:
                return {"result_level": "无法确定", "result_interpretation": "您的答案无法匹配到任何结果，请重试。"}

            final_personality_id = max(personality_counts, key=personality_counts.get)
            final_result = interpretations_obj.get(final_personality_id, {})
            
            return {
                "raw_score": None, "final_score": None,
                "result_level": final_result.get('title'),
                "result_interpretation": final_result.get('description'),
                "result_recommendation": final_result.get('recommendation'),
                "result_details": {
                    "college": final_result.get('college'),
                    "college_motto": final_result.get('college_motto'),
                    "image_url": final_result.get('image_url') 
                }
            }
                
    def _calculate_mbti_dimensional_result(self, request_answers: Dict[str, str], scale_data: Dict) -> Dict:
        """【新增】专门处理 MBTI 维度计分的私有方法"""
        questions = {str(q['order']): q for q in scale_data.get('questions', [])}
        interpretations = scale_data.get('interpretations', {})
        print("使用专属函数了")
        # 1. 初始化维度计分板
        dim_counts = { 'I': 0, 'E': 0, 'S': 0, 'N': 0, 'T': 0, 'F': 0, 'J': 0, 'P': 0 }

        # 2. 遍历答案，解析复合ID并计分
        for q_order, option_id in request_answers.items():
            question = questions.get(q_order)
            if not question: continue
            
            option = next((opt for opt in question.get('options', []) if opt['id'] == option_id), None)
            if not option: continue
                
            target_id = option.get('target_personality_id')
            if target_id and target_id.startswith('mbti:'):
                try:
                    # 解析 "mbti:IE:I"
                    _, dimension, value = target_id.split(':')
                    if value in dim_counts:
                        dim_counts[value] += 1
                except ValueError:
                    # 如果格式不正确，则跳过
                    continue

        # 3. 计算最终人格类型
        result_type = ""
        result_type += 'I' if dim_counts['I'] >= dim_counts['E'] else 'E' # 等于时默认 I
        result_type += 'S' if dim_counts['S'] >= dim_counts['N'] else 'N' # 等于时默认 S
        result_type += 'T' if dim_counts['T'] >= dim_counts['F'] else 'F' # 等于时默认 T
        result_type += 'J' if dim_counts['J'] >= dim_counts['P'] else 'P' # 等于时默认 J
        
        # 4. 查找并返回结果
        final_result = interpretations.get(result_type, {})
        
        return {
            "raw_score": None,
            "final_score": None,
            "result_level": final_result.get('title'), # 复用 title 字段
            "result_interpretation": final_result.get('description'),
            "result_recommendation": final_result.get('recommendation'),
            "result_details": {
                "college": final_result.get('college'),                 # ✅ 添加 college
                "college_motto": final_result.get('college_motto'),     # ✅ 添加 college_motto
                "title": final_result.get('title'),
                "type_code": result_type,
                "dimension_scores": dim_counts,
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