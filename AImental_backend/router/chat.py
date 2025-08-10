# routers/chat.py

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
import json

from .auth import get_current_user_id
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

class CreateChatResponse(BaseModel):
    chat_id: str
    title: str
    message: str

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

@router.post("/", response_model=CreateChatResponse, status_code=status.HTTP_201_CREATED)
def create_a_new_chat_session(current_user_id: str = Depends(get_current_user_id)):
    new_chat = chat_table.create_new_chat(user_id=current_user_id)
    if not new_chat:
        raise HTTPException(status_code=500, detail="Could not create a new chat session.")
    return CreateChatResponse(
        chat_id=new_chat.id,
        title=new_chat.title,
        message="New empty chat session created successfully."
    )

@router.post("/{chat_id}/respond", response_model=RespondResponse)
def chat_respond(
    chat_id: str,
    request_data: RespondRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    处理用户消息，获取AI回复，并在需要时生成和更新标题。
    【已更新】现在会将 user_id 传递给 LLM 函数。
    """
    chat_session = chat_table.get_chat_history_by_id(chat_id)
    if not chat_session or chat_session.user_id != current_user_id:
        raise HTTPException(status_code=404, detail="Chat not found or permission denied.")

    history = json.loads(chat_session.message)
    is_first_user_message = len(history) == 0

    # --- 【修改】将 current_user_id 传递下去 ---
    reply_content = get_ai_response_and_update_history(chat_id, current_user_id, request_data.message)
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
    return chat_session


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_a_chat_session(chat_id: str, current_user_id: str = Depends(get_current_user_id)):
    chat_to_delete = chat_table.get_chat_history_by_id(chat_id=chat_id)
    if not chat_to_delete or chat_to_delete.user_id != current_user_id:
        raise HTTPException(status_code=4.04, detail="Chat not found or permission denied.")

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
