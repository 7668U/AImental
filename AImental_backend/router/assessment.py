# router/assessment.py (图片URL拼接最终版)

import json
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import Header
from typing import List, Dict, Any, Optional

# 1. 导入项目模块
try:
    from .auth import get_current_user_id
except (ImportError, ModuleNotFoundError):
    from auth import get_current_user_id

from model.assessment import (
    assessment_tables,
    ScaleInfoResponse,
    get_assessment_display_meta,
    # ScaleDetailResponse,
    SubmitAnswersRequest,
    UserAssessmentResponse
)
from assessment_ai import generate_assessment_ai_analysis, is_health_assessment
from vip_access import confirm_reservation, release_reservation, reserve_feature_or_http
from vip_catalog import FEATURE_ASSESSMENT_ANALYSIS

SERVER_BASE_URL = os.getenv(
    "PUBLIC_BASE_URL",
    "https://api.feelyourself.cn",
).rstrip("/")

# ---------------------------------------------------
# Router 设置
# ---------------------------------------------------
router = APIRouter(
    prefix="/assessments",
    tags=["Assessments - 心理测评"],
)

# ---------------------------------------------------
# API 端点
# ---------------------------------------------------
# --- 在这里添加新的 Pydantic 模型 ---
class FormattedScaleResponse(ScaleInfoResponse):
    """用于单个量表详情页的、格式化后的响应模型"""
    questions: List[Dict[str, Any]]
    choices: List[Dict[str, Any]]


def _build_scale_info(scale_obj, include_json_data: bool = False) -> Optional[Dict[str, Any]]:
    if not scale_obj:
        return None

    scale_info = {
        "id": scale_obj.id,
        "short_name": scale_obj.short_name,
        "name": scale_obj.name,
        "description": scale_obj.description,
        "category": scale_obj.category or "专业测试",
        "assessment_type": scale_obj.assessment_type or "scoring",
        **get_assessment_display_meta(scale_obj.short_name),
    }
    if include_json_data:
        scale_info["json_data"] = json.loads(scale_obj.json_data)
    return scale_info


def _build_record_scale_info(record, include_json_data: bool = False) -> Dict[str, Any]:
    scale_info = _build_scale_info(record.scale, include_json_data=include_json_data)
    if scale_info:
        return scale_info

    # Keep old records visible even if their historical scale definition was
    # removed from the current scale catalog.
    assessment_type = (
        "scoring"
        if record.raw_score is not None or record.final_score is not None
        else "categorical"
    )
    return {
        "id": str(record.scale_id or f"legacy-{record.id}"),
        "short_name": "LEGACY",
        "name": "历史测评",
        "description": "该记录对应的量表定义已不在当前量表目录中。",
        "category": "历史记录",
        "assessment_type": assessment_type,
        "display_group": "历史记录",
        "display_group_order": 99,
        "display_order": 99,
    }


