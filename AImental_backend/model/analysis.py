# models/analysis.py

import uuid
import time
import json
from typing import List, Dict, Any, Optional # 引入 Optional

from peewee import Model, CharField, TextField, IntegerField, CompositeKey
from pydantic import BaseModel, Field
from security.data_encryption import EncryptedTextField

# 导入数据库连接
try:
    from db import status_db
except ImportError:
    import peewee as pw
    status_db = pw.SqliteDatabase('db/daily_status.db')

# ===================================================
# 1. Pydantic 数据模型 (为所有报告类型定义)
# ===================================================

# --- 模块一：核心情绪分析 (无改动) ---
class MoodDistributionItem(BaseModel):
    name: str
    value: int
    percent: float

class MoodAnalysisContent(BaseModel):
    total_checkins: int
    recorded_days: Optional[int] = None
    dominant_mood: str
    mood_distribution: List[MoodDistributionItem]
    dominant_mood_family: Optional[str] = None
    mood_family_distribution: List[MoodDistributionItem] = Field(default_factory=list)
    valence_distribution: List[MoodDistributionItem] = Field(default_factory=list)
    energy_distribution: List[MoodDistributionItem] = Field(default_factory=list)
    interpretation: str

# --- 模块二：生活状态关联分析 (无改动) ---
class TagMoodSeriesItem(BaseModel):
    name: str
    data: List[int]

class TagMoodChartData(BaseModel):
    categories: List[str]
    series: List[TagMoodSeriesItem]

class TagMoodAnalysisContent(BaseModel):
    chart_data: TagMoodChartData
    status_distribution: List[MoodDistributionItem] = Field(default_factory=list)
    status_family_distribution: List[MoodDistributionItem] = Field(default_factory=list)
    top_correlations: List[Dict[str, Any]] = Field(default_factory=list)
    interpretation: str

# --- 模块三：文字内容分析 (词云) ---
class WordCloudItem(BaseModel):
    name: str
    value: int

class WordCloudAnalysisContent(BaseModel):
    # 【重要修改】增加一个 image_url 字段
    image_url: Optional[str] = None # 图片的访问路径
    word_list: List[WordCloudItem]
    interpretation: str

# --- 模块四：情绪色彩分析 (无改动) ---
class ColorPaletteItem(BaseModel):
    hex: str
    name: str
    percent: float

class ColorPaletteAnalysisContent(BaseModel):
    color_palette: List[ColorPaletteItem]
    dominant_color_group: Optional[str] = None
    color_group_distribution: List[MoodDistributionItem] = Field(default_factory=list)
    color_tone_distribution: List[MoodDistributionItem] = Field(default_factory=list)
    interpretation: str

# ===================================================
# 2. Peewee 数据库模型 (无改动)
# ===================================================

class Analysis(Model):
    """用于缓存分析结果的 Peewee 模型。"""
    user_id = CharField(max_length=36, index=True)
    period_key = CharField(max_length=50, index=True)
    analysis_type = CharField(max_length=50)
    content = EncryptedTextField(purpose="analyses.content")
    created_at = IntegerField(default=lambda: int(time.time()))
    updated_at = IntegerField(default=lambda: int(time.time()))

    class Meta:
        database = status_db
        table_name = 'analyses'
        primary_key = CompositeKey('user_id', 'period_key', 'analysis_type')

# ===================================================
# 3. 数据表访问类 (无改动)
# ===================================================

class AnalysisTable:
    def __init__(self, db_connection):
        self.db = db_connection
        self.db.create_tables([Analysis], safe=True)
        # self.db.drop_tables([Analysis], safe=True)  # 清理旧数据
    def get_analysis(self, user_id: str, period_key: str, analysis_type: str) -> Analysis | None:
        """使用复合主键获取缓存的分析结果。"""
        return Analysis.get_or_none(
            (Analysis.user_id == user_id) &
            (Analysis.period_key == period_key) &
            (Analysis.analysis_type == analysis_type)
        )

    def list_ai_report_history(self, user_id: str, limit: int = 100) -> List[Analysis]:
        return list(
            Analysis.select()
            .where(
                (Analysis.user_id == user_id) &
                (
                    (Analysis.analysis_type.contains("_ai_report_")) |
                    (Analysis.analysis_type.startswith("ai_report_"))
                )
            )
            .order_by(Analysis.updated_at.desc())
            .limit(limit)
        )

    def save_analysis(self, user_id: str, period_key: str, analysis_type: str, content_model: BaseModel) -> Analysis:
        """
        保存或更新分析结果。
        接收一个 Pydantic 模型，将其序列化为 JSON 字符串后存入数据库。
        """
        content_json = content_model.model_dump_json()
        defaults = {
            'content': content_json,
            'updated_at': int(time.time())
        }
        query = Analysis.insert(
            user_id=user_id,
            period_key=period_key,
            analysis_type=analysis_type,
            content=content_json,
            created_at=int(time.time())
        ).on_conflict(
            conflict_target=[Analysis.user_id, Analysis.period_key, Analysis.analysis_type],
            update=defaults
        )
        query.execute()
        return self.get_analysis(user_id, period_key, analysis_type)

# ===================================================
# 4. 实例化对象
# ===================================================
analysis_table = AnalysisTable(status_db)
