# router/assessment.py

import json
from fastapi import APIRouter, Depends, HTTPException
from typing import List

# 1. 导入项目模块
# 假设你的 auth.py 在同一个 router 目录下
try:
    from .auth import get_current_user_id
except ImportError:
    # 如果结构不同，请相应调整
    # 这是一个备用导入，以防你的 auth 逻辑在项目根的 auth.py 中
    from auth import get_current_user_id

# 从 model 层导入数据访问对象和 Pydantic 模型
from model.assessment import (
    assessment_tables,
    ScaleInfoResponse,
    ScaleDetailResponse,
    SubmitAnswersRequest,
    UserAssessmentResponse
)
from model.user import User  # 导入User模型以便在响应中获取用户信息

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

@router.get("/", response_model=List[ScaleInfoResponse], summary="获取所有量表列表")
def get_all_available_scales():
    """
    提供给前端，用于展示所有可用的心理测评量表。
    返回一个包含所有量表基本信息的列表。
    """
    scales = assessment_tables.get_all_scales()
    return scales

@router.get("/{scale_id}", response_model=ScaleDetailResponse, summary="获取单个量表详情")
def get_single_scale_details(scale_id: str):
    """
    当用户选择一个特定的量表时，前端调用此接口获取完整的题目、选项和规则。
    """
    scale = assessment_tables.get_scale_by_id(scale_id)
    if not scale:
        raise HTTPException(status_code=404, detail="Scale not found")
    
    # 将从数据库取出的JSON字符串解析为字典
    scale.json_data = json.loads(scale.json_data)
    
    return scale

@router.post("/submit", response_model=UserAssessmentResponse, summary="提交测评答案并获取结果")
def submit_assessment_answers(
    request_data: SubmitAnswersRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    result_record = assessment_tables.create_user_assessment(
        user_id=current_user_id,
        request_data=request_data
    )
    
    if not result_record:
        raise HTTPException(status_code=400, detail="Failed to process assessment. Check scale_id or answers.")
    
    # 【关键修正】在返回前，将 answers 字符串解析回字典
    if isinstance(result_record.answers, str):
        result_record.answers = json.loads(result_record.answers)
    
    return result_record

@router.get("/history/", response_model=List[UserAssessmentResponse], summary="获取当前用户的测评历史")
def get_user_assessment_history(current_user_id: str = Depends(get_current_user_id)):
    """
    获取当前登录用户的所有历史测评记录，按时间倒序排列。
    这是一个受保护的路由。
    """
    history = assessment_tables.get_assessments_by_user(user_id=current_user_id)
    
    # 丰富返回信息，将 scale 的基本信息也一并返回
    response_list = []
    for record in history:
        # 将答案字符串解析为字典
        record.answers = json.loads(record.answers)
        
        # 附加量表信息
        if record.scale:
             record.scale_info = {
                "id": record.scale.id,
                "short_name": record.scale.short_name,
                "name": record.scale.name,
                "description": record.scale.description
             }
        response_list.append(record)
        
    return response_list


@router.delete("/history/{record_id}", status_code=204, summary="删除一条测评记录")
def delete_assessment_record(
    record_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    删除属于当前用户的一条指定的测评历史记录。
    这是一个受保护的路由。
    """
    success = assessment_tables.delete_user_assessment(
        user_id=current_user_id,
        record_id=record_id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Record not found or you do not have permission to delete it.")
    
    # 成功时，FastAPI 会自动返回 204 No Content 状态码
    return