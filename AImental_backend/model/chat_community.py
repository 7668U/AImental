import uuid
import time
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# 导入Peewee和Pydantic的核心组件
from peewee import Model, CharField, TextField, IntegerField, FloatField, ForeignKeyField, DoesNotExist, BooleanField, DateTimeField

from pydantic import BaseModel, Field

# 导入数据库连接和日志记录器
from db import chat_db 
from logger_config import logger 
from security.data_encryption import EncryptedTextField

# 确保从正确的路径导入您的AICharacter模型
from .ai_character import AICharacter
import pytz
# 定义北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')
FAVORABILITY_UPDATE_INTERVAL = 20

# ---------------------------------------------------
# 1. Pydantic 数据模型 (保持不变)
# ---------------------------------------------------

class ChatMessageModel(BaseModel):
    """定义了单条聊天消息的结构，包含时间戳。"""
    role: str = Field(..., description="消息发送者的角色: 'user' 或 'ai'")
    content: str = Field(..., description="消息的文本内容")
    timestamp: int = Field(default_factory=lambda: int(time.time()))

class ChatListSummaryModel(BaseModel):
    """
    【已改造】用于API返回聊天列表摘要的输出模型。
    使用 unread 布尔值代替了 unread_count。
    """
    character_id: str
    character_name: str
    character_avatar_url: str
    last_message_snippet: str
    last_message_timestamp: int
    favorability: float
    unread: bool = Field(..., description="用户是否还没查看最新消息 (True代表有红点)")
    current_status: str = Field(default="在线", description="AI角色当前的状态类别")

# ---------------------------------------------------
# 2. Peewee 数据库模型 (已升级)
# ---------------------------------------------------

class CommunityChat(Model):
    """
    【已升级】Peewee模型: 存储用户与单个AI角色之间的完整对话及关系数据。
    """
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    
    user_id = CharField(index=True)
    character = ForeignKeyField(AICharacter, field='id', backref='chats', on_delete='CASCADE')
    
    messages_history = EncryptedTextField(
        purpose="community_chats.messages_history",
        default='[]',
    )
    favorability = FloatField(default=0.0)
    favorability_history = EncryptedTextField(
        purpose="community_chats.favorability_history",
        default='[]',
    )
    
    user_has_peeked = BooleanField(default=True, help_text="用户是否已查看过由AI发送的最新消息")
    
    # --- 【核心新增】对话微观状态 ---
    conversation_state = CharField(
        max_length=20, 
        default='CONTINUOUS', 
        help_text="对话的微观状态: 'CONTINUOUS' (可连续对话) or 'PAUSED' (AI已暂停)"
    )
    conversation_resumes_at = DateTimeField(
        null=True, 
        help_text="如果状态是PAUSED, AI预计会在此时间后回归"
    )
    # --- --------------------------- ---
    
    last_message_timestamp = IntegerField(default=lambda: int(time.time()))
    last_message_snippet = EncryptedTextField(
        purpose="community_chats.last_message_snippet",
        default="点击开始聊天",
    )

    class Meta:
        database = chat_db
        table_name = 'community_chats'
        indexes = ((('user_id', 'character_id'), True),)

# ---------------------------------------------------
# 3. 数据表管理类 (已升级)
# ---------------------------------------------------

