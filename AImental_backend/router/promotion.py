# routers/promotion.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# 1. 从项目其他文件中导入
from model.promotion import (
    SOUL_DRINK_SCORE_MAP,
    promotion_table,
    soul_drink_table,
    test_data,
    TestResultResponseModel,
)
from .auth import get_current_user_id # 用于保护需要登录的接口

# ---------------------------------------------------
# Router Setup
# ---------------------------------------------------
router = APIRouter(
    prefix="/promotion",
    tags=["Promotion - 趣味问卷推广"],
)

# ---------------------------------------------------
# Pydantic Models for API validation
# ---------------------------------------------------

class SessionStartResponse(BaseModel):
    session_id: str

class QuestionOptionModel(BaseModel):
    id: str
    text: str

class QuestionModel(BaseModel):
    order: int
    text: str
    options: List[QuestionOptionModel]

class SubmissionRequest(BaseModel):
    session_id: str
    answers: List[Dict[str, Any]] = Field(..., description="例如: [{'order': 1, 'option_id': 'a'}]")

# ✨ 新增：用于“认领”接口的请求体
class ClaimRequest(BaseModel):
    session_id: str


class SoulDrinkSessionRequest(BaseModel):
    visitor_token: Optional[str] = None


class SoulDrinkProgressRequest(BaseModel):
    visitor_token: str
    answers: List[Optional[str]] = Field(default_factory=list)
    current_index: int = 0


class SoulDrinkCompleteRequest(BaseModel):
    visitor_token: str
    answers: List[str]


class SoulDrinkSessionResponse(BaseModel):
    visitor_token: str
    status: str
    current_index: int = 0
    answers: List[Any] = Field(default_factory=list)
    scores: Optional[Dict[str, int]] = None
    result_type: Optional[str] = None
    result_drink: Optional[str] = None
    result_card: Optional[str] = None
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None
    completed_at: Optional[Any] = None

# ---------------------------------------------------
# API Endpoints
# ---------------------------------------------------

@router.post("/start", response_model=SessionStartResponse, summary="1. H5 - 开始测试")
def start_test_session():
    """H5页面调用，创建匿名测试会话。"""
    record = promotion_table.create_test_session()
    if not record:
        raise HTTPException(status_code=500, detail="创建会话失败")
    return SessionStartResponse(session_id=record.session_id)


@router.get("/questions", response_model=List[QuestionModel], summary="2. H5 - 获取题目")
def get_all_questions():
    """H5页面获取所有题目和选项（不含答案）。"""
    questions_data = test_data.get("questions", [])
    if not questions_data:
        raise HTTPException(status_code=404, detail="未找到问卷题目")
    
    response_questions = [
        QuestionModel(
            order=q['order'], 
            text=q['text'], 
            options=[QuestionOptionModel(id=opt['id'], text=opt['text']) for opt in q.get('options', [])]
        ) for q in questions_data
    ]
    return response_questions


@router.post("/submit", summary="3. H5 - 提交答案")
def submit_answers(request: SubmissionRequest):
    """H5页面提交答案，后端计算并保存结果。"""
    full_questions_map = {q['order']: q for q in test_data.get('questions', [])}
    answers_with_target = []
    for ans in request.answers:
        question = full_questions_map.get(ans.get('order'))
        if question:
            for opt in question.get('options', []):
                if opt.get('id') == ans.get('option_id'):
                    answers_with_target.append({'target_personality_id': opt['target_personality_id']})
                    break
    
    if not answers_with_target:
        raise HTTPException(status_code=400, detail="无效的答案")

    result_id = promotion_table.submit_test_answers(
        session_id=request.session_id,
        answers=answers_with_target
    )
    
    if not result_id:
        raise HTTPException(status_code=404, detail="会话无效或已完成")
        
    return {"message": "提交成功，请前往小程序查看结果。"}


@router.post("/claim-result", summary="4. 小程序 - 认领测试结果")
def claim_test_result(
    request: ClaimRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    【小程序专用】用户登录后，调用此接口将匿名测试结果与当前用户绑定。
    需要有效的JWT Token。
    """
    linked_record = promotion_table.link_user_to_session(
        session_id=request.session_id,
        user_id=current_user_id
    )
    if not linked_record:
        raise HTTPException(status_code=404, detail="认领失败，会话ID无效或已被认领")
    
    return {"message": "结果认领成功！"}


@router.get("/my-result", response_model=TestResultResponseModel, summary="5. 小程序 - 获取我的结果")
def get_my_test_result(current_user_id: str = Depends(get_current_user_id)):
    """
    【小程序专用】获取当前登录用户的测试结果详情。
    需要有效的JWT Token。
    """
    record = promotion_table.get_result_by_user_id(user_id=current_user_id)
    if not record or not record.result_personality_id:
        raise HTTPException(status_code=404, detail="未找到您的测试结果，请先完成测试。")
    
    personality_details = promotion_table.get_personality_details(record.result_personality_id)
    if not personality_details:
        raise HTTPException(status_code=500, detail="结果数据错误，请联系管理员。")

    return TestResultResponseModel(**personality_details)


@router.post("/soul-drink/session", response_model=SoulDrinkSessionResponse, summary="H5 灵魂饮料 - 获取或创建匿名档案")
def get_or_create_soul_drink_session(request: SoulDrinkSessionRequest):
    record = soul_drink_table.get_or_create_session(request.visitor_token)
    return SoulDrinkSessionResponse(**soul_drink_table.serialize(record))


@router.post("/soul-drink/progress", response_model=SoulDrinkSessionResponse, summary="H5 灵魂饮料 - 保存答题进度")
def save_soul_drink_progress(request: SoulDrinkProgressRequest):
    if len(request.answers) > 15:
        raise HTTPException(status_code=400, detail="答案数量超过题目数量")

    record = soul_drink_table.save_progress(
        visitor_token=request.visitor_token,
        answers=request.answers,
        current_index=request.current_index,
    )
    if not record:
        raise HTTPException(status_code=404, detail="匿名档案不存在")

    return SoulDrinkSessionResponse(**soul_drink_table.serialize(record))


@router.post("/soul-drink/complete", response_model=SoulDrinkSessionResponse, summary="H5 灵魂饮料 - 保存并返回测试结果")
def complete_soul_drink_test(request: SoulDrinkCompleteRequest):
    if len(request.answers) != 15:
        raise HTTPException(status_code=400, detail="请完成全部 15 题")
    if any(
        answer not in SOUL_DRINK_SCORE_MAP[index]
        for index, answer in enumerate(request.answers)
    ):
        raise HTTPException(status_code=400, detail="答案格式无效")

    record = soul_drink_table.complete(
        visitor_token=request.visitor_token,
        answers=request.answers,
    )
    if not record:
        raise HTTPException(status_code=404, detail="匿名档案不存在")

    return SoulDrinkSessionResponse(**soul_drink_table.serialize(record))


@router.post("/soul-drink/restart", response_model=SoulDrinkSessionResponse, summary="H5 灵魂饮料 - 覆盖并重新测试")
def restart_soul_drink_test(request: SoulDrinkSessionRequest):
    if not request.visitor_token:
        raise HTTPException(status_code=400, detail="缺少匿名档案 token")

    record = soul_drink_table.restart(request.visitor_token)
    if not record:
        raise HTTPException(status_code=404, detail="匿名档案不存在")

    return SoulDrinkSessionResponse(**soul_drink_table.serialize(record))
