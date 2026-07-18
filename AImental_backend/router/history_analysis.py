# router/history_analysis.py

import json
from datetime import datetime
from fastapi import APIRouter, Depends, Header, HTTPException, status
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# 1. 导入项目模块
from .auth import get_current_user_id
# ✅ 【修改】导入所有需要的模型和数据访问对象
from model.history_analysis import (
    history_analysis_tables,
    HistoryAnalysisCreateRequest
)
from LLM import generate_assessment_synthesis_report
from vip_access import (
    confirm_reservation,
    release_reservation,
    reserve_feature_or_http,
)
from vip_catalog import FEATURE_ASSESSMENT_ANALYSIS


# ✅ 【修改】将Pydantic模型定义移到Router文件顶部，保持一致性
class SynthesisReportResponse(BaseModel):
    overall_assessment: str = Field(..., description="综合评估")
    trend_analysis: str = Field(..., description="趋势分析")
    recommendations: str = Field(..., description="个性化建议")
    # ✅ 【新增字段】告诉前端这次结果是来自缓存还是新生成的
    from_cache: bool = Field(default=False, description="结果是否来自缓存")


class HistoryAnalysisListItem(BaseModel):
    id: str
    history_count: int
    overall_assessment: str
    created_at: datetime


class HistoryAnalysisDetailResponse(BaseModel):
    id: str
    analyzed_history_ids: List[str]
    overall_assessment: str
    trend_analysis: str
    recommendations: str
    created_at: datetime


def _parse_history_analysis(record) -> Dict[str, Any]:
    try:
        history_ids = json.loads(record.analyzed_history_ids)
    except (TypeError, json.JSONDecodeError):
        history_ids = []
    try:
        content = json.loads(record.content)
    except (TypeError, json.JSONDecodeError):
        content = {}
    if not isinstance(history_ids, list):
        history_ids = []
    if not isinstance(content, dict):
        content = {}
    return {
        "id": record.id,
        "analyzed_history_ids": [str(item) for item in history_ids],
        "overall_assessment": content.get("comprehensive_evaluation", ""),
        "trend_analysis": content.get("trend_analysis", ""),
        "recommendations": content.get("personalized_recommendations", ""),
        "created_at": record.created_at,
    }


# ---------------------------------------------------
# Router 设置
# ---------------------------------------------------
router = APIRouter(
    prefix="/history-analysis",
    tags=["History Analysis - 历史记录分析"],
)

# ---------------------------------------------------
# API 端点
# ---------------------------------------------------

# ✅ 【核心修改】重写整个 synthesize_assessment_report 函数
@router.post(
    "/synthesize",
    response_model=SynthesisReportResponse,
    summary="获取或创建历史记录综合分析报告(带缓存)"
)
def synthesize_assessment_report(
    request: HistoryAnalysisCreateRequest,
    current_user_id: str = Depends(get_current_user_id),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
):
    """
    接收历史记录ID列表，优先从数据库查找已有的分析。
    如果找不到，则调用LLM实时分析，并将新结果存入数据库。
    """
    if not request.history_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="History IDs cannot be empty.")

    # 1. 创建唯一签名
    signature = history_analysis_tables._create_signature(request.history_ids)

    # 2. 检查缓存（数据库）
    cached_report = history_analysis_tables.get_analysis_by_signature(current_user_id, signature)

    if cached_report:
        # 2.1 【缓存命中】直接返回数据库中的结果
        print(f"✅ Cache hit for signature: {signature[:10]}...")
        report_content = json.loads(cached_report.content)
        return SynthesisReportResponse(
            overall_assessment=report_content.get('comprehensive_evaluation', ''),
            trend_analysis=report_content.get('trend_analysis', ''),
            recommendations=report_content.get('personalized_recommendations', ''),
            from_cache=True # 告知前端这是缓存数据
        )

    reservation = reserve_feature_or_http(
        user_id=current_user_id,
        feature=FEATURE_ASSESSMENT_ANALYSIS,
        supplied_request_id=x_request_id or signature,
    )
    try:
        print(f"❌ Cache miss for signature: {signature[:10]}... Generating new report.")
        report_dict = generate_assessment_synthesis_report(
            user_id=current_user_id,
            history_ids=request.history_ids
        )

        if not report_dict:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "model_generation_failed",
                    "message": "AI 测评分析生成失败，请稍后重试。",
                },
            )

        history_analysis_tables.save_new_analysis(
            user_id=current_user_id,
            history_ids=request.history_ids,
            signature=signature,
            report_content=report_dict
        )
        confirm_reservation(reservation)
        return SynthesisReportResponse(
            overall_assessment=report_dict.get('comprehensive_evaluation', 'AI未能生成评估内容。'),
            trend_analysis=report_dict.get('trend_analysis', 'AI未能生成趋势分析。'),
            recommendations=report_dict.get('personalized_recommendations', 'AI未能生成建议。'),
            from_cache=False
        )
    except Exception:
        release_reservation(reservation)
        raise


@router.get(
    "/",
    response_model=List[HistoryAnalysisListItem],
    summary="获取当前用户的历史测评综合分析列表",
)
def list_history_analyses(
    current_user_id: str = Depends(get_current_user_id),
):
    records = history_analysis_tables.get_analyses_by_user(current_user_id)
    result = []
    for record in records:
        payload = _parse_history_analysis(record)
        result.append(
            {
                "id": payload["id"],
                "history_count": len(payload["analyzed_history_ids"]),
                "overall_assessment": payload["overall_assessment"],
                "created_at": payload["created_at"],
            }
        )
    return result


@router.get(
    "/{analysis_id}",
    response_model=HistoryAnalysisDetailResponse,
    summary="获取单条历史测评综合分析",
)
def get_history_analysis_detail(
    analysis_id: str,
    current_user_id: str = Depends(get_current_user_id),
):
    record = history_analysis_tables.get_analysis_by_id(analysis_id)
    if not record or record.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="History analysis not found.",
        )
    return _parse_history_analysis(record)
