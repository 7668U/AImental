# model/history_analysis.py

import uuid
import json
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any

from peewee import Model, CharField, DateTimeField, TextField, ForeignKeyField
from pydantic import BaseModel, Field

from db import assessment_db
from .user import User

# --- 【新增导入】导入需要用到的数据查询模块 ---
from .status import checkin_table
from .assessment import assessment_tables, personality_test_manager
# --------------------------------------------

# ---------------------------------------------------
# 1. Peewee 数据模型 (数据库表结构)
# ---------------------------------------------------

class HistoryAnalysis(Model):
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    user = ForeignKeyField(User, backref='history_analyses', field='id', on_delete='CASCADE')
    analysis_signature = CharField(max_length=64, unique=True, index=True)
    analyzed_history_ids = TextField()
    content = TextField()
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        database = assessment_db
        table_name = 'history_analyses'

# ---------------------------------------------------
# 2. Pydantic 模型
# ---------------------------------------------------

class HistoryAnalysisContentResponse(BaseModel):
    comprehensive_evaluation: str
    trend_analysis: str
    personalized_recommendations: str

class HistoryAnalysisCreateRequest(BaseModel):
    history_ids: List[str] = Field(..., min_length=1)

class HistoryAnalysisResponse(BaseModel):
    id: str
    user_id: str
    analyzed_history_ids: List[str]
    content: HistoryAnalysisContentResponse
    created_at: datetime
    class Config: from_attributes = True

# ---------------------------------------------------
# 3. 数据表访问类
# ---------------------------------------------------

class HistoryAnalysisTables:
    def __init__(self, db_connection):
        self.db = db_connection
        self.db.create_tables([HistoryAnalysis])

    def _create_signature(self, history_ids: List[str]) -> str:
        sorted_ids = sorted(history_ids)
        ids_string = json.dumps(sorted_ids, separators=(',', ':'))
        return hashlib.sha256(ids_string.encode('utf-8')).hexdigest()

    def get_analysis_by_signature(self, user_id: str, signature: str) -> Optional[HistoryAnalysis]:
        return HistoryAnalysis.get_or_none(
            (HistoryAnalysis.analysis_signature == signature) &
            (HistoryAnalysis.user == user_id)
        )

    def save_new_analysis(
        self, user_id: str, history_ids: List[str],
        signature: str, report_content: Dict[str, str]
    ) -> HistoryAnalysis:
        return HistoryAnalysis.create(
            user=user_id,
            analysis_signature=signature,
            analyzed_history_ids=json.dumps(sorted(history_ids)),
            content=json.dumps(report_content, ensure_ascii=False)
        )

    def get_analysis_by_id(self, analysis_id: str) -> Optional[HistoryAnalysis]:
        return HistoryAnalysis.get_or_none(HistoryAnalysis.id == analysis_id)

    def get_analyses_by_user(self, user_id: str) -> List[HistoryAnalysis]:
        return list(
            HistoryAnalysis.select()
            .where(HistoryAnalysis.user == user_id)
            .order_by(HistoryAnalysis.created_at.desc())
        )
    
    def delete_history_analysis(self, user_id: str, analysis_id: str) -> bool:
        query = HistoryAnalysis.delete().where(
            (HistoryAnalysis.id == analysis_id) & (HistoryAnalysis.user == user_id)
        )
        return query.execute() > 0

history_analysis_tables = HistoryAnalysisTables(assessment_db)

# ---------------------------------------------------
# 4. 【新增】为Prompt整合用户数据的工具函数
# ---------------------------------------------------

def format_user_data_for_prompt(user_id: str) -> str:
    """
    获取并格式化一个用户的所有相关数据，用于构建Prompt。
    """
    summary_parts = []

    # 1. 获取最近7天的心情记录
    try:
        recent_checkins = checkin_table.get_recent_checkins(user_id, days=7)
        if recent_checkins:
            mood_summary = "- 最近7天心情记录：\n"
            for checkin in recent_checkins:
                checkin_date = datetime.fromtimestamp(checkin.timestamp).strftime('%Y-%m-%d')
                mood_summary += f"  - {checkin_date}: 心情为“{checkin.mood}”。"
                if checkin.text_content:
                    mood_summary += f" 当天ta记录道：“{checkin.text_content[:50]}...”。\n"
                else:
                    mood_summary += "\n"
            summary_parts.append(mood_summary)
    except Exception as e:
        print(f"[Prompt Data] Error fetching mood data: {e}")

    # 2. 获取所有心理测评结果
    try:
        assessments = assessment_tables.get_assessments_by_user(user_id)
        if assessments:
            assessment_summary = "- 过往心理测评结果摘要：\n"
            for assessment in assessments:
                # 使用 hasattr 检查是否存在 scale_name，因为它是通过 join 别名添加的
                scale_name = getattr(assessment, 'scale_name', '未知量表')
                assessment_summary += f"  - {assessment.completed_at.strftime('%Y-%m-%d')} 完成了“{scale_name}”测评，"
                assessment_summary += f"结果为“{assessment.result_level}”，得分为 {assessment.final_score}分。\n"
            summary_parts.append(assessment_summary)
    except Exception as e:
        print(f"[Prompt Data] Error fetching assessment data: {e}")

    # 3. 获取所有人格测试结果
    try:
        personality_tests = personality_test_manager.get_personality_tests_by_user(user_id)
        if personality_tests:
            personality_summary = "- 过往人格/趣味测试结果摘要：\n"
            for test in personality_tests:
                test_name = getattr(test, 'test_name', '未知测试')
                personality_summary += f"  - {test.completed_at.strftime('%Y-%m-%d')} 完成了“{test_name}”，"
                personality_summary += f"结果为“{test.result_major}”。\n"
            summary_parts.append(personality_summary)
    except Exception as e:
        print(f"[Prompt Data] Error fetching personality test data: {e}")

    # 4. 组合所有信息
    if not summary_parts:
        return "该用户暂无更多信息。"

    # 使用新的、更明确的引导语
    full_summary = (
        "这是由用户授权提供给你的，关于ta最近一段时间的个人信息。"
        "请你仔细阅读并基于这些信息来感受和理解用户当前的情绪状态与潜在问题，从而更好地进行对话，帮助用户解决问题。建议你适当地基于这些信息主动发问。\n\n"
        "--- 用户背景信息如下 ---"
        + "\n".join(summary_parts)
    )
    return full_summary
