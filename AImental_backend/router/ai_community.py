# routers/ai_community.py

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect,status
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio
import json
import random
import redis # 【新增】导入redis库
from redis.backoff import NoBackoff
from redis.retry import Retry
# --- 导入所有需要的组件 ---

# 认证
from .auth import get_current_user_id

# Pydantic模型
from model.friendship import friendship_table
from model.friendship import Friendship
from model.chat_community import ChatListSummaryModel, ChatMessageModel, community_chat_table
from model.ai_character import AICharacterModel,AICharacter, ai_character_table
from model.ai_status import ai_status_table
from model.ai_task import ai_task_table
from model.community_memory import community_memory_table
from redis import asyncio as aioredis
from pydantic import BaseModel, Field
import pytz
from .auth import get_current_user_id # 导入你实际的认证依赖项
import traceback
from logger_config import logger
from generate_community_response import generate_ai_response, build_night_reply_context

from datetime import datetime, date # 【修改】导入 date
# ---------------------------------------------------
# Router 设置
# ---------------------------------------------------
router = APIRouter(
    prefix="/community",
    tags=["AI Community - 心灵社区核心接口"],
)

# 定义北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def _build_response_status_context(
    *,
    current_status,
    user_id: str,
    character_id: str,
    now: datetime,
) -> Dict[str, str]:
    """把角色日程转换成回复风格。日程只影响语气，不再阻断回复。"""
    category = current_status.status_category if current_status else "在线"
    status_text = current_status.status_text if current_status else "正在看消息"
    focus_level = current_status.focus_level if current_status else "AVAILABLE"

    is_night = now.hour >= 23 or now.hour < 7
    looks_like_sleep = "睡" in category or "睡" in status_text or focus_level == "UNINTERRUPTIBLE"

    response_mode = "normal"
    response_guidance = "正常陪伴式回复。"
    if is_night or looks_like_sleep:
        response_mode = "night_soft"
        response_guidance = build_night_reply_context(user_id, character_id, now)
    elif focus_level == "HIGH":
        response_mode = "focused"
        response_guidance = "你手头原本有事，但已经看到用户消息。回复可以更短、更像从事情里抬头说话，但不能拒绝或暂停。"
    elif focus_level == "LOW":
        response_mode = "low_energy"
        response_guidance = "你状态比较松弛，可以自然接话，不要表现得像客服。"

    return {
        "status_title": category,
        "status_description": status_text,
        "focus_level": focus_level,
        "response_mode": response_mode,
        "response_guidance": response_guidance,
    }

def _save_ai_messages_and_build_payload(
    user_id: str,
    character_id: str,
    messages: List[str],
) -> List[Dict[str, Any]]:
    saved_messages = []
    for content in messages[:5]:
        cleaned_content = str(content).strip()
        if not cleaned_content:
            continue
        conversation = community_chat_table.add_message(
            user_id=user_id,
            character_id=character_id,
            role="ai",
            content=cleaned_content,
        )
        if not conversation:
            continue
        try:
            history = json.loads(conversation.messages_history)
            if history:
                saved_messages.append(history[-1])
        except json.JSONDecodeError:
            logger.warning("AI消息已保存，但解析 messages_history 失败。")
    if saved_messages:
        community_chat_table.mark_as_peeked(user_id, character_id)
    return saved_messages

# ===================================================
# --- 0. Redis 及 WebSocket 实时通信管理 ---
# ===================================================

redis_client = None
active_reply_sessions: set[str] = set()

@router.on_event("startup")
async def startup_event():
    """应用启动时，创建aioredis连接池。"""
    global redis_client
    try:
        redis_client = aioredis.from_url(
            "redis://127.0.0.1", # 本地运行时避免 localhost 解析到不可用地址
            # 如果你是本地运行，请使用 "redis://localhost"
            encoding="utf-8", 
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
            retry_on_timeout=False,
            retry=Retry(NoBackoff(), 0),
            health_check_interval=0,
        )
        await redis_client.ping()
        logger.info("✅ Router 'ai_community' 已成功连接到 aioredis。")
    except Exception as e:
        logger.warning(f"Router 'ai_community' 未连接到 aioredis，实时推送能力将跳过: {e}")
        redis_client = None

