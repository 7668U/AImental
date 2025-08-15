from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
import json

from .auth import get_current_user_id
# 【第1步】: 确保导入的是更新后的 ChatModel
from model.chat import chat_table, Chat, ChatModel
from LLM import get_ai_response_and_update_history, generate_chat_title

# ---------------------------------------------------
# 1. 路由设置
# ---------------------------------------------------
router = APIRouter(
    prefix="/chats",
    tags=["Chats - 聊天管理"],
)

# ---------------------------------------------------
# 2. Pydantic模型
# ---------------------------------------------------

# 【第2步】: 新增一个用于创建聊天的请求体模型
class CreateChatRequest(BaseModel):
    with_context: Optional[bool] = True

# 【第3步】: 修改创建聊天的响应模型，加入 with_context
class CreateChatResponse(BaseModel):
    chat_id: str
    title: str
    message: str
    with_context: bool

class ChatSummary(BaseModel):
    id: str
    title: str

class RespondRequest(BaseModel):
    message: str

class RespondResponse(BaseModel):
    reply: str
    title: Optional[str] = None
    
class UpdateChatTitleRequest(BaseModel):
    title: str

# ---------------------------------------------------
# 3. API 接口
# ---------------------------------------------------

# 【第4步】: 大幅修改创建新聊天的接口
@router.post("/", response_model=CreateChatResponse, status_code=status.HTTP_201_CREATED)
def create_a_new_chat_session(
    request_data: CreateChatRequest, # 使用新的请求模型
    current_user_id: str = Depends(get_current_user_id)
):
    """
    根据用户设置（是否携带历史背景）创建一个新的聊天会话。
    """
    # 将前端传来的值传递给数据库操作函数
    new_chat = chat_table.create_new_chat(
        user_id=current_user_id,
        with_context=request_data.with_context
    )
    if not new_chat:
        raise HTTPException(status_code=500, detail="Could not create a new chat session.")
    
    # 在响应中也返回创建的状态
    return CreateChatResponse(
        chat_id=new_chat.id,
        title=new_chat.title,
        message="New chat session created successfully.",
        with_context=new_chat.with_context
    )

@router.post("/{chat_id}/respond", response_model=RespondResponse)
def chat_respond(
    chat_id: str,
    request_data: RespondRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    chat_session = chat_table.get_chat_history_by_id(chat_id)
    if not chat_session or chat_session.user_id != current_user_id:
        raise HTTPException(status_code=404, detail="Chat not found or permission denied.")

    history = json.loads(chat_session.message)
    is_first_user_message = len(history) == 0

    reply_content = get_ai_response_and_update_history(chat_id, request_data.message)
    if not reply_content:
        raise HTTPException(status_code=500, detail="Failed to get AI response.")

    new_title = None
    if is_first_user_message:
        new_title = generate_chat_title(request_data.message)
        db_query = Chat.update(title=new_title).where(Chat.id == chat_id)
        db_query.execute()

    return RespondResponse(reply=reply_content, title=new_title)


@router.get("/", response_model=List[ChatSummary])
def get_all_chat_summaries_for_the_current_user(current_user_id: str = Depends(get_current_user_id)):
    chat_summaries = chat_table.get_chat_summaries_for_user(user_id=current_user_id)
    return chat_summaries


@router.get("/{chat_id}", response_model=ChatModel)
def get_a_specific_chat_history(
    chat_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    chat_session = chat_table.get_chat_history_by_id(chat_id=chat_id)
    if not chat_session or chat_session.user_id != current_user_id:
        raise HTTPException(status_code=404, detail="Chat not found or permission denied.")
    # 因为 ChatModel 已经更新，这里会自动返回 with_context 字段
    return chat_session


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_a_chat_session(chat_id: str, current_user_id: str = Depends(get_current_user_id)):
    chat_to_delete = chat_table.get_chat_history_by_id(chat_id=chat_id)
    if not chat_to_delete or chat_to_delete.user_id != current_user_id:
        raise HTTPException(status_code=404, detail="Chat not found or permission denied.")

    if not chat_table.delete_chat_by_id(chat_id=chat_id):
        raise HTTPException(status_code=500, detail="Failed to delete the chat session.")
    return

@router.patch("/{chat_id}", status_code=status.HTTP_200_OK)
def update_chat_title_endpoint(
    chat_id: str,
    request_data: UpdateChatTitleRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    chat_session = chat_table.get_chat_history_by_id(chat_id)
    if not chat_session or chat_session.user_id != current_user_id:
        raise HTTPException(status_code=404, detail="Chat not found or permission denied.")
    
    if not chat_table.update_chat_title(chat_id, request_data.title):
        raise HTTPException(status_code=500, detail="Failed to update chat title.")
        
    return {"message": "Title updated successfully"}