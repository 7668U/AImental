# routers/chat.py

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
import json

# 统一从你的项目模块导入
from .auth import get_current_user_id
# [修正] 从 model.chat 中导入 Chat (用于数据库操作) 和 ChatModel (用于API响应)
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
# 2. 此路由专用的Pydantic模型
# ---------------------------------------------------

class CreateChatResponse(BaseModel):
    """创建新空会话后的响应体"""
    chat_id: str
    title: str
    message: str

class ChatSummary(BaseModel):
    """聊天历史列表中的单项摘要"""
    id: str
    title: str

class RespondRequest(BaseModel):
    """发送消息的请求体"""
    message: str

class RespondResponse(BaseModel):
    """处理消息后的响应体"""
    reply: str
    title: Optional[str] = None  # 新标题是可选的，只在首次回复时返回

# ---------------------------------------------------
# 3. API 接口
# ---------------------------------------------------

@router.post("/", response_model=CreateChatResponse, status_code=status.HTTP_201_CREATED)
def create_a_new_chat_session(current_user_id: str = Depends(get_current_user_id)):
    """
    **为当前用户创建一个新的、空的聊天会话**

    此接口不接受任何请求体，仅创建一个包含默认标题的会话。
    """
    # 调用数据库函数创建会话，该函数已包含默认标题
    new_chat = chat_table.create_new_chat(user_id=current_user_id)
    
    if not new_chat:
        raise HTTPException(status_code=500, detail="Could not create a new chat session.")
    
    # 返回新会话的ID和默认标题
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
    **处理用户消息，获取AI回复，并在需要时生成和更新标题**

    - 安全性: 验证该聊天是否属于当前用户。
    - 核心逻辑: 如果是用户的首条消息，则在返回回复的同时，生成并更新标题。
    """
    # 验证聊天是否存在且属于当前用户
    chat_session = chat_table.get_chat_history_by_id(chat_id)
    if not chat_session or chat_session.user_id != current_user_id:
        raise HTTPException(status_code=404, detail="Chat not found or permission denied.")

    # 检查这是否是用户的首条消息
    history = json.loads(chat_session.message)
    is_first_user_message = len(history) == 0

    # 调用LLM函数获取回复 (此函数内部已包含保存用户和AI消息的逻辑)
    reply_content = get_ai_response_and_update_history(chat_id, request_data.message)
    if not reply_content:
        raise HTTPException(status_code=500, detail="Failed to get AI response.")

    new_title = None
    if is_first_user_message:
        # 如果是首条消息，调用函数生成标题
        new_title = generate_chat_title(request_data.message)
        # 将新标题更新到数据库
        db_query = Chat.update(title=new_title).where(Chat.id == chat_id)
        db_query.execute()

    # 返回AI的回复，以及可选的新标题
    return RespondResponse(reply=reply_content, title=new_title)


@router.get("/", response_model=List[ChatSummary])
def get_all_chat_summaries_for_the_current_user(current_user_id: str = Depends(get_current_user_id)):
    """**获取该用户所有的聊天摘要列表（ID和标题）**"""
    chat_summaries = chat_table.get_chat_summaries_for_user(user_id=current_user_id)
    return chat_summaries


@router.get("/{chat_id}", response_model=ChatModel)
def get_a_specific_chat_history(
    chat_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    **[已修正] 根据ID获取单条完整的聊天记录**
    
    使用正确的Pydantic模型 `ChatModel` 作为响应模型。
    """
    chat_session = chat_table.get_chat_history_by_id(chat_id=chat_id)

    if not chat_session or chat_session.user_id != current_user_id:
        raise HTTPException(status_code=404, detail="Chat not found or permission denied.")
    
    return chat_session


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_a_chat_session(chat_id: str, current_user_id: str = Depends(get_current_user_id)):
    """**根据ID删除一个聊天条目**"""
    chat_to_delete = chat_table.get_chat_history_by_id(chat_id=chat_id)
    
    if not chat_to_delete or chat_to_delete.user_id != current_user_id:
        raise HTTPException(status_code=404, detail="Chat not found or permission denied.")

    success = chat_table.delete_chat_by_id(chat_id=chat_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete the chat session.")
    
    # 成功删除后，按惯例返回204状态码，无需返回消息体
    return