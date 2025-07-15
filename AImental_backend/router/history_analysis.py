# router/history_analysis.py

import json
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel, Field

# 1. 导入项目模块
from .auth import get_current_user_id
# ✅ 【修改】导入所有需要的模型和数据访问对象
from model.history_analysis import (
    history_analysis_tables,
    HistoryAnalysisCreateRequest
)
from LLM import generate_assessment_synthesis_report


# ✅ 【修改】将Pydantic模型定义移到Router文件顶部，保持一致性
class SynthesisReportResponse(BaseModel):
    overall_assessment: str = Field(..., description="综合评估")
    trend_analysis: str = Field(..., description="趋势分析")
    recommendations: str = Field(..., description="个性化建议")
    # ✅ 【新增字段】告诉前端这次结果是来自缓存还是新生成的
    from_cache: bool = Field(default=False, description="结果是否来自缓存")


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
    current_user_id: str = Depends(get_current_user_id)
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

    # 3. 【缓存未命中】调用LLM生成新报告
    print(f"❌ Cache miss for signature: {signature[:10]}... Generating new report.")
    report_dict = generate_assessment_synthesis_report(
        user_id=current_user_id,
        history_ids=request.history_ids
    )

    if not report_dict:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate AI analysis report. Please try again later."
        )

    # 4. 【关键步骤】将新生成的报告存入数据库
    history_analysis_tables.save_new_analysis(
        user_id=current_user_id,
        history_ids=request.history_ids,
        signature=signature,
        report_content=report_dict
    )

    # 5. 返回新生成的报告
    return SynthesisReportResponse(
        overall_assessment=report_dict.get('comprehensive_evaluation', 'AI未能生成评估内容。'),
        trend_analysis=report_dict.get('trend_analysis', 'AI未能生成趋势分析。'),
        recommendations=report_dict.get('personalized_recommendations', 'AI未能生成建议。'),
        from_cache=False # 告知前端这是新数据
    )

# ... (旧的 /、/{analysis_id}、DELETE 等路由可以保留，如果你还需要通过ID来管理单个报告的话) ...