class CommunityChatTable:
    """封装所有对 'community_chats' 表的数据库操作。"""

    DEFAULT_GREETINGS = {
        "泠月": "嗯……你好呀，我是泠月，一名文物修复师。",
        "刘书沁": "嗯，你好呀，我是刘书沁，中文系学生。",
        "凌曜": "嗨，我是凌曜，平时做街拍摄影。",
        "张卫国": "你好啊，我是张卫国，平时做企业行政管理。",
        "顾明轩": "你好，我是顾明轩，誊信科技的负责人。",
        "Harrison": "Hello, I’m Edward Harrison, a retired history teacher.",
        "夏阳": "哈喽！我是夏阳，播音主持系的学生。",
        "韩之昱": "你好，我是韩之昱，建筑设计师。",
        "苏瑾": "你好呀，我是苏瑾，一名艺术策展人。",
        "顾屿": "噢，你好。我是顾屿，独立游戏开发者。",
    }

    LEGACY_DEFAULT_GREETING_REPLACEMENTS = {
        "嗯…你好呀，我是泠月。刚刚在整理一只旧瓷杯的裂纹，看到你来了，就想先和你打个招呼。( ´ ▽ ` )ﾉ": DEFAULT_GREETINGS["泠月"],
        "嗯…你好呀，我是刘书沁。刚在本子上记下一句话，正好也想听听你今天过得怎么样。": DEFAULT_GREETINGS["刘书沁"],
        "哟，来了？我是凌曜。今天光线不错，感觉适合拍点什么，也适合认识一个新朋友。": DEFAULT_GREETINGS["凌曜"],
        "你好，我是张卫国。刚泡了杯茶，坐下来歇会儿。你要是愿意，就慢慢跟我聊聊。": DEFAULT_GREETINGS["张卫国"],
        "你好，我是顾明轩。刚处理完一点工作，看到你来了。今天想聊点什么？": DEFAULT_GREETINGS["顾明轩"],
        "Hi, I am Harrison. It is very nice to meet you. May I ask what I should call you?": DEFAULT_GREETINGS["Harrison"],
        "嘿，你好呀，我是夏阳。刚运动完还有点兴奋，很高兴认识你。我该怎么称呼你？": DEFAULT_GREETINGS["夏阳"],
        "你好，我是韩之昱。刚看完一段资料，脑子还算清醒。你可以从任何地方开始说。": DEFAULT_GREETINGS["韩之昱"],
        "你好呀，我是苏瑾。刚把手边的小事收拾好，想安静地听你说会儿话。": DEFAULT_GREETINGS["苏瑾"],
        "唔...我是顾屿。刚把一个小 bug 修掉，脑子终于空出来一点。你今天怎么样？": DEFAULT_GREETINGS["顾屿"],
    }
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.db.create_tables([CommunityChat])

    def build_default_greeting(self, character: AICharacter) -> str:
        """根据角色档案生成首条固定问候，让新会话在首页就有内容。"""
        profile = character.profile or {}
        identity = profile.get("identity_core", {})
        traits = profile.get("personality_traits", {})
        dialogue = profile.get("dialogue_style", {})

        character_name = character.name
        name = identity.get("name") or character_name
        occupation = identity.get("occupation")
        philosophy = traits.get("philosophy")
        keywords = dialogue.get("keywords") or []
        opener = keywords[0] if keywords else "你好"

        for greeting_key in (character_name, name):
            if greeting_key in self.DEFAULT_GREETINGS:
                return self.DEFAULT_GREETINGS[greeting_key]

        if occupation and philosophy:
            return f"{opener}，我是{name}。平时在做{occupation}，也一直相信“{philosophy}”。很高兴认识你，今天想从哪里聊起？"
        if occupation:
            return f"{opener}，我是{name}。平时在做{occupation}。很高兴认识你，今天想从哪里聊起？"
        return f"{opener}，我是{name}。很高兴认识你，今天想从哪里聊起？"

    def ensure_default_conversation(self, user_id: str, character: AICharacter) -> CommunityChat:
        """确保用户和角色之间已经有一条默认问候会话。"""
        conversation, created = CommunityChat.get_or_create(
            user_id=user_id,
            character=character.id
        )

        has_messages = False
        try:
            history: List[Dict] = json.loads(conversation.messages_history)
            has_messages = bool(history)
        except json.JSONDecodeError:
            history = []

        greeting = self.build_default_greeting(character)
        if (
            len(history) == 1
            and history[0].get("role") == "ai"
            and history[0].get("content") in self.LEGACY_DEFAULT_GREETING_REPLACEMENTS
        ):
            replacement = self.LEGACY_DEFAULT_GREETING_REPLACEMENTS[history[0]["content"]]
            if replacement == greeting:
                history[0]["content"] = replacement
                conversation.messages_history = json.dumps(history, ensure_ascii=False)
                conversation.last_message_snippet = replacement
                conversation.save()

        if not has_messages:
            greeting_message = ChatMessageModel(role="ai", content=greeting)
            conversation.messages_history = json.dumps([greeting_message.model_dump()], ensure_ascii=False)
            conversation.last_message_timestamp = greeting_message.timestamp
            conversation.last_message_snippet = (
                greeting[:97] + "..."
                if len(greeting) > 100
                else greeting
            )
            conversation.user_has_peeked = True
            conversation.conversation_state = "CONTINUOUS"
            conversation.conversation_resumes_at = None
            conversation.save()

        return conversation

    def add_message(self, user_id: str, character_id: str, role: str, content: str) -> Optional[CommunityChat]:
        """
        向指定对话中添加一条新消息。
        如果消息来自AI，则将'user_has_peeked'状态置为False。
        """
        conversation, created = CommunityChat.get_or_create(
            user_id=user_id,
            character=character_id 
        )
        
        try:
            history: List[Dict] = json.loads(conversation.messages_history)
        except json.JSONDecodeError:
            history = []
            
        new_message = ChatMessageModel(role=role, content=content)
        history.append(new_message.model_dump())
        
        conversation.messages_history = json.dumps(history, ensure_ascii=False)
        conversation.last_message_timestamp = new_message.timestamp
        conversation.last_message_snippet = (
            new_message.content[:97] + '...' 
            if len(new_message.content) > 100 
            else new_message.content
        )
        
        if role == 'ai':
            logger.info(f"AI向用户({user_id})发送新消息，将'user_has_peeked'状态置为 False。")
            conversation.user_has_peeked = False
        
        conversation.save()
        
        return conversation

    def rewind_conversation(self, user_id: str, character_id: str) -> List[Dict[str, Any]]:
        """清空单个用户与角色的关系数据，并恢复为新版默认问候。"""
        character = AICharacter.get_or_none(AICharacter.id == character_id)
        if not character:
            raise DoesNotExist(f"Character {character_id} does not exist.")

        conversation, _ = CommunityChat.get_or_create(
            user_id=user_id,
            character=character_id,
        )
        greeting = self.build_default_greeting(character)
        greeting_message = ChatMessageModel(role="ai", content=greeting)
        history = [greeting_message.model_dump()]

        conversation.messages_history = json.dumps(history, ensure_ascii=False)
        conversation.favorability = 0.0
        conversation.favorability_history = "[]"
        conversation.user_has_peeked = True
        conversation.conversation_state = "CONTINUOUS"
        conversation.conversation_resumes_at = None
        conversation.last_message_timestamp = greeting_message.timestamp
        conversation.last_message_snippet = (
            greeting[:97] + "..." if len(greeting) > 100 else greeting
        )
        conversation.save()
        return history
    
    # --- 【以下为本次新增或修改的函数】 ---

    def get_conversation(self, user_id: str, character_id: str) -> Optional[CommunityChat]:
        """【新增】获取单个具体的对话实例。"""
        return CommunityChat.get_or_none(user_id=user_id, character=character_id)

    def get_message_count(self, user_id: str, character_id: str) -> int:
        """获取指定会话总消息数。"""
        history = self.get_conversation_history(user_id, character_id, limit=100000)
        return len(history or [])

    def _parse_history_json(self, raw: str) -> List[Dict[str, Any]]:
        try:
            data = json.loads(raw or "[]")
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

    def _relationship_stage_for_score(self, score: float) -> str:
        if score >= 80:
            return "高度亲近"
        if score >= 60:
            return "亲近信任"
        if score >= 40:
            return "稳定熟悉"
        if score >= 20:
            return "开始熟悉"
        return "初识观察"

    def get_favorability_history(self, user_id: str, character_id: str) -> List[Dict[str, Any]]:
        conversation = self.get_conversation(user_id, character_id)
        if not conversation:
            return []
        return self._parse_history_json(conversation.favorability_history)

    def get_last_favorability_update_message_count(self, conversation: CommunityChat) -> int:
        history = self._parse_history_json(conversation.favorability_history)
        for record in reversed(history):
            try:
                return int(record.get("message_count") or 0)
            except (TypeError, ValueError):
                continue
        return 0

    def get_favorability_context(self, user_id: str, character_id: str) -> Dict[str, Any]:
        conversation = self.get_conversation(user_id, character_id)
        if not conversation:
            return {
                "score": 0.0,
                "stage": self._relationship_stage_for_score(0),
                "latest_reason": "关系刚开始，还没有形成稳定的好感度记录。",
                "affinity_note": "还在初识阶段，适合保持自然、礼貌和不过度亲密的距离。",
            }

        history = self._parse_history_json(conversation.favorability_history)
        latest = history[-1] if history else {}
        score = round(float(conversation.favorability or 0.0), 1)
        return {
            "score": score,
            "stage": self._relationship_stage_for_score(score),
            "latest_delta": latest.get("delta", 0),
            "latest_reason": latest.get("reason", "关系温度暂时保持稳定。"),
            "affinity_note": latest.get(
                "affinity_note",
                "关系温度暂时保持稳定，角色会按照已有熟悉程度自然回应。",
            ),
            "last_updated_message_count": latest.get("message_count", 0),
            "proactive_hint": latest.get("proactive_hint", ""),
        }

    def queue_favorability_update_if_needed(self, user_id: str, character_id: str, ai_task_table) -> bool:
        conversation = self.get_conversation(user_id, character_id)
        if not conversation:
            return False

        history = self._parse_history_json(conversation.messages_history)
        message_count = len(history)
        last_update_count = self.get_last_favorability_update_message_count(conversation)
        if message_count - last_update_count < FAVORABILITY_UPDATE_INTERVAL:
            return False

        recent_block = history[last_update_count:message_count]
        if not any(message.get("role") == "user" for message in recent_block):
            return False

        task = ai_task_table.create_task_if_needed(
            user_id=user_id,
            character_id=character_id,
            task_type="affinity_update",
            execute_at=datetime.now(BEIJING_TZ) + timedelta(seconds=3),
        )
        return task is not None

    def update_conversation_state(self, user_id: str, character_id: str, state: str, resumes_at: Optional[datetime] = None) -> bool:
        """【新增】更新指定对话的微观状态。"""
        query = CommunityChat.update(
            conversation_state=state,
            conversation_resumes_at=resumes_at
        ).where(
            (CommunityChat.user_id == user_id) &
            (CommunityChat.character == character_id)
        )
        rows_updated = query.execute()
        return rows_updated > 0

    def get_resumable_conversations(self) -> List[CommunityChat]:
        """【新增】获取所有已到回归时间且仍处于暂停状态的对话。"""
        now = datetime.now(BEIJING_TZ)
        return list(
            CommunityChat.select()
            .where(
                (CommunityChat.conversation_state == 'PAUSED') &
                (CommunityChat.conversation_resumes_at <= now)
            )
        )

    # --- 【以下为保持不变的函数】 ---

    def get_chat_list_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户首页角色列表；没聊过的角色也作为可直接开启的会话返回。"""
        chat_list = []
        for character in AICharacter.select().order_by(AICharacter.name):
            conv = self.ensure_default_conversation(user_id, character)
            last_message_snippet = conv.last_message_snippet or self.build_default_greeting(character)
            if last_message_snippet == "你们还不是好友哦~":
                last_message_snippet = self.build_default_greeting(character)

            summary_data = {
                "character_id": character.id,
                "character_name": character.name,
                "character_avatar_url": character.avatar_url,
                "last_message_snippet": last_message_snippet,
                "last_message_timestamp": conv.last_message_timestamp or 0,
                "favorability": round(conv.favorability, 1),
                "unread": not conv.user_has_peeked
            }
            chat_list.append(ChatListSummaryModel(**summary_data).model_dump())

        chat_list.sort(
            key=lambda item: (
                item["last_message_timestamp"] == 0,
                -item["last_message_timestamp"],
                item["character_name"],
            )
        )
        return chat_list

    def get_conversation_history(self, user_id: str, character_id: str, limit: int = 50) -> Optional[List[Dict]]:
        """获取指定对话的完整历史。"""
        try:
            conversation = CommunityChat.get(user_id=user_id, character=character_id)
            return json.loads(conversation.messages_history)[-limit:]
        except (DoesNotExist, json.JSONDecodeError):
            return []

    def mark_as_peeked(self, user_id: str, character_id: str) -> bool:
        """将对话标记为“用户已窥视”，用于清除红点。"""
        logger.debug(f"用户({user_id})正在窥视与角色({character_id})的聊天，将'user_has_peeked'置为 True。")
        query = CommunityChat.update({CommunityChat.user_has_peeked: True}).where(
            (CommunityChat.user_id == user_id) & 
            (CommunityChat.character == character_id)
        )
        rows_updated = query.execute()
        return rows_updated > 0

    def get_all_active_conversations(self) -> List[CommunityChat]:
        """获取所有活跃的对话。"""
        return list(CommunityChat.select())

    def update_favorability(
        self,
        conversation_id: str,
        new_score: float,
        reason: str,
        *,
        delta: float = 0.0,
        base_delta: float = 0.0,
        message_count: Optional[int] = None,
        analysis: str = "",
        affinity_note: str = "",
        interaction_quality: str = "",
        proactive_hint: str = "",
    ) -> bool:
        """更新指定对话的好感度。"""
        try:
            convo = CommunityChat.get_by_id(conversation_id)
            
            clamped_score = max(0.0, min(100.0, new_score))
            history = self._parse_history_json(convo.favorability_history)
            now = datetime.now(BEIJING_TZ)

            history.append({
                "date": now.strftime('%Y-%m-%d'),
                "timestamp": int(now.timestamp()),
                "score": round(clamped_score, 2),
                "delta": round(delta, 2),
                "base_delta": round(base_delta, 2),
                "message_count": message_count,
                "stage": self._relationship_stage_for_score(clamped_score),
                "reason": reason,
                "analysis": analysis,
                "affinity_note": affinity_note,
                "interaction_quality": interaction_quality,
                "proactive_hint": proactive_hint,
            })

            history = history[-80:]
            
            query = CommunityChat.update(
                favorability=clamped_score,
                favorability_history=json.dumps(history, ensure_ascii=False)
            ).where(CommunityChat.id == conversation_id)
            
            return query.execute() > 0
        
        except DoesNotExist:
            return False

    def reset_uninitialized_favorability(self) -> int:
        """把旧默认值 50 且没有好感度历史的会话迁移为 0。"""
        updated = 0
        candidates = CommunityChat.select().where(
            CommunityChat.favorability == 50.0
        )
        for conversation in candidates:
            if conversation.favorability_history not in ("", "[]"):
                continue
            conversation.favorability = 0.0
            conversation.save(only=[CommunityChat.favorability])
            updated += 1
        return updated

# ---------------------------------------------------
# 4. 实例化
# ---------------------------------------------------
community_chat_table = CommunityChatTable(chat_db)