@router.on_event("shutdown")
async def shutdown_event():
    """应用关闭时，关闭aioredis连接池。"""
    if redis_client:
        await redis_client.close()
        logger.info("🔌 Router 'ai_community' 的 aioredis 连接已关闭。")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """WebSocket端点，用于实时消息推送。"""
    try:
        user_id = get_current_user_id(token)
        if not user_id or not redis_client:
            await websocket.close(code=1008)
            return
    except Exception:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    logger.info(f"WebSocket connected for user: {user_id}")
    
    channel = f"ws_channel:{user_id}"
    
    async def client_message_handler(ws: WebSocket):
        """处理来自客户端的消息（如心跳包）。"""
        try:
            while True:
                await ws.receive_text() # 只接收，不处理，维持连接
        except WebSocketDisconnect:
            logger.info(f"Client {user_id} disconnected.")

    async def redis_listener(ws: WebSocket):
        """监听Redis频道并将消息推送给客户端。"""
        async with redis_client.pubsub() as pubsub:
            await pubsub.subscribe(channel)
            logger.info(f"User {user_id} subscribed to Redis channel '{channel}'")
            try:
                # 使用异步迭代器，这是一个非阻塞的循环
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        message_data = json.loads(message["data"])
                        await ws.send_json(message_data)
            except Exception as e:
                logger.error(f"Redis listener error for {user_id}: {e}")

    # 并发运行两个任务
    listener_task = asyncio.create_task(redis_listener(websocket))
    handler_task = asyncio.create_task(client_message_handler(websocket))
    
    done, pending = await asyncio.wait(
        [listener_task, handler_task], return_when=asyncio.FIRST_COMPLETED
    )
    for task in pending:
        task.cancel()
    logger.info(f"WebSocket session ended for user: {user_id}")


# --- 【保留】您原始文件中的辅助函数 ---
async def redis_message_handler(websocket: WebSocket, pubsub):
    """一个独立的协程，专门用来监听Redis频道的消息并推送给前端。"""
    while True:
        message = pubsub.get_message(ignore_subscribe_messages=True, timeout=60)
        if message:
            try:
                message_data = json.loads(message["data"])
                await websocket.send_json(message_data)
                print(f"Sent message from Redis to WebSocket: {message_data}")
            except Exception as e:
                print(f"Error processing message from Redis: {e}")
                break
        await asyncio.sleep(0.01)


async def client_message_handler(websocket: WebSocket, user_id: str):
    """一个独立的协程，专门用来接收来自前端的消息（如心跳包）。"""
    while True:
        try:
            data = await websocket.receive_text()
        except WebSocketDisconnect:
            print(f"Client {user_id} disconnected.")
            break


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
    raise HTTPException(status_code=status.HTTP_410_GONE, detail="好友申请机制已下线")

@router.get("/friendship/requests", summary="获取我发送的好友请求列表")
def get_my_friend_requests(current_user_id: str = Depends(get_current_user_id)):
    raise HTTPException(status_code=status.HTTP_410_GONE, detail="好友申请机制已下线")

