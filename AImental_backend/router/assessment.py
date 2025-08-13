# router/assessment.py (图片URL拼接最终版)

import json
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

# 1. 导入项目模块
try:
    from .auth import get_current_user_id
except (ImportError, ModuleNotFoundError):
    from auth import get_current_user_id

from model.assessment import (
    assessment_tables,
    ScaleInfoResponse,
    ScaleDetailResponse,
    SubmitAnswersRequest,
    UserAssessmentResponse
)

# ✅ 【第 1 步】: 在这里定义您的服务器基地址
# 部署时请务必替换为您的实际公网域名和端口
# 例如: "https://www.your-domain.com"
SERVER_BASE_URL = "http://127.0.0.1:8000"

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

@router.get(
    "/", 
    response_model=List[ScaleInfoResponse], 
    summary="获取所有可用的测评量表列表"
)
def get_all_available_scales(
    current_user_id: str = Depends(get_current_user_id)
):
    scales = assessment_tables.get_all_scales()
    return scales

@router.get(
    "/{scale_id}", 
    response_model=ScaleDetailResponse, 
    summary="获取单个量表的完整详情"
)
def get_single_scale_details(scale_id: str):
    scale = assessment_tables.get_scale_by_id(scale_id)
    if not scale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scale not found")
    
    scale.json_data = json.loads(scale.json_data)
    return scale

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

    response_dict = {
        "id": result_record.id,
        "user_id": result_record.user_id,
        "scale_id": result_record.scale_id,
        "answers": json.loads(result_record.answers) if result_record.answers else {},
        "raw_score": result_record.raw_score,
        "final_score": result_record.final_score,
        "result_level": result_record.result_level,
        "result_interpretation": result_record.result_interpretation,
        "result_recommendation": result_record.result_recommendation,
        "result_details": json.loads(result_record.result_details) if result_record.result_details else None,
        "completed_at": result_record.completed_at,
        "scale_info": None,
        "scale_details": None
    }
    
    scale_obj = assessment_tables.get_scale_by_id(request_data.scale_id)
    if scale_obj:
        response_dict['scale_details'] = {
            "id": scale_obj.id, "short_name": scale_obj.short_name,
            "name": scale_obj.name, "description": scale_obj.description,
            "category": scale_obj.category, "assessment_type": scale_obj.assessment_type,
            "json_data": json.loads(scale_obj.json_data)
        }
    
    # ✅ 【第 2 步】: 在返回前，为图片URL添加服务器地址前缀
    if response_dict.get("result_details") and isinstance(response_dict["result_details"], dict):
        image_url = response_dict["result_details"].get("image_url")
        # 如果 image_url 存在，且不是以 http 开头的完整路径
        if image_url and not image_url.startswith("http"):
            response_dict["result_details"]["image_url"] = f"{SERVER_BASE_URL}{image_url}"

    return response_dict

@router.get(
    "/history/", 
    response_model=List[UserAssessmentResponse], 
    summary="获取当前用户的测评历史记录"
)
def get_user_assessment_history(current_user_id: str = Depends(get_current_user_id)):
    history = assessment_tables.get_assessments_by_user(user_id=current_user_id)
    
    response_list = []
    for record in history:
        item = {
            "id": record.id, "user_id": record.user_id, "scale_id": record.scale_id,
            "answers": json.loads(record.answers) if record.answers else {},
            "raw_score": record.raw_score, "final_score": record.final_score,
            "result_level": record.result_level,
            "result_interpretation": record.result_interpretation,
            "result_recommendation": record.result_recommendation,
            "result_details": json.loads(record.result_details) if record.result_details else None,
            "completed_at": record.completed_at,
            "scale_details": None, "scale_info": None,
        }
        
        if record.scale:
            item['scale_info'] = ScaleInfoResponse.from_orm(record.scale).model_dump()
        
        # ✅ 【第 2 步】: 对列表中的每一项都进行URL拼接处理
        if item.get("result_details") and isinstance(item["result_details"], dict):
            image_url = item["result_details"].get("image_url")
            if image_url and not image_url.startswith("http"):
                item["result_details"]["image_url"] = f"{SERVER_BASE_URL}{image_url}"
        
        response_list.append(item)
            
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

    response_dict = {
        "id": record.id, "user_id": record.user_id, "scale_id": record.scale_id,
        "answers": json.loads(record.answers) if record.answers else {},
        "raw_score": record.raw_score, "final_score": record.final_score,
        "result_level": record.result_level,
        "result_interpretation": record.result_interpretation,
        "result_recommendation": record.result_recommendation,
        "result_details": json.loads(record.result_details) if record.result_details else None,
        "completed_at": record.completed_at,
        "scale_info": None, "scale_details": None
    }
    
    if record.scale:
        scale_obj = record.scale
        response_dict['scale_details'] = {
            "id": scale_obj.id, "short_name": scale_obj.short_name,
            "name": scale_obj.name, "description": scale_obj.description,
            "category": scale_obj.category, "assessment_type": scale_obj.assessment_type,
            "json_data": json.loads(scale_obj.json_data)
        }
    
    # ✅ 【第 2 步】: 同样地，为这个接口也添加URL拼接逻辑
    if response_dict.get("result_details") and isinstance(response_dict["result_details"], dict):
        image_url = response_dict["result_details"].get("image_url")
        if image_url and not image_url.startswith("http"):
            response_dict["result_details"]["image_url"] = f"{SERVER_BASE_URL}{image_url}"

    return response_dict