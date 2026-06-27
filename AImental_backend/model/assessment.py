# model/assessment.py

import uuid
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any, Set, Tuple

from peewee import Model, CharField, IntegerField, DateTimeField, TextField, ForeignKeyField, FloatField
from pydantic import BaseModel, Field

from db import assessment_db
from .user import User  # 假设 User 模型可以从 .user 导入

# --- 静态配置 ---
ASSESSMENT_DATA_DIR = "assessment_data/"

ASSESSMENT_DISPLAY_GROUPS = {
    "SDS": ("心理健康", 1, 1),
    "SAS": ("心理健康", 1, 2),
    "BRMS": ("心理健康", 1, 3),
    "SAD": ("心理健康", 1, 4),
    "IAS": ("心理健康", 1, 5),
    "Lonely": ("心理健康", 1, 6),
    "SES": ("自我人格", 2, 1),
    "APS": ("自我人格", 2, 2),
    "CLT": ("自我人格", 2, 3),
    "mbti-93": ("自我人格", 2, 4),
    "AAS": ("亲密关系", 3, 1),
    "ECR": ("亲密关系", 3, 2),
    "LAMT": ("亲密关系", 3, 3),
    "LDCT": ("亲密关系", 3, 4),
    "TPS": ("趣味探索", 4, 1),
    "ICI": ("趣味探索", 4, 2),
    "REAL-MAJOR-V1": ("趣味探索", 4, 3),
    "AGLT": ("趣味探索", 4, 4),
}

BDI_DIMENSIONS = {
    "emotion": {
        "label": "情绪",
        "questions": [1, 2, 10, 11],
        "evidence_labels": {
            1: "难过",
            2: "对未来悲观",
            10: "哭泣变化",
            11: "烦躁",
        },
        "stable": "情绪低落、无望感和烦躁目前不明显。",
        "mild": "情绪有一些波动，可能偶尔低落、悲观或更容易烦躁。",
        "moderate": "低落、悲观或烦躁已经比较明显，可能正在影响日常状态。",
        "high": "情绪困扰较重，低落、无望感或烦躁需要被认真关注。",
    },
    "interest": {
        "label": "兴趣",
        "questions": [4, 12, 20],
        "evidence_labels": {
            4: "日常兴趣下降",
            12: "对人与事的兴趣下降",
            20: "亲密或愉悦感相关兴趣变化",
        },
        "stable": "对日常事物和人际连接的兴趣整体保持得还可以。",
        "mild": "兴趣和连接感有一些下降，适合继续观察。",
        "moderate": "兴趣下降较明显，可能让日常行动和人际连接变得更费力。",
        "high": "兴趣和愉悦感受困扰较重，可能明显削弱生活动力。",
    },
    "body": {
        "label": "身体",
        "questions": [15, 16, 17, 18, 19],
        "evidence_labels": {
            15: "精力变化",
            16: "睡眠变化",
            17: "食欲变化",
            18: "体重变化",
            19: "健康担忧",
        },
        "stable": "精力、睡眠、食欲和身体担忧目前整体较稳定。",
        "mild": "身体状态有些波动，可能和精力、睡眠或食欲有关。",
        "moderate": "身体相关困扰比较明显，可能会放大情绪负担。",
        "high": "身体层面的压力较重，精力、睡眠、食欲或健康担忧需要认真照顾。",
    },
    "cognition": {
        "label": "认知",
        "questions": [3, 5, 6, 7, 8, 13, 14, 21],
        "evidence_labels": {
            3: "失败感",
            5: "罪恶感",
            6: "受惩罚感",
            7: "对自己失望",
            8: "自责",
            13: "决策困难",
            14: "无价值感",
            21: "注意力变化",
        },
        "stable": "自我评价、决策和注意力相关困扰目前不突出。",
        "mild": "自责、自我评价或专注力有一些波动，建议温和观察。",
        "moderate": "自责、自我价值感或决策专注困难比较明显，可能正在影响行动感。",
        "high": "认知层面的压力较重，自责、无价值感或专注困难需要被认真对待。",
    },
}


