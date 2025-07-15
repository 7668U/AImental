# router/feedback.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List

# 1. 从项目其他文件中导入
from model.feedback import feedback_table, FeedbackModel
from .auth import get_current_user_id 

# ---------------------------------------------------
# Router 设置
# ---------------------------------------------------
router = APIRouter(
    prefix="/feedback",
    tags=["Feedback - 用户反馈"],
)

# ---------------------------------------------------
# Pydantic 请求体模型
# ---------------------------------------------------
class FeedbackCreateRequest(BaseModel):
    """创建反馈时的请求体"""
    # 【新增】增加 feedback_type 字段
    feedback_type: str
    content: str

# ---------------------------------------------------
# API Endpoints
# ---------------------------------------------------

@router.post("/", response_model=FeedbackModel, status_code=201, summary="提交新的用户反馈")
def submit_feedback(
    request: FeedbackCreateRequest, # <--- 请求体现在包含 feedback_type
    current_user_id: str = Depends(get_current_user_id)
):
    """
    用户提交一条新的反馈。
    - **feedback_type**: 反馈类型 ('optimization' 或 'bug')
    - **content**: 反馈内容，不能为空。
    - 需要有效的 Token 进行认证。
    """
    # 【修改】将 feedback_type 传递给数据库处理函数
    new_feedback = feedback_table.create_feedback(
        user_id=current_user_id,
        content=request.content,
        feedback_type=request.feedback_type
    )
    return new_feedback


# --- 其他接口无需修改 ---

@router.get("/", response_model=List[FeedbackModel], summary="获取我的历史反馈")
def get_my_feedback_history(current_user_id: str = Depends(get_current_user_id)):
    """
    获取当前登录用户提交过的所有反馈记录，按时间从新到旧排序。
    - 需要有效的 Token 进行认证。
    """
    return feedback_table.get_feedback_by_user(user_id=current_user_id)


@router.delete("/{feedback_id}", status_code=200, summary="删除一条反馈")
def delete_single_feedback(
    feedback_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    删除指定 ID 的反馈记录。
    - 为了安全，服务器会校验这条反馈是否属于当前登录用户。
    - 需要有效的 Token 进行认证。
    """
    feedback_to_delete = feedback_table.get_feedback_by_id(feedback_id)
    if not feedback_to_delete:
        raise HTTPException(status_code=404, detail="Feedback not found")

    if feedback_to_delete.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this feedback")

    feedback_table.delete_feedback(feedback_id)

    return {"message": "Feedback deleted successfully"}