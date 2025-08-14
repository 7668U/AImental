# routers/ai_community.py (已集成Redis)

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio
import json
import random
import redis # 【新增】导入redis库
# --- 导入所有需要的组件 ---

# 认证
from .auth import get_current_user_id

# Pydantic模型
from model.friendship import Friendship
from model.chat_community import ChatListSummaryModel, ChatMessageModel
from model.ai_character import AICharacterModel,AICharacter

# 数据表管理类
from model.friendship import friendship_table
from model.chat_community import community_chat_table
from model.ai_character import ai_character_table
from model.ai_status import ai_status_table
from model.ai_task import ai_task_table
from redis import asyncio as aioredis
from pydantic import BaseModel, Field
import pytz
from .auth import get_current_user_id  # 导入你实际的认证依赖项
import traceback
# ---------------------------------------------------
# Router 设置
# ---------------------------------------------------
router = APIRouter(
    prefix="/community",
    tags=["AI Community - 心灵社区核心接口"],
)

# ===================================================
# --- 0. Redis 及 WebSocket 实时通信管理 (已重构) ---
# ===================================================

# 【修改】配置 aioredis 客户端
# 我们将在应用启动时创建连接池，而不是在这里直接创建实例
redis_client = None

@router.on_event("startup")
async def startup_event():
    """应用启动时，创建aioredis连接池。"""
    global redis_client
    try:
        redis_client = aioredis.from_url(
            "redis://localhost", # 在docker-compose网络中使用服务名'redis'
            # 如果你是本地运行，请使用 "redis://localhost"
            encoding="utf-8", 
            decode_responses=True
        )
        await redis_client.ping()
        print("✅ Successfully connected to aioredis.")
    except Exception as e:
        print(f"❌ Could not connect to aioredis: {e}")
        redis_client = None

@router.on_event("shutdown")
async def shutdown_event():
    """应用关闭时，关闭aioredis连接池。"""
    if redis_client:
        await redis_client.close()
        print("🔌 Aioredi-s connection closed.")


# 【重构】WebSocket 端点，现在使用 aioredis 的异步 Pub/Sub
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    try:
        user_id = get_current_user_id(token)
        if not user_id or not redis_client:
            await websocket.close(code=1008)
            return
    except Exception:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    print(f"WebSocket connected for user: {user_id}")
    
    channel = f"ws_channel:{user_id}"
    
    async def client_message_handler(ws: WebSocket):
        """处理来自客户端的消息（如心跳包）。"""
        try:
            while True:
                await ws.receive_text() # 只接收，不处理，维持连接
        except WebSocketDisconnect:
            print(f"Client {user_id} disconnected.")

    async def redis_listener(ws: WebSocket):
        """监听Redis频道并将消息推送给客户端。"""
        async with redis_client.pubsub() as pubsub:
            await pubsub.subscribe(channel)
            print(f"User {user_id} subscribed to Redis channel '{channel}'")
            try:
                # 使用异步迭代器，这是一个非阻塞的循环
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        message_data = json.loads(message["data"])
                        await ws.send_json(message_data)
            except Exception as e:
                print(f"Redis listener error for {user_id}: {e}")

    # 并发运行两个任务
    listener_task = asyncio.create_task(redis_listener(websocket))
    handler_task = asyncio.create_task(client_message_handler(websocket))
    
    done, pending = await asyncio.wait(
        [listener_task, handler_task], return_when=asyncio.FIRST_COMPLETED
    )
    for task in pending:
        task.cancel()
    print(f"WebSocket session ended for user: {user_id}")


async def redis_message_handler(websocket: WebSocket, pubsub):
    """一个独立的协程，专门用来监听Redis频道的消息并推送给前端。"""
    while True:
        # get_message会阻塞等待，直到有消息或超时
        message =  pubsub.get_message(ignore_subscribe_messages=True, timeout=60)
        if message:
            try:
                message_data = json.loads(message["data"])
                await websocket.send_json(message_data)
                print(f"Sent message from Redis to WebSocket: {message_data}")
            except Exception as e:
                print(f"Error processing message from Redis: {e}")
                break # 出现错误时中断循环
        await asyncio.sleep(0.01) # 短暂休眠，避免CPU空转