def get_assessment_display_meta(short_name: str) -> Dict[str, Any]:
    group, group_order, display_order = ASSESSMENT_DISPLAY_GROUPS.get(
        short_name,
        ("其他", 99, 99),
    )
    return {
        "display_group": group,
        "display_group_order": group_order,
        "display_order": display_order,
    }


def _level_from_average(score: float) -> str:
    if score < 0.75:
        return "相对稳定"
    if score < 1.5:
        return "有些波动"
    if score < 2.25:
        return "需要关注"
    return "明显承压"

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

    @property
    def display_group(self) -> str:
        return get_assessment_display_meta(self.short_name)["display_group"]

    @property
    def display_group_order(self) -> int:
        return get_assessment_display_meta(self.short_name)["display_group_order"]

    @property
    def display_order(self) -> int:
        return get_assessment_display_meta(self.short_name)["display_order"]

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
    display_group: Optional[str] = None
    display_group_order: Optional[int] = None
    display_order: Optional[int] = None
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
    ai_analysis: Optional[Dict[str, Any]] = None
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
                    print(f"ℹ️ Scale '{short_name_from_file}' already exists. Refreshing metadata from '{filename}'.")
                    filepath = os.path.join(ASSESSMENT_DATA_DIR, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            scale_info = data.get('scale_info', {})
                            (
                                Scale.update(
                                    name=scale_info.get('name', 'N/A'),
                                    description=scale_info.get('description', ''),
                                    category=scale_info.get('category') or '专业测试',
                                    assessment_type=scale_info.get('assessment_type') or 'scoring',
                                    json_data=json.dumps(data, ensure_ascii=False),
                                    updated_at=datetime.now()
                                )
                                .where(Scale.short_name == short_name_from_file)
                                .execute()
                            )
                    except Exception as e:
                        print(f"❌ Error refreshing file {filename}: {e}")
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
                            category=scale_info.get('category') or '专业测试',
                            assessment_type=scale_info.get('assessment_type') or 'scoring',
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
        display_meta = get_assessment_display_meta(scale.short_name)
        response_data = {
            "id": scale.id,
            "short_name": scale.short_name,
            "name": scale.name,
            "description": scale.description,
            "category": scale.category or "专业测试",
            "assessment_type": scale.assessment_type or "scoring",
            **display_meta,
            # 从解析后的JSON中提取 instructions
            "instructions": scale_info.get('instructions'),
            # 同时也可以把题目和选项带上，供测试页面使用
            "questions": full_data.get('questions', []),
            "choices": full_data.get('choices', [])
        }
        return response_data
    def get_all_scales(self) -> List[Scale]:
        scales = list(Scale.select(
            Scale.id, Scale.short_name, Scale.name, Scale.description, Scale.category, Scale.assessment_type
        ))
        return sorted(scales, key=lambda scale: (scale.display_group_order, scale.display_order, scale.name))
        
    def get_scale_by_id(self, scale_id: str) -> Optional[Scale]:
        return Scale.get_or_none(Scale.id == scale_id)

    def _calculate_scoring_result(self, request_answers: Dict[str, Any], scale_data: Dict) -> Dict:
        """【修改版】处理打分测试的计分逻辑，支持反向计分和谎言量表"""
        rules = scale_data.get('scale_info', {}).get('scoring_rules', {})
        interpretations = scale_data.get('interpretations', [])
        questions = scale_data.get('questions', [])
        common_choice_scores = self._extract_choice_scores(scale_data.get('choices', []))
        default_score_bounds = self._get_score_bounds(common_choice_scores)
        question_score_bounds = self._build_question_score_bounds(questions, default_score_bounds)
        
        # 1. 获取计分规则
        # 兼容 "reverse_scoring_items" 和 "reverse_scored_items" 两种可能的拼写
        reverse_items = set(rules.get('reverse_scoring_items', []) + rules.get('reverse_scored_items', []))
        reverse_items.update(self._get_question_level_reverse_items(questions))
        
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
                min_score, max_score = question_score_bounds.get(q_order, default_score_bounds)
                raw_score += (min_score + max_score - score)
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

    def _extract_choice_scores(self, choices: List[Dict[str, Any]]) -> List[float]:
        scores = []
        for choice in choices or []:
            try:
                scores.append(float(choice.get("score")))
            except (TypeError, ValueError):
                continue
        return scores

    def _get_score_bounds(self, scores: List[float]) -> Tuple[float, float]:
        if not scores:
            return (0, 1)
        return (min(scores), max(scores))

    def _build_question_score_bounds(
        self,
        questions: List[Dict[str, Any]],
        default_bounds: Tuple[float, float],
    ) -> Dict[int, Tuple[float, float]]:
        bounds = {}
        for question in questions or []:
            try:
                order = int(question.get("order"))
            except (TypeError, ValueError):
                continue

            question_choices = question.get("choices") or question.get("options") or []
            question_scores = self._extract_choice_scores(question_choices)
            bounds[order] = self._get_score_bounds(question_scores) if question_scores else default_bounds
        return bounds

    def _get_question_level_reverse_items(self, questions: List[Dict[str, Any]]) -> Set[int]:
        reverse_items = set()
        for question in questions or []:
            if not (question.get("is_reverse_scored") or question.get("reverse_scored")):
                continue
            try:
                reverse_items.add(int(question.get("order")))
            except (TypeError, ValueError):
                continue
        return reverse_items

    def _scale_uses_reverse_scoring(self, scale_data: Dict[str, Any]) -> bool:
        rules = scale_data.get('scale_info', {}).get('scoring_rules', {})
        if rules.get('reverse_scoring_items') or rules.get('reverse_scored_items'):
            return True
        return bool(self._get_question_level_reverse_items(scale_data.get('questions', [])))

    def ensure_scoring_result_for_record(self, record: UserAssessment) -> None:
        """Refresh historical scoring records that may have been saved before scoring fixes."""
        if not record or not record.scale or record.scale.assessment_type != "scoring":
            return

        try:
            scale_data = json.loads(record.scale.json_data)
        except json.JSONDecodeError:
            return

        should_refresh = record.result_level is None or self._scale_uses_reverse_scoring(scale_data)
        if not should_refresh:
            return

        try:
            answers = json.loads(record.answers) if record.answers else {}
        except json.JSONDecodeError:
            return

        result_data = self._calculate_scoring_result(answers, scale_data)
        result_data = self._attach_ai_analysis(record.scale.short_name, answers, result_data)

        has_changes = (
            record.raw_score != result_data.get("raw_score")
            or record.final_score != result_data.get("final_score")
            or record.result_level != result_data.get("result_level")
            or record.result_interpretation != result_data.get("result_interpretation")
            or record.result_recommendation != result_data.get("result_recommendation")
        )

        next_details = result_data.get("result_details")
        next_details_json = json.dumps(next_details, ensure_ascii=False) if next_details else None
        if record.result_details != next_details_json:
            has_changes = True

        if not has_changes:
            return

        record.raw_score = result_data.get("raw_score")
        record.final_score = result_data.get("final_score")
        record.result_level = result_data.get("result_level")
        record.result_interpretation = result_data.get("result_interpretation")
        record.result_recommendation = result_data.get("result_recommendation")
        record.result_details = next_details_json
        record.save()

    def _build_bdi_ai_analysis(
        self,
        request_answers: Dict[str, Any],
        result_level: Optional[str],
        final_score: Optional[float],
    ) -> Dict[str, Any]:
        numeric_answers: Dict[int, float] = {}
        for q_order_str, score_str in request_answers.items():
            try:
                numeric_answers[int(q_order_str)] = float(score_str)
            except (ValueError, TypeError):
                continue

        dimensions = []
        elevated_labels = []
        for key, config in BDI_DIMENSIONS.items():
            question_ids = config["questions"]
            scores = [numeric_answers.get(question_id, 0) for question_id in question_ids]
            average_score = sum(scores) / len(question_ids) if question_ids else 0
            level = _level_from_average(average_score)

            if level == "相对稳定":
                summary = config["stable"]
            elif level == "有些波动":
                summary = config["mild"]
            elif level == "需要关注":
                summary = config["moderate"]
            else:
                summary = config["high"]

            evidence = [
                config["evidence_labels"][question_id]
                for question_id in question_ids
                if numeric_answers.get(question_id, 0) > 0
            ][:4]

            if level in {"需要关注", "明显承压"}:
                elevated_labels.append(config["label"])

            dimensions.append({
                "key": key,
                "label": config["label"],
                "level": level,
                "score": round(average_score, 2),
                "summary": summary,
                "evidence": evidence,
            })

        q9_score = numeric_answers.get(9, 0)
        risk_dimension_level = _level_from_average(q9_score)
        if q9_score >= 2:
            risk_summary = "你在自伤或自杀念头题项上选择了较高分值，这需要被立即认真对待。"
        elif q9_score == 1:
            risk_summary = "你提到过相关念头，虽然不一定代表会付诸行动，但很值得尽快获得支持。"
        else:
            risk_summary = "当前未从 Q9 看到明显自伤或自杀念头信号。"

        dimensions.append({
            "key": "risk",
            "label": "风险",
            "level": risk_dimension_level,
            "score": q9_score,
            "summary": risk_summary,
            "evidence": ["自伤或自杀念头"] if q9_score > 0 else [],
        })

        if q9_score >= 2:
            professional_support = {
                "recommended": True,
                "urgency": "urgent",
                "text": "建议尽快联系身边可信任的人、心理咨询师或精神科医生；如果你担心自己可能会伤害自己，请立即联系当地紧急支持资源或急救服务。",
            }
            risk_note = {
                "triggered": True,
                "level": "high",
                "text": "这份结果提示需要优先保障安全。请不要独自承受，尽快告诉一个可信任的人，并寻求专业或紧急支持。",
            }
        elif q9_score == 1:
            professional_support = {
                "recommended": True,
                "urgency": "suggested",
                "text": "建议尽快找可信任的人聊聊，也建议考虑联系心理咨询师或精神科医生获得支持。",
            }
            risk_note = {
                "triggered": True,
                "level": "medium",
                "text": "你提到过相关念头，这已经值得被认真照顾。请优先让自己处在有人支持、相对安全的环境中。",
            }
        else:
            professional_support = {
                "recommended": bool(final_score is not None and final_score >= 20),
                "urgency": "suggested" if final_score is not None and final_score >= 20 else "optional",
                "text": "如果这种状态持续两周以上，或明显影响学习、工作、人际和生活，建议联系心理咨询师或精神科医生。",
            }
            risk_note = {
                "triggered": False,
                "level": "none",
                "text": "",
            }

        if q9_score >= 2:
            state_summary = f"你的结果为{result_level or '当前状态'}，并出现需要优先关注的安全风险信号，请先确保身边有人支持。"
        elif q9_score == 1:
            state_summary = f"你的结果为{result_level or '当前状态'}，同时出现过相关风险念头，建议尽快找可信任的人或专业人士聊聊。"
        elif elevated_labels:
            state_summary = f"你的结果为{result_level or '当前状态'}，主要需要关注{ '、'.join(elevated_labels[:3]) }相关变化。"
        else:
            state_summary = f"你的结果为{result_level or '当前状态'}，目前各维度整体较平稳，仍可以继续观察近期变化。"

        possible_causes = [
            "近期可能存在持续压力、恢复不足或生活节奏被打乱的情况。",
            "当情绪、身体和自我评价同时承压时，低落感可能会被进一步放大。",
        ]
        if any(item["key"] == "body" and item["level"] in {"需要关注", "明显承压"} for item in dimensions):
            possible_causes.append("睡眠、精力、食欲或身体担忧的变化，可能正在影响你的情绪恢复。")
        if any(item["key"] == "interest" and item["level"] in {"需要关注", "明显承压"} for item in dimensions):
            possible_causes.append("兴趣下降和与他人连接减少，可能让你更难从日常生活中获得支持感。")

        small_actions = [
            "今天先完成一件 10 分钟内能做完的小事，给自己一个可完成的起点。",
            "连续 3 天记录心情、睡眠、精力和触发事件，观察状态是否有规律。",
            "找一个可信任的人说一句真实近况，不需要一次讲完所有事情。",
        ]
        if q9_score > 0:
            small_actions.insert(0, "先把自己移动到更安全、有人陪伴或更容易求助的环境里。")

        return {
            "state_summary": state_summary,
            "dimensions": dimensions,
            "possible_causes": possible_causes,
            "small_actions": small_actions,
            "professional_support": professional_support,
            "emotion_recording": {
                "recommended": True,
                "focus": ["心情", "睡眠", "精力", "触发事件"],
                "text": "建议接下来持续记录情绪，重点观察低落、睡眠、精力和触发事件的变化。",
            },
            "risk_note": risk_note,
        }

    def _attach_ai_analysis(
        self,
        scale_short_name: str,
        request_answers: Dict[str, Any],
        result_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        if scale_short_name != "SDS":
            return result_data

        ai_analysis = self._build_bdi_ai_analysis(
            request_answers=request_answers,
            result_level=result_data.get("result_level"),
            final_score=result_data.get("final_score"),
        )
        result_details = result_data.get("result_details")
        if not isinstance(result_details, dict):
            result_details = {}
        result_details["ai_analysis"] = ai_analysis
        result_data["result_details"] = result_details
        result_data["ai_analysis"] = ai_analysis
        return result_data


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

        result_data = self._attach_ai_analysis(scale.short_name, request_data.answers, result_data)
        
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
        records = list(UserAssessment.select().where(UserAssessment.user == user_id).order_by(UserAssessment.completed_at.desc()))
        for record in records:
            self.ensure_scoring_result_for_record(record)
        return records

    def get_assessment_by_id(self, record_id: str) -> Optional[UserAssessment]:
        """根据记录ID获取单条测评结果"""
        record = UserAssessment.get_or_none(UserAssessment.id == record_id)
        self.ensure_scoring_result_for_record(record)
        return record

    def ensure_ai_analysis_for_record(self, record: UserAssessment) -> Optional[Dict[str, Any]]:
        """为历史 SDS/BDI-II 记录补齐 AI 分析，并返回分析对象。"""
        if not record or not record.scale or record.scale.short_name != "SDS":
            return None

        try:
            answers = json.loads(record.answers) if record.answers else {}
        except json.JSONDecodeError:
            answers = {}

        try:
            result_details = json.loads(record.result_details) if record.result_details else {}
        except json.JSONDecodeError:
            result_details = {}

        if not isinstance(result_details, dict):
            result_details = {}

        existing_analysis = result_details.get("ai_analysis")
        if isinstance(existing_analysis, dict):
            return existing_analysis

        ai_analysis = self._build_bdi_ai_analysis(
            request_answers=answers,
            result_level=record.result_level,
            final_score=record.final_score,
        )
        result_details["ai_analysis"] = ai_analysis
        record.result_details = json.dumps(result_details, ensure_ascii=False)
        record.save()
        return ai_analysis

    def delete_user_assessment(self, user_id: str, record_id: str) -> bool:
        """删除一条属于特定用户的测评记录"""
        query = UserAssessment.delete().where(
            (UserAssessment.id == record_id) & (UserAssessment.user == user_id)
        )
        deleted_rows = query.execute()
        return deleted_rows > 0

# --- 实例化数据表访问对象 ---
assessment_tables = AssessmentTables(assessment_db)
