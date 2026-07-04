# router/assessment.py (图片URL拼接最终版)

import json
from fastapi import APIRouter, Depends, HTTPException, status
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

# ✅ 【第 1 步】: 在这里定义您的服务器基地址
# 部署时请务必替换为您的实际公网域名和端口
# 例如: "https://www.your-domain.com"
SERVER_BASE_URL = "http://127.0.0.1:8000"
CDN_ASSET_BASE_URL = "https://assets.feelyourself.cn/miniprogram/assets/v1"
MBTI_ASSET_VERSION = "202607050230"


def _normalize_asset_url(url: Optional[str]) -> Optional[str]:
    if url and url.startswith("/images/mbti/"):
        return f"{CDN_ASSET_BASE_URL}{url}?v={MBTI_ASSET_VERSION}"
    if url and not url.startswith("http"):
        return f"{SERVER_BASE_URL}{url}"
    return url

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

    try:
        raw_scale_data = json.loads(scale_obj.json_data or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        raw_scale_data = {}
    raw_scale_info = raw_scale_data.get("scale_info") if isinstance(raw_scale_data, dict) else {}
    cover_image_url = raw_scale_info.get("cover_image_url") if isinstance(raw_scale_info, dict) else None

    scale_info = {
        "id": scale_obj.id,
        "short_name": scale_obj.short_name,
        "name": scale_obj.name,
        "description": scale_obj.description,
        "cover_image_url": _normalize_asset_url(cover_image_url),
        "category": scale_obj.category or "专业测试",
        "assessment_type": scale_obj.assessment_type or "scoring",
        **get_assessment_display_meta(scale_obj.short_name),
    }
    if include_json_data:
        scale_info["json_data"] = raw_scale_data
    return scale_info


def _normalize_result_details(result_details: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(result_details, dict):
        return result_details

    image_url = result_details.get("image_url")
    if image_url:
        result_details["image_url"] = _normalize_asset_url(image_url)
    result_card_url = result_details.get("result_card_url")
    if result_card_url:
        result_details["result_card_url"] = _normalize_asset_url(result_card_url)
    return result_details


def _build_assessment_response(record, include_scale_json: bool = False) -> Dict[str, Any]:
    result_details = json.loads(record.result_details) if record.result_details else None
    ai_analysis = None
    if isinstance(result_details, dict):
        ai_analysis = result_details.get("ai_analysis")
    if not ai_analysis:
        ai_analysis = assessment_tables.ensure_ai_analysis_for_record(record)
        if ai_analysis:
            result_details = json.loads(record.result_details) if record.result_details else None

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
        "scale_info": _build_scale_info(record.scale) if record.scale else None,
        "scale_details": _build_scale_info(record.scale, include_json_data=include_scale_json) if record.scale else None,
    }
    return response_dict
    
    
@router.get(
    "/", 
    response_model=List[ScaleInfoResponse], 
    summary="获取所有可用的测评量表列表"
)
def get_all_available_scales(
    current_user_id: str = Depends(get_current_user_id)
):
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

    formatted_scale["cover_image_url"] = _normalize_asset_url(formatted_scale.get("cover_image_url"))
        
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