async def client_message_handler(websocket: WebSocket, user_id: str):
    """一个独立的协程，专门用来接收来自前端的消息（如心跳包）。"""
    while True:
        try:
            data = await websocket.receive_text()
            # 这里可以处理心跳包或客户端发来的其他指令
            # print(f"Received message from client {user_id}: {data}")
        except WebSocketDisconnect:
            print(f"Client {user_id} disconnected.")
            break # 客户端断开，中断循环


# ===================================================
# --- 1. 好友关系 (Friendship) 相关接口 (保持不变) ---
# ===================================================

class FriendRequestForm(BaseModel):
    verification_message: str

@router.post("/friendship/request/{character_id}", summary="向AI角色发送好友请求")
def send_friend_request(
    character_id: str,
    form: FriendRequestForm,
    current_user_id: str = Depends(get_current_user_id),
):
    # 这部分的所有逻辑都保持原样
    status = friendship_table.get_friendship_status(current_user_id, character_id)
    if status in ['accepted', 'pending']:
        raise HTTPException(status_code=400, detail="请求已发送或你们已是好友")

    friendship_table.create_request(
        user_id=current_user_id,
        character_id=character_id,
        message=form.verification_message
    )
    
    delay = timedelta(seconds=10)
    beijing_tz = pytz.timezone('Asia/Shanghai')
    execute_at = datetime.now(beijing_tz) + delay
    
    ai_task_table.create_task_if_needed(
        user_id=current_user_id,
        character_id=character_id,
        task_type='friend_request_response',
        execute_at=execute_at
    )
    
    return {"message": "好友请求已发送"}

@router.get("/friendship/requests", summary="获取我发送的好友请求列表")
def get_my_friend_requests(current_user_id: str = Depends(get_current_user_id)):
    return {"message": "功能待实现"}