def _normalize_result_details(result_details: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(result_details, dict):
        return result_details

    image_url = result_details.get("image_url")
    if image_url and not image_url.startswith("http"):
        result_details["image_url"] = f"{SERVER_BASE_URL}{image_url}"
    return result_details


def _build_assessment_response(record, include_scale_json: bool = False) -> Dict[str, Any]:
    result_details = json.loads(record.result_details) if record.result_details else None
    ai_analysis = None
    if isinstance(result_details, dict):
        ai_analysis = result_details.get("ai_analysis")
    response_dict = {
        "id": record.id,
        "user_id": record.user_id,
        "scale_id": record.scale_id,
        "answers": json.loads(record.answers) if record.answers else {},
        "raw_score": record.raw_score,
        "final_score": record.final_score,
        "result_level": record.result_level,
        "result_interpretation": record.result_interpretation,
        "result_recommendation": record.result_recommendation,
        "result_details": _normalize_result_details(result_details),
        "ai_analysis": ai_analysis,
        "completed_at": record.completed_at,
        "scale_info": _build_record_scale_info(record, include_json_data=False),
        "scale_details": _build_record_scale_info(record, include_json_data=include_scale_json),
    }
    return response_dict
    
    
@router.get(
    "/", 
    response_model=List[ScaleInfoResponse], 
    summary="获取所有可用的测评量表列表"
)
def get_all_available_scales():
    scales = assessment_tables.get_all_scales()
    return [_build_scale_info(scale) for scale in scales]

@router.get(
    "/{scale_id}", 
    response_model=FormattedScaleResponse, # <--- 1. 使用新的响应模型
    summary="获取单个量表的完整详情（已为前端格式化）" # <--- 2. 更新接口摘要
)
def get_single_scale_details(scale_id: str):
    # --- 3. 调用我们之前在 model/assessment.py 中创建的新方法 ---
    formatted_scale = assessment_tables.get_formatted_scale_details_by_id(scale_id)
    
    if not formatted_scale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scale not found")
        
    # --- 4. 直接返回格式化好的字典 ---
    return formatted_scale

@router.post(
    "/submit", 
    response_model=UserAssessmentResponse, 
    summary="提交测评答案并获取结果"
)
def submit_assessment_answers(
    request_data: SubmitAnswersRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    result_record = assessment_tables.create_user_assessment(
        user_id=current_user_id,
        request_data=request_data
    )
    if not result_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Failed to process assessment. Check scale_id or answers format."
        )

    return _build_assessment_response(result_record, include_scale_json=True)

@router.get(
    "/history/", 
    response_model=List[UserAssessmentResponse], 
    summary="获取当前用户的测评历史记录"
)
def get_user_assessment_history(current_user_id: str = Depends(get_current_user_id)):
    history = assessment_tables.get_assessments_by_user(user_id=current_user_id)
    
    response_list = []
    for record in history:
        response_list.append(_build_assessment_response(record, include_scale_json=False))
            
    return response_list

@router.delete(
    "/history/{record_id}", 
    status_code=status.HTTP_204_NO_CONTENT, 
    summary="删除一条测评记录"
)
def delete_assessment_record(
    record_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    success = assessment_tables.delete_user_assessment(
        user_id=current_user_id,
        record_id=record_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Record not found or you do not have permission to delete it."
        )
    return

@router.get(
    "/history/{record_id}", 
    response_model=UserAssessmentResponse, 
    summary="获取单条完整的测评历史记录详情"
)
def get_single_assessment_record(
    record_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    record = assessment_tables.get_assessment_by_id(record_id)
    if not record or record.user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    return _build_assessment_response(record, include_scale_json=True)


@router.post(
    "/history/{record_id}/ai-analysis",
    response_model=Dict[str, Any],
    summary="按需生成单条测评的 AI 分析",
)
def generate_single_assessment_ai_analysis(
    record_id: str,
    current_user_id: str = Depends(get_current_user_id),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
):
    record = assessment_tables.get_assessment_by_id(record_id)
    if not record or record.user_id != current_user_id or not record.scale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    if not is_health_assessment(record.scale.short_name, record.scale.category or ""):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "assessment_ai_not_available", "message": "该问卷暂不支持单次 AI 分析。"},
        )

    cached_analysis = assessment_tables.get_cached_ai_analysis_for_record(record)
    if cached_analysis:
        return {"ai_analysis": cached_analysis, "from_cache": True}

    reservation = reserve_feature_or_http(
        user_id=current_user_id,
        feature=FEATURE_ASSESSMENT_ANALYSIS,
        supplied_request_id=x_request_id or f"assessment:{record_id}:{uuid.uuid4()}",
    )
    try:
        try:
            answers = json.loads(record.answers) if record.answers else {}
            scale_data = json.loads(record.scale.json_data)
        except (TypeError, json.JSONDecodeError):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"code": "assessment_data_invalid", "message": "测评数据暂时无法读取。"},
            )

        result_data = {
            "result_level": record.result_level,
            "final_score": record.final_score,
            "result_interpretation": record.result_interpretation,
            "result_recommendation": record.result_recommendation,
        }
        ai_analysis = generate_assessment_ai_analysis(scale_data, result_data, answers)
        if not ai_analysis:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "model_generation_failed",
                    "message": "AI 分析暂时生成失败，请稍后重试。",
                },
            )

        assessment_tables.save_ai_analysis_for_record(record, ai_analysis)
        confirm_reservation(reservation)
        return {"ai_analysis": ai_analysis, "from_cache": False}
    except Exception:
        release_reservation(reservation)
        raise


