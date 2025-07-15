# model/history_analysis.py

import uuid
import json
import hashlib # ✅ 1. 【新增导入】导入哈希库
from datetime import datetime
from typing import Optional, List, Dict, Any

from peewee import Model, CharField, DateTimeField, TextField, ForeignKeyField
from pydantic import BaseModel, Field

from db import assessment_db 
from .user import User

# ---------------------------------------------------
# 1. Peewee 数据模型 (数据库表结构)
# ---------------------------------------------------

class HistoryAnalysis(Model):
    """
    用户历史记录AI分析表。
    """
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    user = ForeignKeyField(User, backref='history_analyses', field='id', on_delete='CASCADE')
    
    # ✅ 2. 【新增字段】用于存储ID列表的唯一签名，这是实现缓存的关键
    analysis_signature = CharField(max_length=64, unique=True, index=True, help_text="SHA256 hash of sorted history IDs")
    
    analyzed_history_ids = TextField(help_text="被分析的用户测评历史记录ID列表的JSON字符串")
    content = TextField(help_text="AI生成的分析报告内容的JSON字符串")
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        database = assessment_db
        table_name = 'history_analyses'

# ... (Pydantic 模型部分保持不变) ...
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
    
    class Config:
        from_attributes = True

# ---------------------------------------------------
# 3. 数据表访问类 (封装所有数据库操作)
# ---------------------------------------------------

class HistoryAnalysisTables:
    """封装所有与历史记录分析相关的数据库操作"""
    def __init__(self, db_connection):
        self.db = db_connection
        # 确保新字段的表被创建
        self.db.create_tables([HistoryAnalysis])

    # ✅ 3. 【新增辅助函数】用于创建唯一签名
    def _create_signature(self, history_ids: List[str]) -> str:
        """对排序后的ID列表进行哈希，生成唯一签名"""
        # 先排序，确保 ['id1', 'id2'] 和 ['id2', 'id1'] 的签名一致
        sorted_ids = sorted(history_ids)
        # 将列表转换为一个紧凑的JSON字符串
        ids_string = json.dumps(sorted_ids, separators=(',', ':'))
        # 计算SHA256哈希值
        signature = hashlib.sha256(ids_string.encode('utf-8')).hexdigest()
        return signature

    # ✅ 4. 【新增查询函数】根据签名查找已有的分析报告
    def get_analysis_by_signature(self, user_id: str, signature: str) -> Optional[HistoryAnalysis]:
        """根据签名查找记录"""
        return HistoryAnalysis.get_or_none(
            (HistoryAnalysis.analysis_signature == signature) &
            (HistoryAnalysis.user == user_id)
        )

    # ✅ 5. 【新增保存函数】将新生成的报告存入数据库
    def save_new_analysis(
        self,
        user_id: str,
        history_ids: List[str],
        signature: str,
        report_content: Dict[str, str]
    ) -> HistoryAnalysis:
        """将新的分析结果保存到数据库"""
        record = HistoryAnalysis.create(
            user=user_id,
            analysis_signature=signature,
            analyzed_history_ids=json.dumps(sorted(history_ids)), # 存排序后的ID
            content=json.dumps(report_content, ensure_ascii=False)
        )
        return record

    # ... (旧的 get_analysis_by_id, get_analyses_by_user, delete_history_analysis 等函数可以保留，无需修改) ...
    def get_analysis_by_id(self, analysis_id: str) -> Optional[HistoryAnalysis]:
        """根据主键ID获取单个分析报告"""
        return HistoryAnalysis.get_or_none(HistoryAnalysis.id == analysis_id)

    def get_analyses_by_user(self, user_id: str) -> List[HistoryAnalysis]:
        """获取一个用户的所有历史分析报告，按时间倒序"""
        return list(
            HistoryAnalysis.select()
            .where(HistoryAnalysis.user == user_id)
            .order_by(HistoryAnalysis.created_at.desc())
        )
    
    def delete_history_analysis(self, user_id: str, analysis_id: str) -> bool:
        """删除一条属于特定用户的分析报告"""
        query = HistoryAnalysis.delete().where(
            (HistoryAnalysis.id == analysis_id) & (HistoryAnalysis.user == user_id)
        )
        deleted_rows = query.execute()
        return deleted_rows > 0

# --- 实例化数据表访问对象 ---
history_analysis_tables = HistoryAnalysisTables(assessment_db)