@router.get("/friendship/status/{character_id}", summary="查询与某个AI的好友状态")
def check_friendship_status(
    character_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    status = friendship_table.get_friendship_status(current_user_id, character_id)
    return {"status": status}


# ===================================================
# --- 2. 角色发现 (Character Discovery) (保持不变) ---
# ===================================================

@router.get("/characters", response_model=List[AICharacterModel], summary="获取可添加的AI角色列表")
def list_discoverable_characters(current_user_id: str = Depends(get_current_user_id)):
    return ai_character_table.get_all_characters()


# ===================================================
# --- 3. 聊天核心 (Chat Core) 相关接口 (保持不变) ---
# ===================================================

@router.get("/chats", response_model=List[ChatListSummaryModel], summary="获取用户的聊天会话列表")
def get_chat_list(current_user_id: str = Depends(get_current_user_id)):
    return community_chat_table.get_chat_list_for_user(current_user_id)

@router.get("/chats/{character_id}", summary="获取与指定AI的聊天历史记录")
def get_chat_history(
    character_id: str,
    current_user_id: str = Depends(get_current_user_id),
    limit: int = 50,
):
    # 【核心修正】将函数名从 mark_as_read 改为 mark_as_peeked
    community_chat_table.mark_as_peeked(current_user_id, character_id)
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
    # 这部分的所有逻辑都保持原样
    friend_status = friendship_table.get_friendship_status(current_user_id, character_id)
    if friend_status != 'accepted':
        raise HTTPException(status_code=403, detail="你们还不是好友")

    community_chat_table.add_message(
        user_id=current_user_id,
        character_id=character_id,
        role='user',
        content=form.content
    )
    
    delay = timedelta(seconds=10)
    beijing_tz = pytz.timezone('Asia/Shanghai')
    execute_at = datetime.now(beijing_tz) + delay
    execute_at += timedelta(seconds=random.randint(0, 30))
    
    ai_task_table.create_task_if_needed(
        user_id=current_user_id,
        character_id=character_id,
        task_type='reply',
        execute_at=execute_at
    )
    
    return {"message": "消息已发送"}

# --- 【新增】的聊天详情接口 (保持不变) ---
class ChatDetailsResponse(BaseModel):
    history: List[Dict[str, Any]] = Field(..., description="聊天历史记录列表")
    character_status: str = Field(..., description="AI角色当前的实时状态文本")

@router.get(
    "/chats/{character_id}/details", 
    response_model=ChatDetailsResponse, 
    summary="【新】获取聊天详情（历史记录+AI状态）"
)
def get_chat_details(
    character_id: str,
    current_user_id: str = Depends(get_current_user_id),
    limit: int = 50,
):
    community_chat_table.mark_as_peeked(current_user_id, character_id)
    history = community_chat_table.get_conversation_history(
        user_id=current_user_id, 
        character_id=character_id, 
        limit=limit
    )
    current_status_obj = ai_status_table.get_current_status(character_id)
    character_status_text = current_status_obj.status_text if current_status_obj else "在线"
    return ChatDetailsResponse(
        history=history,
        character_status=character_status_text
    )

# ===================================================
# --- 4. 实时推送逻辑 (已重构) ---
# ===================================================
# 注意：这些函数现在是同步的，供你的 background_worker.py 调用

def push_message_to_user(user_id: str, character_id: str, message_content: str):
    """
    【重构】当AI生成回复后，通过Redis发布消息。
    """
    if not redis_client:
        print("Redis is not connected. Cannot push message.")
        return
        
    new_msg_record = community_chat_table.add_message(
        user_id=user_id,
        character_id=character_id,
        role='ai',
        content=message_content
    )
    
    message_data = ChatMessageModel(
        role='ai',
        content=message_content,
        timestamp=new_msg_record.last_message_timestamp
    ).model_dump()
    
    payload = {
        "type": "new_message",
        "from_character_id": character_id,
        "message": message_data
    }
    
    channel = f"ws_channel:{user_id}"
    redis_client.publish(channel, json.dumps(payload))
    print(f"Published message to Redis channel '{channel}' for user {user_id}")

def push_friend_request_result(user_id: str, character_id: str, status: str, initial_message: Optional[str] = None):
    """
    【重构】当好友请求被处理后，通过Redis发布结果。
    """
    if not redis_client:
        print("Redis is not connected. Cannot push friend request result.")
        return

    payload = {
        "type": "friend_request_result",
        "from_character_id": character_id,
        "status": status,
        "initial_message": initial_message
    }
    channel = f"ws_channel:{user_id}"
    redis_client.publish(channel, json.dumps(payload))
    print(f"Published friend request result to Redis channel '{channel}' for user {user_id}")


@router.get("/discover/characters",
            response_model=List[AICharacterModel],
            summary="获取可发现的AI角色列表",
            description="获取当前用户尚未成为好友或已发送请求的AI角色列表。")
async def get_discoverable_characters(user_id: str = Depends(get_current_user_id)):
    """
    为用户提供一个用于“发现”或“添加好友”的AI角色列表。

    此接口直接依赖 `get_current_user_id` 来获取当前用户的ID字符串。
    其核心逻辑保持不变，但代码更简洁：
    1. 通过依赖项直接获取 user_id。
    2. 在'friendships'表中查找该用户已关联（好友或待处理）的AI角色ID。
    3. 查询'ai_characters'表，并排除掉这些已关联的角色。
    """
    try:
        # 1. 查找所有需要排除的AI角色的ID
        # 依赖项已经确保了user_id是有效的，所以我们直接使用
        excluded_character_query = Friendship.select(Friendship.character).where(
            (Friendship.user == user_id) &
            ((Friendship.status == 'accepted') | (Friendship.status == 'pending'))
        )
        
        excluded_character_ids = [friendship.character.id for friendship in excluded_character_query]

        # 2. 查询所有ID不在排除列表中的AI角色
        discoverable_characters = AICharacter.select().where(
            AICharacter.id.not_in(excluded_character_ids)
        )

        # 3. FastAPI会自动将Peewee对象列表（如果response_model是Pydantic模型）序列化为JSON
        return list(discoverable_characters)

    except Exception as e:
        # 捕获可能的数据库错误或其他未知异常
        print(f"Error fetching discoverable characters for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="获取角色列表时发生服务器内部错误")
    
    
    
# --- Pydantic模型 (保持不变) ---
class FriendshipHistoryItem(BaseModel):
    """ 定义单条好友申请历史记录的数据结构 """
    character_id: str
    character_name: str
    character_avatar_url: str
    status: str
    request_timestamp: datetime
    verification_message: str

    class Config:
        from_attributes = True

# --- 获取历史记录的API接口【调试版】 ---

@router.get("/friendship/history",
            response_model=List[FriendshipHistoryItem],
            summary="获取当前用户的好友申请历史",
            description="返回一个列表，包含用户所有已发送的好友申请及其当前状态。")
async def get_friendship_history(user_id: str = Depends(get_current_user_id)):
    """
    【调试版】
    加入了详细的print输出，用于定位500错误。
    """
    print("\n--- [DEBUG] Entering /friendship/history endpoint ---")
    try:
        print(f"[DEBUG] 1. Received request for user_id: {user_id}")

        history_query = (Friendship
                         .select(
                             AICharacter.id.alias('character_id'),
                             AICharacter.name.alias('character_name'),
                             AICharacter.avatar_url.alias('character_avatar_url'),
                             Friendship.status,
                             Friendship.request_timestamp,
                             Friendship.verification_message
                         )
                         .join(AICharacter, on=(Friendship.character == AICharacter.id))
                         .where(Friendship.user == user_id)
                         .order_by(Friendship.request_timestamp.desc())
                         .dicts())
        
        # 打印出将要执行的SQL语句
        print(f"[DEBUG] 2. Generated SQL Query: {history_query.sql()}")

        print("[DEBUG] 3. Executing query and fetching data from database...")
        # 执行查询并将结果转为列表
        history_list = list(history_query)
        print(f"[DEBUG] 4. Query successful. Fetched {len(history_list)} records.")
        
        # 打印从数据库获取到的原始数据（在Pydantic验证前）
        # 如果数据很多，可以只打印第一条
        if history_list:
            print(f"[DEBUG] 5. Raw data sample (first record): {history_list[0]}")
        else:
            print("[DEBUG] 5. Raw data is empty.")

        print("[DEBUG] 6. Returning data for Pydantic validation and response...")
        return history_list

    except Exception as e:
        # 【核心调试】打印完整的错误堆栈信息
        print("\n--- [ERROR] An exception occurred! ---")
        print(f"[ERROR] Exception Type: {type(e).__name__}")
        print(f"[ERROR] Exception Details: {e}")
        print("[ERROR] Full Traceback:")
        traceback.print_exc() # 打印详细的错误路径
        print("--- [ERROR] End of exception info ---\n")
        
        # 依然向前端返回标准的500错误
        raise HTTPException(status_code=500, detail="获取申请历史时发生服务器内部错误")
    

# --- 【核心新增】在文件末尾增加一个新的API接口 ---
@router.post("/chats/{character_id}/peek", summary="用户窥视聊天窗口，标记为已读")
async def user_peek_at_chat(
    character_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    这个接口用于客户端通知服务器，用户已经进入或正在查看某个聊天窗口。
    服务器收到通知后，会将对应会话的 user_has_peeked 状态设为 True。
    """
    success = community_chat_table.mark_as_peeked(user_id, character_id)
    if not success:
        # 这个错误通常不关键，可以不向前端抛出异常，只在后端记录
        print(f"警告: 标记用户 {user_id} 窥视角色 {character_id} 的操作未找到记录或失败。")
    return {"message": "Peek status updated"}