@router.get("/friendship/status/{character_id}", summary="查询与某个AI的好友状态")
def check_friendship_status(
    character_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    return {"status": "open"}


# ===================================================
# --- 2. 角色发现 (Character Discovery) ---
# ===================================================

@router.get("/characters", response_model=List[AICharacterModel], summary="获取可添加的AI角色列表")
def list_discoverable_characters(current_user_id: str = Depends(get_current_user_id)):
    return ai_character_table.get_all_characters()


# ===================================================
# --- 3. 聊天核心 (Chat Core) 相关接口 ---
# ===================================================

@router.get("/chats", response_model=List[ChatListSummaryModel], summary="获取所有AI角色聊天入口")
def get_chat_list(current_user_id: str = Depends(get_current_user_id)):
    return community_chat_table.get_chat_list_for_user(current_user_id)

@router.get("/chats/{character_id}", summary="获取与指定AI的聊天历史记录")
def get_chat_history(
    character_id: str,
    current_user_id: str = Depends(get_current_user_id),
    limit: int = 100,
):
    community_chat_table.mark_as_peeked(current_user_id, character_id)
    history = community_chat_table.get_conversation_history(current_user_id, character_id, limit=limit)
    return history

class MessageForm(BaseModel):
    content: str

class SendMessageResponse(BaseModel):
    message: str
    daily_count: int = -1
    ai_messages: List[Dict[str, Any]] = Field(default_factory=list)

@router.post("/chats/{character_id}/messages", summary="用户向AI发送消息")
async def send_message(
    character_id: str,
    form: MessageForm,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    【最终升级版】
    处理用户发送的消息。
    集成每日消息数量限制，并同步返回AI的分段回复。
    """
    character = ai_character_table.get_character_by_id(character_id)
    if not character:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")

    reply_lock_key = f"{current_user_id}:{character_id}"
    if reply_lock_key in active_reply_sessions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="对方正在回复您哦~稍后再发吧"
        )

    active_reply_sessions.add(reply_lock_key)
    try:
        # --- 【新增校验 1：每日消息数量限制】 ---
        if not redis_client:
            # Redis 是可选实时组件；不可用时跳过每日计数。
            logger.warning("Redis client is not available. Skipping daily message limit check.")
        else:
            daily_count = await get_today_message_count(current_user_id)
            if daily_count >= MESSAGE_LIMIT_PER_DAY:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"您今天发送的总消息条数已经达到{MESSAGE_LIMIT_PER_DAY}条限额啦~明天再来玩吧~"
                )

        final_count = -1
        if redis_client:
            today_str = date.today().isoformat()
            redis_key = f"daily_message_count:{current_user_id}:{today_str}"
            new_count = await redis_client.incr(redis_key)
            if new_count == 1:
                await redis_client.expire(redis_key, timedelta(days=1))

            logger.info(f"User({current_user_id}) sent a message. Today's count is now: {new_count}/{MESSAGE_LIMIT_PER_DAY}")
            final_count = new_count

        community_chat_table.add_message(
            user_id=current_user_id,
            character_id=character_id,
            role='user',
            content=form.content
        )

        now = datetime.now(BEIJING_TZ)
        current_status = ai_status_table.get_current_status(character_id)
        full_day_schedule = ai_status_table.get_schedule_for_date(character_id, now.date())
        history = community_chat_table.get_conversation_history(current_user_id, character_id, limit=50)
        memory_context = community_memory_table.get_prompt_context(current_user_id, character_id)
        status_context = _build_response_status_context(
            current_status=current_status,
            user_id=current_user_id,
            character_id=character_id,
            now=now,
        )

        structured_response = await asyncio.to_thread(
            generate_ai_response,
            character_profile=character.profile,
            current_ai_status=status_context,
            conversation_history=history,
            full_day_schedule=full_day_schedule,
            current_beijing_time=now,
            memory_context=memory_context,
        )

        ai_messages = []
        if structured_response and structured_response.messages:
            ai_messages = _save_ai_messages_and_build_payload(
                current_user_id,
                character_id,
                structured_response.messages,
            )

        if not ai_messages:
            logger.warning(f"角色 {character_id} 未能生成可保存的AI回复。")

        community_chat_table.update_conversation_state(
            user_id=current_user_id,
            character_id=character_id,
            state="CONTINUOUS",
            resumes_at=None,
        )

        try:
            queued = community_memory_table.queue_memory_update_if_needed(
                current_user_id,
                character_id,
                ai_task_table,
            )
            if queued:
                logger.info(f"已为用户 {current_user_id} 与角色 {character_id} 排队记忆更新任务。")
        except Exception:
            logger.error(
                f"为用户 {current_user_id} 与角色 {character_id} 排队记忆更新任务失败。",
                exc_info=True,
            )

        return SendMessageResponse(
            message="消息已发送",
            daily_count=final_count,
            ai_messages=ai_messages,
        )
    finally:
        active_reply_sessions.discard(reply_lock_key)
# --- 【核心升级点】 ---
class ChatDetailsResponse(BaseModel):
    history: List[Dict[str, Any]] = Field(..., description="聊天历史记录列表")
    character_status: str = Field(..., description="AI角色当前的实时状态文本")
    character: AICharacterModel = Field(..., description="AI角色资料卡信息")

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
    # --- 【调试日志 1】: 打印函数的入口和收到的参数 ---
    logger.debug(f"--- [GET /details DEBUG] 1. 函数开始执行，收到请求，角色ID: {character_id}")

    character = ai_character_table.get_character_by_id(character_id)
    if not character:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")

    community_chat_table.mark_as_peeked(current_user_id, character_id)
    history = community_chat_table.get_conversation_history(
        user_id=current_user_id, 
        character_id=character_id, 
        limit=limit
    )

    # --- 【调试日志 2】: 打印即将调用的关键函数 ---
    logger.debug(f"--- [GET /details DEBUG] 2. 准备调用 ai_status_table.get_current_status...")
    
    current_status_obj = ai_status_table.get_current_status(character_id)

    # --- 【调试日志 3】: 打印关键函数的返回结果，这是最重要的一步！---
    logger.debug(f"--- [GET /details DEBUG] 3. get_current_status 调用完成，返回的对象是: {current_status_obj}")

    # --- 【调试日志 4】: 根据返回结果，记录将要执行的逻辑分支 ---
    if current_status_obj:
        logger.debug(f"--- [GET /details DEBUG] 4. 对象不为空，将使用 status_category: '{current_status_obj.status_category}'")
        character_status_text = current_status_obj.status_category
    else:
        logger.warning(f"--- [GET /details DEBUG] 4. 对象为空 (None)，将使用默认状态 '在线'")
        character_status_text = "在线"

    # --- 【调试日志 5】: 打印最终要返回给前端的数据 ---
    logger.debug(f"--- [GET /details DEBUG] 5. 最终返回给前端的状态文本是: '{character_status_text}' ---")
    
    return ChatDetailsResponse(
        history=history,
        character_status=character_status_text,
        character=character
    )

# ===================================================
# --- 4. 【保留】实时推送逻辑 ---
# ===================================================
# 注意：这些函数在您的原始代码中存在，但并未在此文件内被调用。
# 它们可能是为了被 background_worker.py 导入而存在。为保持一致性，予以保留。

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
    # redis_client.publish(channel, json.dumps(payload))
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
    # redis_client.publish(channel, json.dumps(payload))
    print(f"Published friend request result to Redis channel '{channel}' for user {user_id}")


    
    
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
        
        print(f"[DEBUG] 2. Generated SQL Query: {history_query.sql()}")

        print("[DEBUG] 3. Executing query and fetching data from database...")
        history_list = list(history_query)
        print(f"[DEBUG] 4. Query successful. Fetched {len(history_list)} records.")
        
        if history_list:
            print(f"[DEBUG] 5. Raw data sample (first record): {history_list[0]}")
        else:
            print("[DEBUG] 5. Raw data is empty.")

        print("[DEBUG] 6. Returning data for Pydantic validation and response...")
        return history_list

    except Exception as e:
        print("\n--- [ERROR] An exception occurred! ---")
        print(f"[ERROR] Exception Type: {type(e).__name__}")
        print(f"[ERROR] Exception Details: {e}")
        print("[ERROR] Full Traceback:")
        traceback.print_exc()
        print("--- [ERROR] End of exception info ---\n")
        
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
        logger.debug(f"用户 {user_id} 正在查看尚未开始的角色会话 {character_id}。")
    return {"message": "Peek status updated"}

# ===================================================
# --- 【核心新增】聊天状态查询接口 ---
# ===================================================

class ChatStatusResponse(BaseModel):
    daily_count: int = Field(..., description="用户今日已发送消息数")
    limit: int = Field(..., description="每日消息上限")

MESSAGE_LIMIT_PER_DAY = 50

async def get_today_message_count(user_id: str) -> int:
    """【新增】从Redis获取用户今日发送的消息数"""
    if not redis_client:
        return 0
    today_str = date.today().isoformat()
    redis_key = f"daily_message_count:{user_id}:{today_str}"
    count = await redis_client.get(redis_key)
    return int(count) if count else 0

@router.get(
    "/chats/status",
    response_model=ChatStatusResponse,
    summary="获取用户的聊天状态（如每日消息数）"
)
async def get_user_chat_status(current_user_id: str = Depends(get_current_user_id)):
    """
    返回用户今天的消息发送计数和每日上限。
    前端可以在进入聊天页时调用此接口来初始化UI状态。
    """
    daily_count = await get_today_message_count(current_user_id)
    return ChatStatusResponse(daily_count=daily_count, limit=MESSAGE_LIMIT_PER_DAY)


# 确保导入了你的 User 模型
from model.user import User

# (可选但推荐) 为了接口返回结构更清晰，定义一个新的 Pydantic 模型
from pydantic import BaseModel
class DiscoverResponse(BaseModel):
    characters: List[AICharacterModel]
    total_count: int
    is_fully_unlocked: bool

@router.get("/discover/characters",
            response_model=DiscoverResponse,
            summary="获取可发现的AI角色列表")
async def get_discoverable_characters(user_id: str = Depends(get_current_user_id)):
    # --- 日志 1: 记录函数入口和关键参数 ---
    logger.info(f"开始为用户 {user_id} 获取可发现角色...")
    
    try:
        # 1. 获取当前用户对象
        user = User.get_or_none(User.id == user_id)
        if not user:
            logger.warning(f"用户ID: {user_id} 在数据库中未找到。")
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # --- 日志 2: 打印用户的解锁状态 ---
        logger.debug(f"成功找到用户: {user.id}, 社区解锁状态: {user.has_unlocked_community}")

        # 2. 获取所有可发现的角色完整列表
        # 注意：这里的 .where(...) 我用一个有效的查询代替了，请确保你的代码是完整的
        # 如果你的 Friendship 表还没有数据，这个查询会返回空，是正常的
        try:
            excluded_character_query = Friendship.select(Friendship.character).where(
                (Friendship.user == user_id) & 
                (Friendship.status.in_(['pending', 'accepted']))
            )
            excluded_character_ids = [friendship.character.id for friendship in excluded_character_query]
            # --- 日志 3: 打印排除了多少个角色 ---
            logger.debug(f"需要排除的角色ID列表: {excluded_character_ids}")
        except Exception as e:
            logger.error(f"查询 Friendship 表时出错: {e}", exc_info=True)
            excluded_character_ids = [] # 查询失败时，给一个空列表，避免整个接口崩溃

        all_discoverable_query = AICharacter.select().where(AICharacter.id.not_in(excluded_character_ids))
        all_discoverable_list = list(all_discoverable_query)
        # --- 日志 4: 打印总共找到了多少个可发现角色 ---
        logger.debug(f"数据库中总共找到 {len(all_discoverable_list)} 个可供发现的角色。")

        # 3. 根据用户的解锁状态，决定返回哪些角色数据
        characters_to_send = []
        if user.has_unlocked_community:
            characters_to_send = all_discoverable_list
        elif all_discoverable_list:
            characters_to_send = [all_discoverable_list[0]]
        
        # --- 日志 5: 打印最终决定要发送的角色数量 ---
        logger.debug(f"根据解锁状态，本次准备发送 {len(characters_to_send)} 个角色给前端。")
        
        # 4. 按照新的响应模型格式返回数据
        response_data = DiscoverResponse(
            characters=characters_to_send,
            total_count=len(all_discoverable_list),
            is_fully_unlocked=user.has_unlocked_community
        )
        
        # --- 日志 6: 打印最终要返回给前端的完整数据结构 (这是最重要的日志！) ---
        # 使用 .model_dump_json() 可以得到一个格式化好的 JSON 字符串，非常适合调试
        logger.info(f"最终返回给前端的数据结构:\n{response_data.model_dump_json(indent=2)}")
        
        return response_data

    except Exception as e:
        # --- 日志 7: 捕获所有未知异常 ---
        # exc_info=True 会把详细的错误堆栈信息也记录下来，非常有用！
        logger.error(f"为用户 {user_id} 获取角色时发生未知异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取角色列表时发生服务器内部错误")
    
# routers/ai_community.py

# ... (您文件里所有已存在的代码) ...


# --- 【请将以下代码完整粘贴到文件末尾】 ---

from fastapi import Query

@router.get(
    "/debug/has_schedule/{character_id}", 
    summary="【调试专用】检查角色在特定日期是否有日程"
)
def debug_check_schedule_exists(
    character_id: str,
    # 使用 Query 来让 FastAPI 生成更清晰的文档，并设置别名
    target_date_str: str = Query(
        ..., 
        alias="date",
        description="要查询的日期，格式必须为 YYYY-MM-DD",
        examples=["2025-08-18"]
    ),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    一个用于快速调试的接口，直接调用 ai_status_table.has_schedule_for_date
    来验证指定角色在某一天是否存在任何日程记录。
    """
    logger.info(f"[DEBUG /has_schedule] 收到对角色 {character_id} 在日期 {target_date_str} 的检查请求。")
    
    try:
        # 1. 将字符串格式的日期转换为 date 对象
        target_date_obj = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        logger.error(f"[DEBUG /has_schedule] 日期格式错误: '{target_date_str}'。必须是 YYYY-MM-DD。")
        raise HTTPException(
            status_code=400, 
            detail=f"日期格式错误: '{target_date_str}'。请使用 YYYY-MM-DD 格式。"
        )

    # 2. 调用核心业务逻辑函数
    try:
        exists = ai_status_table.has_schedule_for_date(character_id, target_date_obj)
        logger.info(f"[DEBUG /has_schedule] ai_status_table.has_schedule_for_date 返回: {exists}")
        
        # 3. 返回一个清晰的JSON结果
        return {
            "character_id": character_id,
            "date_checked": target_date_str,
            "schedule_exists": exists,
            "message": "检查完成。"
        }
    except Exception as e:
        logger.error(f"[DEBUG /has_schedule] 调用 has_schedule_for_date 时发生未知错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="在检查日程是否存在时服务器发生内部错误。"
        )
