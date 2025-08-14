# routers/ai_community.py

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio
import json
import random

# --- 导入所有需要的组件 ---

# 认证
from .auth import get_current_user_id

# Pydantic模型
from model.friendship import Friendship
from model.chat_community import ChatListSummaryModel, ChatMessageModel
from model.ai_character import AICharacterModel

# 数据表管理类
from model.friendship import friendship_table
from model.chat_community import community_chat_table
from model.ai_character import ai_character_table
from model.ai_status import ai_status_table
from model.ai_task import ai_task_table

from pydantic import BaseModel, Field

# ---------------------------------------------------
# Router 设置
# ---------------------------------------------------
router = APIRouter(
    prefix="/community",
    tags=["AI Community - 心灵社区核心接口"],
)

# ===================================================
# --- 0. WebSocket 实时通信管理 ---
# ===================================================

class ConnectionManager:
    """管理所有活跃的WebSocket连接。"""
    def __init__(self):
        # 使用字典来存储连接，键为user_id，值为WebSocket对象
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"WebSocket connected for user: {user_id}")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            print(f"WebSocket disconnected for user: {user_id}")

    async def send_personal_message(self, message: Dict[str, Any], user_id: str):
        """向指定用户发送JSON消息。"""
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            try:
                await websocket.send_json(message)
                print(f"Sent message to user {user_id}: {message}")
            except Exception as e:
                print(f"Error sending message to user {user_id}: {e}")
                self.disconnect(user_id)

# 实例化连接管理器
manager = ConnectionManager()

# WebSocket 端点
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """
    WebSocket主端点。客户端连接时需要提供JWT Token进行认证。
    """
    try:
        # 伪代码：实际项目中应使用更健壮的token验证
        user_id = get_current_user_id(token) 
        if not user_id:
            await websocket.close(code=1008)
            return
    except:
        await websocket.close(code=1008)
        return

    await manager.connect(user_id, websocket)
    try:
        while True:
            # 等待客户端发送消息，例如心跳包或已读回执
            data = await websocket.receive_text()
            # 在这里可以处理客户端发来的消息，比如“已读”回执
            # message = json.loads(data)
            # if message.get("type") == "read_receipt":
            #     community_chat_table.mark_as_read(user_id, message.get("character_id"))
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        print(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(user_id)


# ===================================================
# --- 1. 好友关系 (Friendship) 相关接口 ---
# ===================================================

class FriendRequestForm(BaseModel):
    verification_message: str

@router.post("/friendship/request/{character_id}", summary="向AI角色发送好友请求")
def send_friend_request(
    character_id: str,
    form: FriendRequestForm,
    current_user_id: str = Depends(get_current_user_id),
):
    status = friendship_table.get_friendship_status(current_user_id, character_id)
    if status in ['accepted', 'pending']:
        raise HTTPException(status_code=400, detail="请求已发送或你们已是好友")

    friendship_table.create_request(
        user_id=current_user_id,
        character_id=character_id,
        message=form.verification_message
    )
    
    execute_at = datetime.now() + timedelta(minutes=random.randint(1, 5))
    ai_task_table.create_task_if_needed(
        user_id=current_user_id,
        character_id=character_id,
        task_type='friend_request_response',
        execute_at=execute_at
    )
    
    return {"message": "好友请求已发送"}

@router.get("/friendship/requests", summary="获取我发送的好友请求列表")
def get_my_friend_requests(current_user_id: str = Depends(get_current_user_id)):
    # friendship_table需要实现一个新方法来支持此功能
    return {"message": "功能待实现"}

@router.get("/friendship/status/{character_id}", summary="查询与某个AI的好友状态")
def check_friendship_status(
    character_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    status = friendship_table.get_friendship_status(current_user_id, character_id)
    return {"status": status}


# ===================================================
# --- 2. 角色发现 (Character Discovery) ---
# ===================================================

@router.get("/characters", response_model=List[AICharacterModel], summary="获取可添加的AI角色列表")
def list_discoverable_characters(current_user_id: str = Depends(get_current_user_id)):
    return ai_character_table.get_all_characters()


# ===================================================
# --- 3. 聊天核心 (Chat Core) 相关接口 ---
# ===================================================

@router.get("/chats", response_model=List[ChatListSummaryModel], summary="获取用户的聊天会话列表")
def get_chat_list(current_user_id: str = Depends(get_current_user_id)):
    """获取会话列表，包含未读数。"""
    return community_chat_table.get_chat_list_for_user(current_user_id)

@router.get("/chats/{character_id}", summary="获取与指定AI的聊天历史记录")
def get_chat_history(
    character_id: str,
    current_user_id: str = Depends(get_current_user_id),
    limit: int = 50,
):
    """进入聊天页面时调用，获取历史消息，并【将该会话标记为已读】。"""
    # 将此会话的未读数清零
    community_chat_table.mark_as_read(current_user_id, character_id)
    history = community_chat_table.get_conversation_history(current_user_id, character_id, limit=limit)
    return history

class MessageForm(BaseModel):
    content: str

@router.post("/chats/{character_id}/messages", summary="用户向AI发送消息")
def send_message(
    character_id: str,
    form: MessageForm,
    current_user_id: str = Depends(get_current_user_id)
):
    friend_status = friendship_table.get_friendship_status(current_user_id, character_id)
    if friend_status != 'accepted':
        raise HTTPException(status_code=403, detail="你们还不是好友")

    community_chat_table.add_message(
        user_id=current_user_id,
        character_id=character_id,
        role='user',
        content=form.content
    )

    ai_status = ai_status_table.get_current_status(character_id)
    delay_minutes = ai_status.reply_delay_minutes if ai_status else 5
    execute_at = datetime.now() + timedelta(minutes=delay_minutes + random.uniform(0, delay_minutes * 0.2))

    ai_task_table.create_task_if_needed(
        user_id=current_user_id,
        character_id=character_id,
        task_type='reply',
        execute_at=execute_at
    )
    
    return {"message": "消息已发送"}

# ===================================================
# --- 4. 实时推送逻辑 (集成到后台任务中) ---
# ===================================================
# 注意：这部分不是API，而是需要在您的 background_worker.py 中调用的逻辑
# 我在这里写出函数原型，您需要将其整合到您的worker任务处理流程中

async def push_message_to_user(user_id: str, character_id: str, message_content: str):
    """
    当AI生成回复后，通过WebSocket推送给用户。
    """
    # 1. 存储消息到数据库，这一步会增加未读数
    new_msg_record = community_chat_table.add_message(
        user_id=user_id,
        character_id=character_id,
        role='ai',
        content=message_content
    )
    
    # 2. 准备推送的JSON数据
    # 使用ChatMessageModel来确保数据格式一致
    message_data = ChatMessageModel(
        role='ai',
        content=message_content,
        timestamp=new_msg_record.last_message_timestamp
    ).model_dump()
    
    # 3. 构造推送的完整载荷
    payload = {
        "type": "new_message",
        "from_character_id": character_id,
        "message": message_data
    }
    
    # 4. 通过WebSocket管理器发送
    await manager.send_personal_message(payload, user_id)

async def push_friend_request_result(user_id: str, character_id: str, status: str, initial_message: Optional[str] = None):
    """
    当好友请求被处理后，通过WebSocket推送结果。
    """
    payload = {
        "type": "friend_request_result",
        "from_character_id": character_id,
        "status": status, # 'accepted' or 'rejected'
        "initial_message": initial_message # 如果接受了，附带第一条消息
    }
    await manager.send_personal_message(payload, user_id)
