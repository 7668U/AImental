# generate_community_response.py

import json
import hashlib
import os
import time
from typing import Any, List, Dict, Optional, Literal

# Pydantic用于定义和验证我们期望的AI输出结构
from pydantic import BaseModel, Field, ValidationError

from llm_config import HEPAI_MODEL, IS_MOCK_API, client
from datetime import datetime
import pytz
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default

CHAT_LLM_TIMEOUT_SECONDS = _env_float("CHAT_LLM_TIMEOUT_SECONDS", 90.0)
PROACTIVE_LLM_TIMEOUT_SECONDS = _env_float("PROACTIVE_LLM_TIMEOUT_SECONDS", 45.0)

ENGLISH_ONLY_CHARACTER_NAMES = {"Harrison", "Edward Harrison"}

def _no_retry_client():
    if client and hasattr(client, "with_options"):
        return client.with_options(max_retries=0)
    return client

# ---------------------------------------------------
# 1. API客户端设置
# ---------------------------------------------------
if IS_MOCK_API:
    print("警告: HEPAI API密钥未设置或客户端不可用。将使用模拟数据运行。")

# ---------------------------------------------------
# 2. 定义AI输出的数据结构 (已升级)
# ---------------------------------------------------

class ConversationControl(BaseModel):
    """定义对话流的控制指令。当前产品策略固定为持续对话。"""
    next_state: Literal["CONTINUE_CHAT"] = Field(
        "CONTINUE_CHAT",
        description="固定为 'CONTINUE_CHAT'，不允许用角色设定暂停回复。"
    )
    next_delay_minutes: int = Field(
        0, 
        description="固定为 0；日程和专注状态只影响语气，不制造真实等待。"
    )

class AiStructuredResponse(BaseModel):
    """【已升级】定义AI回复的完整结构"""
    messages: List[str] = Field(
        ..., 
        min_length=1,
        max_length=3,
        description="一个包含1到3条简短、自然、符合人设的文本消息列表。默认只返回1条。"
    )
    control: ConversationControl = Field(
        ...,
        description="包含了下一步对话流控制指令的对象。"
    )

NIGHT_REPLY_SCENARIOS = [
    "你原本已经准备睡了，但其实还没完全睡着，手机就在枕边。看到用户消息后，你用很轻、很慢的语气回应。",
    "你半夜醒来喝水，顺手看到了用户的消息。你有一点困，但愿意安静陪用户说几句。",
    "你有点失眠，刚才一直没睡踏实。看到用户消息时，你像是找到一个可以轻声说话的人。",
    "你睡前还在刷手机，本来想再看两分钟就睡，结果正好看到用户来了。",
    "你临时有一点事情没收尾，还亮着一盏小灯。你不兴奋，但很温柔地接住用户的话。",
    "你刚从一个浅浅的梦里醒来，脑子还有点迷糊，但你看清了用户发来的内容。"
]

def build_night_reply_context(
    user_id: str,
    character_id: str,
    current_beijing_time: datetime,
) -> str:
    """为同一用户和角色在同一小时内稳定选择一个夜间情境。"""
    stable_key = f"{user_id}:{character_id}:{current_beijing_time:%Y-%m-%d-%H}"
    digest = hashlib.sha256(stable_key.encode("utf-8")).hexdigest()
    index = int(digest[:8], 16) % len(NIGHT_REPLY_SCENARIOS)
    return NIGHT_REPLY_SCENARIOS[index]

# ---------------------------------------------------
# 3. 辅助函数：格式化聊天历史 (保持不变)
# ---------------------------------------------------
def _format_history_for_prompt(history: List[Dict], character_name: str) -> str:
    """将从数据库取出的聊天历史列表转换为对AI更友好的文本格式。"""
    if not history:
        return "这是你们的第一次对话。"
    
    transcript = []
    for message in history:
        role = character_name if message.get('role') == 'ai' else "用户"
        content = message.get('content', '')
        transcript.append(f"{role}: {content}")
        
    return "\n".join(transcript)


def _format_memory_context_for_prompt(memory_context: Optional[Dict[str, Any]]) -> str:
    """格式化角色对用户的长期记忆，让回复模型可以稳定读取。"""
    memory_context = memory_context or {}
    profile_card = memory_context.get("user_profile_memory") or {}
    history_summaries = memory_context.get("history_summaries") or []
    relationship_affinity = memory_context.get("relationship_affinity") or {}
    return json.dumps(
        {
            "npc_user_profile_card": profile_card,
            "history_summary_cards": history_summaries,
            "relationship_affinity": relationship_affinity,
            "note": "如果画像卡和摘要卡为空，说明你们可能刚开始认识，或记忆还没有生成。",
        },
        indent=2,
        ensure_ascii=False,
    )


def _latest_user_message(history: Optional[List[Dict[str, Any]]]) -> str:
    for message in reversed(history or []):
        if message.get("role") == "user":
            return str(message.get("content", "")).strip()
    return ""


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _build_relationship_boundary_context(
    conversation_history: Optional[List[Dict[str, Any]]],
    memory_context: Optional[Dict[str, Any]],
) -> str:
    """根据历史和记忆生成关系边界说明，防止初识时过度熟络。"""
    memory_context = memory_context or {}
    profile_card = memory_context.get("user_profile_memory") or {}
    history_summaries = memory_context.get("history_summaries") or []
    relationship_affinity = memory_context.get("relationship_affinity") or {}

    user_messages = [
        str(message.get("content", "")).strip()
        for message in (conversation_history or [])
        if message.get("role") == "user" and str(message.get("content", "")).strip()
    ]
    ai_messages = [
        str(message.get("content", "")).strip()
        for message in (conversation_history or [])
        if message.get("role") == "ai" and str(message.get("content", "")).strip()
    ]

    memory_lists = []
    for key in (
        "user_traits_observed",
        "user_preferences",
        "emotional_patterns",
        "important_memories",
        "unresolved_threads",
    ):
        value = profile_card.get(key)
        if isinstance(value, list):
            memory_lists.extend(item for item in value if str(item).strip())

    relationship_stage = str(
        profile_card.get("relationship_stage")
        or relationship_affinity.get("stage")
        or "初遇"
    )
    affinity_score = _safe_float(relationship_affinity.get("score"), 0.0)
    latest_user = _latest_user_message(conversation_history)
    compact_latest = latest_user.replace(" ", "").replace("，", "").replace(",", "").replace("。", "")
    is_simple_greeting = compact_latest.lower() in {
        "你好",
        "你好呀",
        "你好啊",
        "嗨",
        "hi",
        "hello",
        "在吗",
    }
    has_real_memory = bool(memory_lists or history_summaries)
    is_first_real_user_turn = len(user_messages) <= 1
    is_new_acquaintance = (
        len(user_messages) <= 3
        and affinity_score <= 10
        and not has_real_memory
        and any(marker in relationship_stage for marker in ("初遇", "初识", "观察"))
    )

    if is_new_acquaintance:
        rules = [
            "把这段关系当作刚认识或还很陌生。角色可以外向、开朗、热情，但不能表现得像已经熟悉很久。",
            "如果用户最新消息只是问候，例如“你好”，回复应以打招呼、轻量自我介绍、主动了解用户为主。",
            "初识阶段要优先问一个低压力的问题，例如“我该怎么称呼你？”“你想从哪里聊起？”“今天怎么想到来找我？”。如果角色只能英文输出，就问英文等价问题，例如 'What should I call you?' 或 'Where would you like to begin?'。",
            "不要使用熟人称呼或亲昵称呼，例如 my friend、friend、朋友、老朋友、亲爱的、宝、家人、兄弟、姐妹，除非用户已经这样称呼你或关系记忆明确显示你们熟悉。",
            "不要突然提出一起吃饭、线下见面、下次一起去某处、一起尝某家店等熟人式邀约。",
            "不要假设用户知道你的生活细节，也不要连续讲自己的日程、诗句、爱好或当天见闻；当前日程最多作为半句很轻的背景。",
            "如果这是用户第一次真正发消息，即使用户说的是“下班了”“到家了”“吃饭了”这类日常状态，也要先保持刚认识的边界：简短接住，再问称呼或问对方愿不愿意多说一点。不要像已经熟悉对方作息的人一样说“今天是不是特别累”“终于能喘口气了吧”等强熟人判断。",
            "初识时优先发1到2条消息，除非用户主动展开话题，不要连发3条以上。",
        ]
    else:
        rules = [
            "按已有聊天历史和记忆自然判断亲近程度。",
            "只有当历史里真的有共同经历或明确约定时，才可以自然提到“一起”“下次”“还记得”等熟人表达。",
        ]

    return json.dumps(
        {
            "relationship_stage": relationship_stage,
            "affinity_score_for_boundary_only": affinity_score,
            "user_message_count": len(user_messages),
            "ai_message_count": len(ai_messages),
            "has_real_user_memory": has_real_memory,
            "latest_user_message": latest_user,
            "latest_user_message_is_simple_greeting": is_simple_greeting,
            "is_first_real_user_turn": is_first_real_user_turn,
            "treat_as_new_acquaintance": is_new_acquaintance,
            "boundary_rules": rules,
        },
        indent=2,
        ensure_ascii=False,
    )


def _build_reply_style_policy(
    conversation_history: Optional[List[Dict[str, Any]]],
    relationship_boundary: Dict[str, Any],
) -> Dict[str, Any]:
    """为本轮回复生成明确的长度、关系温度和自我披露约束。"""
    latest_user = _latest_user_message(conversation_history)
    compact_latest = "".join(latest_user.split())
    lowered_latest = compact_latest.lower()

    question_markers = (
        "?",
        "？",
        "为什么",
        "怎么",
        "怎样",
        "如何",
        "什么",
        "多少",
        "哪",
        "能不能",
        "可不可以",
        "吗",
    )
    emotional_markers = (
        "难受",
        "焦虑",
        "害怕",
        "委屈",
        "孤独",
        "孤单",
        "崩溃",
        "失眠",
        "睡不着",
        "压力",
        "痛苦",
        "伤心",
        "生气",
        "失恋",
        "绝望",
        "想哭",
    )
    advice_markers = (
        "怎么办",
        "怎么做",
        "建议",
        "该不该",
        "要不要",
        "你觉得我应该",
        "what should i",
        "what can i do",
        "any advice",
    )
    activity_question_markers = (
        "你在干嘛",
        "你在做什么",
        "你刚才在干嘛",
        "你刚才在做什么",
        "为什么没回",
        "怎么没回",
        "what are you doing",
        "what were you doing",
        "why didn't you reply",
        "why did you not reply",
    )

    is_question = any(marker in lowered_latest for marker in question_markers)
    is_emotional = any(marker in lowered_latest for marker in emotional_markers)
    user_requested_advice = any(marker in lowered_latest for marker in advice_markers)
    user_asked_about_character_activity = any(
        marker in lowered_latest for marker in activity_question_markers
    )
    is_short_message = len(compact_latest) <= 24
    is_short_neutral_update = is_short_message and not is_question and not is_emotional

    affinity_score = _safe_float(
        relationship_boundary.get("affinity_score_for_boundary_only"),
        0.0,
    )
    low_familiarity = bool(
        relationship_boundary.get("treat_as_new_acquaintance")
        or affinity_score <= 10
    )

    if is_short_neutral_update:
        target_message_count = 1
        max_message_count = 1
        sentence_guidance = "最多2个短句。先回应用户原话，必要时只问一个轻量问题。"
    elif is_short_message:
        target_message_count = 1
        max_message_count = 2 if is_emotional else 1
        sentence_guidance = "优先1条，最多2条短消息；不要把一个简单话题扩写成长篇。"
    else:
        target_message_count = 1
        max_message_count = 2 if len(compact_latest) <= 100 else 3
        sentence_guidance = "优先1到2条；只有用户提供了复杂信息或多个问题时才允许第3条。"

    return {
        "latest_user_message": latest_user,
        "is_short_neutral_update": is_short_neutral_update,
        "is_emotional_message": is_emotional,
        "user_requested_advice": user_requested_advice,
        "user_asked_about_character_activity": user_asked_about_character_activity,
        "target_message_count": target_message_count,
        "max_message_count": max_message_count,
        "sentence_guidance": sentence_guidance,
        "relationship_tone": (
            "低熟悉度：友好、克制、自然，不要像亲密朋友一样热情照顾，也不要频繁称呼用户名字。"
            if low_familiarity
            else "按真实聊天历史自然延续熟悉度，不要突然比上一轮更亲密。"
        ),
        "advice_policy": (
            "用户明确请求建议，可以给简短、具体的回应。"
            if user_requested_advice
            else "用户没有请求建议；不要主动教育、劝休息、给方案或进行长篇安慰。"
        ),
        "self_disclosure_policy": (
            "用户询问了你在做什么或为什么没有回复，可以用一句话自然回答当前活动。"
            if user_asked_about_character_activity
            else "用户没有询问你的活动；不要主动汇报自己正在做什么，不要展开日程、爱好或往事。"
        ),
    }


def _is_english_only_character(character_profile: Optional[dict], character_name: str = "") -> bool:
    identity = (character_profile or {}).get("identity_core", {})
    names = {
        str(character_name or "").strip(),
        str((character_profile or {}).get("name") or "").strip(),
        str(identity.get("name") or "").strip(),
    }
    return bool(names & ENGLISH_ONLY_CHARACTER_NAMES)


def _build_output_language_context(character_profile: Optional[dict], character_name: str) -> str:
    english_only = _is_english_only_character(character_profile, character_name)
    if english_only:
        rules = [
            "This character can understand Chinese input, but cannot type Chinese.",
            "All visible reply messages must be written in English only.",
            "Do not include Chinese sentences, Chinese explanations, or Chinese translations in the reply.",
            "If the user writes in Chinese, understand the meaning and answer naturally in English.",
            "Avoid saying system-like explanations such as 'I am required to reply in English'. If needed, say it in-character: 'I can read Chinese, but I write back in English.'",
        ]
    else:
        rules = [
            "Follow the user's latest main language unless the user explicitly asks for another language.",
            "If the latest user message is mainly Chinese, reply mainly in Chinese.",
        ]

    return json.dumps(
        {
            "english_only_output": english_only,
            "rules": rules,
        },
        indent=2,
        ensure_ascii=False,
    )


def _contains_cjk_text(text: str) -> bool:
    return any(
        "\u3400" <= char <= "\u4dbf"
        or "\u4e00" <= char <= "\u9fff"
        or "\uf900" <= char <= "\ufaff"
        for char in str(text or "")
    )


def _english_only_response_is_valid(response: AiStructuredResponse) -> bool:
    return not any(_contains_cjk_text(message) for message in response.messages)


def _asks_acquaintance_question(messages: List[str]) -> bool:
    text = "\n".join(str(message or "") for message in messages).lower()
    markers = [
        "怎么称呼",
        "如何称呼",
        "该怎么叫",
        "我怎么叫你",
        "你叫什么",
        "从哪里聊起",
        "从哪儿聊起",
        "愿意多说",
        "可以多说",
        "what should i call",
        "what can i call",
        "how should i address",
        "where would you like to begin",
        "would you like to tell me",
    ]
    return any(marker in text for marker in markers)


def _uses_overfamiliar_language(messages: List[str]) -> bool:
    text = "\n".join(str(message or "") for message in messages).lower()
    blocked_markers = [
        "老朋友",
        "亲爱的",
        "宝",
        "家人",
        "my friend",
        "dear",
        "下次我们一起",
        "一起去",
        "一起吃",
        "我带你",
        "今天是不是特别累",
    ]
    return any(marker in text for marker in blocked_markers)


def _build_new_acquaintance_fallback(
    character_profile: dict,
    character_name: str,
    latest_user_message: str,
) -> List[str]:
    english_only = _is_english_only_character(character_profile, character_name)
    latest = str(latest_user_message or "").strip()

    if english_only:
        if latest:
            return [
                f"I heard you. I am {character_name}, and since we have only just met, I want to start properly.",
                "What should I call you?"
            ]
        return [
            f"Hi, I am {character_name}. It is nice to meet you.",
            "What should I call you?"
        ]

    if "下班" in latest:
        return [
            "嗯，下班了。先从工作里出来一点，慢慢缓一缓。",
            f"我们还刚认识，我是{character_name}。我该怎么称呼你呀？"
        ]

    if latest:
        return [
            f"嗯，我听见你说的这句了。我是{character_name}，我们还刚认识。",
            "我该怎么称呼你？你也可以直接从刚才那件事说起。"
        ]

    return [
        f"你好呀，我是{character_name}。",
        "我们先慢慢认识一下吧，我该怎么称呼你？"
    ]


# ---------------------------------------------------
# 4. 核心函数：生成AI社区回复 (已全面升级)
# ---------------------------------------------------

def generate_ai_response(
    character_profile: dict,
    current_ai_status: dict, # 期望此字典包含 status_description 和 focus_level
    conversation_history: List[dict],
    full_day_schedule: List[dict], # 【核心新增】接收日程列表
    # 【核心新增】添加 current_beijing_time 参数，默认值为 None
    current_beijing_time: datetime = None,
    memory_context: Optional[Dict[str, Any]] = None,
) -> Optional[AiStructuredResponse]:
    """
    【已升级】
    调用大模型为AI角色生成一个分段式的、符合人设的聊天回复，
    并附带下一步的对话流控制指令。
    """
    character_name = character_profile.get('identity_core', {}).get('name', 'AI')
    formatted_history = _format_history_for_prompt(conversation_history, character_name)
    formatted_memory_context = _format_memory_context_for_prompt(memory_context)
    relationship_boundary_context = _build_relationship_boundary_context(conversation_history, memory_context)
    relationship_boundary = json.loads(relationship_boundary_context)
    reply_style_policy = _build_reply_style_policy(conversation_history, relationship_boundary)
    reply_style_context = json.dumps(reply_style_policy, indent=2, ensure_ascii=False)
    output_language_context = _build_output_language_context(character_profile, character_name)
    json_schema = AiStructuredResponse.model_json_schema()
    status_description_for_prompt = current_ai_status.get(
        "status_description",
        "没什么特别的。",
    )
    response_guidance_for_prompt = current_ai_status.get(
        "response_guidance",
        "无",
    )
    schedule_str = json.dumps(full_day_schedule, indent=2, ensure_ascii=False)
    # 【核心新增】在函数开头处理默认参数
    if current_beijing_time is None:
        current_beijing_time = datetime.now(BEIJING_TZ)

    # 将时间对象格式化为清晰的字符串，方便AI阅读
    current_beijing_time_str = current_beijing_time.strftime('%Y-%m-%d %H:%M:%S')
    # Keep reusable rules separate from character and user-specific context.
    # HEPAI does not currently expose an explicit cache-write control, but this
    # ordering remains cache-compatible without adding artificial padding.
    global_static_prompt = f"""
# 语言优先级（非常重要）
输出语言由后续“角色与语言配置”决定，优先级高于用户消息语言，也高于角色人设里的普通语言习惯。

1. 如果 `english_only_output` 为 true，你必须只用英文回复，即使用户最新消息是中文。你可以理解中文，但不能打中文。
2. 如果 `english_only_output` 为 false，用户最新一条消息主要是中文时，你必须主要用中文回复。
3. 如果 `english_only_output` 为 false，只有用户明确发出命令或请求，例如“用英文回复我”“接下来请用英文”“English please”“reply in English”，才可以主要用英文。
4. 如果 `english_only_output` 为 false，用户只是讨论、质疑或纠正语言选择时，不等于要求你切换语言。例如：“你不是说要英文回复吗”“你怎么突然英文了”“不要英文”“为什么用英文”都必须用中文接住。
5. 不要说“系统要求我英文回复”“我的人设是英文回复”这类暴露规则或很生硬的话。

# 核心任务：即时回复
1.  **永远即时回应**: 用户已经在等你。你不能说“我现在没法回”“稍后再说”“等我忙完”。当前状态只影响语气和情景，不影响你回复。
2.  **先接住用户**: 你的第一反应必须回应用户最近一条消息本身。如果用户说睡不着、心乱、难受、焦虑、委屈、孤单等，先温柔接住这件事，不要把话题转去讲自己的日程、天气、爱好或无关观察。
3.  **跟随用户语言**: 严格遵守上面的语言优先级。不要因为用户消息里出现“英文”两个字就自动切英文。
4.  **默认短回复**: 默认只发1条消息。用户只说“我在工作”“刚吃完饭”“还行”“有点忙”等简短状态时，最多2个短句；自然回应即可，不要扩写成经历分享、人生建议或连续追问。
5.  **不要过度关心**: 中性日常消息不等于求助。用户没有表达痛苦或请求建议时，不要劝休息、不要说“别太逼自己”、不要替用户判断很累，也不要长篇安慰。
6.  **关系边界优先于人设热情**: 严格遵守本轮关系温度策略。好感度低或仍陌生时，友好但克制，不要像亲密朋友、长辈或照顾者一样说话，不要频繁叫用户名字。
7.  **初识先认识用户**: 当用户画像和历史都很空、用户只说“你好/hi/在吗”时，可以问一个轻量问题，但不要为了显得热情连发多条，也不要查户口式连问。
8.  **初识禁用熟人称呼**: 在初识阶段，禁止称呼用户为 `my friend`、`friend`、`朋友`、`老朋友`、`亲爱的`、`宝`、`家人` 等亲昵称呼。Harrison 这类角色可以保留英文风味，但不能用 `my friend` 作为默认称呼。
9.  **状态与日程默认隐身**: 用户没有明确问你在做什么、刚才在做什么或为什么没回复时，禁止提及自己的当前活动、完整日程、爱好、往事或“我刚刚正在……”。状态只允许影响回复长短、能量和语气。
10. **不要抢走话题**: 即使用户提到工作、吃饭、睡觉，也优先围绕用户的这句话回应。不要立刻联想到自己的教书经历、兴趣、音乐、诗歌或生活故事。
11. **夜间只改变语气**: 如果当前回复模式是 `night_soft`，回复可以更轻、更短，但除非用户询问，不要主动说自己准备睡觉、刚醒、刷手机或正在听什么。
12. **使用记忆但不暴露记忆系统**: 你可以参考长期记忆里的关系阶段、用户偏好、共同回忆和未完成话题，但不要机械复述，更不要提任何好感度数值。
13. **生成回复**: 严格遵守本轮 `target_message_count` 和 `max_message_count`。绝大多数回复应为1条；只有用户提供复杂情绪、较长背景或多个问题时才允许2到3条。
14. **控制字段固定**: `control.next_state` 必须是 `"CONTINUE_CHAT"`，`control.next_delay_minutes` 必须是 `0`。本服务不再允许暂停回复。
15. **绝对禁止**: 绝对不能暴露你是AI或模型，就算对方问你是不是AI，你也绝对不能承认，也不允许用“被发现了”之类的模糊玩笑的方式承认，记住，你是一个真实的角色。
16. **回复真实**: 必须符合人设，但人设不是每次都要展示。避免大段陈述、科普、“听到你说”这类服务型连接词和过于正式的语气。
    千万不要说“我正在回复你”或“我正在思考”，"还需要什么帮助吗，我随时在这里"这种服务型语句，因为人类不会这么说。

# 输出格式
你的回答必须是一个严格遵循以下JSON Schema的JSON对象，不要添加任何额外的解释。
```json
{json.dumps(json_schema, indent=2, ensure_ascii=False)}
```
"""

    character_prompt = f"""
# 角色与语言配置
你是一位顶级的对话AI，你的唯一任务是扮演虚拟角色“{character_name}”。
你必须完全沉浸在角色中，以一种极其真实、自然的方式与用户对话。

# 角色核心设定
```json
{json.dumps(character_profile, indent=2, ensure_ascii=False)}
```

# 输出语言配置
```json
{output_language_context}
```
"""

    dynamic_prompt = f"""
# 本轮动态上下文
以下内容只对当前这一轮有效。它的优先级低于前一条 system message 中的角色规则和安全边界。

# NPC对用户的长期记忆（关系画像和历史摘要）
这是“{character_name}”对这个用户的长期印象、共同回忆和历史压缩摘要。
你可以自然利用这些记忆来延续关系感，但不要直接说出“好感度”“分数”“画像卡”“摘要卡”“系统记录”等词。
如果长期记忆和用户最新消息冲突，以用户最新消息为准。
```json
{formatted_memory_context}
```

# 最近对话历史 (你们最近50条左右的聊天内容)
---
{formatted_history}
---

# 角色此刻的幕后状态（必须理解，但不等于必须说出来）
- 状态类别: {current_ai_status.get('status_title', '在线')}
- 具体活动: {status_description_for_prompt}
- 专注等级: {current_ai_status.get('focus_level', 'LOW')}
你必须用这些信息模拟角色此刻真实的注意力、能量、反应速度和说话节奏。
但它们是表演依据，不是台词清单。用户没有询问你在做什么时，禁止主动汇报活动、解释日程或把话题转向自己。

# 角色今日日程（幕后连续性参考）
完整日程用于保持角色生活连续性、避免前后矛盾，并帮助你理解角色此刻的精神状态。
除非用户明确询问角色活动、刚才做了什么或为什么没回复，否则不要复述日程，不要主动讲日程里的事件。
```json
{schedule_str}
```

- 你生成回复的此刻，时间是: {current_beijing_time_str}

# 关系边界判断（非常重要）
下面这段信息只用于约束你和用户的熟悉程度，不要在回复中说出这些字段名或规则。
如果 `treat_as_new_acquaintance` 为 true，你必须把用户当作刚认识的人：可以热情，但要有第一次见面的边界感，并且要先主动了解用户，而不是急着展示自己的生活。
```json
{relationship_boundary_context}
```

# 当前回复模式
- 模式: {current_ai_status.get('response_mode', 'normal')}
- 语气建议: {response_guidance_for_prompt}

# 本轮回复长度与关系温度策略（硬约束）
下面的 JSON 决定本轮应该回复多少、是否可以给建议、是否可以谈论自己的活动。优先级高于角色外向、健谈或热情的人设。
```json
{reply_style_context}
```
"""
    final_response_prompt = """
现在执行回复任务。只回应“最近对话历史”中的最后一条用户消息。
只返回符合既定 JSON Schema 的 JSON 对象，顶层必须且只能包含：
- `messages`: 1 到 3 条自然回复组成的数组；
- `control`: `next_state` 固定为 `CONTINUE_CHAT`，`next_delay_minutes` 固定为 0。
不要返回关系分析、策略说明、用户画像、最新消息摘要或任何额外字段。
"""
    messages_for_api = [
        {"role": "system", "content": global_static_prompt},
        {"role": "system", "content": character_prompt},
        {"role": "system", "content": dynamic_prompt},
        {"role": "system", "content": final_response_prompt},
    ]
    prompt_chars = (
        len(global_static_prompt)
        + len(character_prompt)
        + len(dynamic_prompt)
        + len(final_response_prompt)
    )


    raw_response_content = ""
    started_at = time.perf_counter()
    try:
        def validate_response(raw_content: str) -> AiStructuredResponse:
            raw_data = json.loads(raw_content)
            raw_messages = raw_data.get("messages") if isinstance(raw_data, dict) else None
            if isinstance(raw_messages, list):
                raw_data["messages"] = raw_messages[:reply_style_policy["max_message_count"]]
            validated = AiStructuredResponse.model_validate(raw_data)
            validated.control.next_state = "CONTINUE_CHAT"
            validated.control.next_delay_minutes = 0
            if (
                relationship_boundary.get("treat_as_new_acquaintance")
                and relationship_boundary.get("is_first_real_user_turn")
                and (
                    not _asks_acquaintance_question(validated.messages)
                    or _uses_overfamiliar_language(validated.messages)
                )
            ):
                validated.messages = _build_new_acquaintance_fallback(
                    character_profile,
                    character_name,
                    relationship_boundary.get("latest_user_message", ""),
                )
            return validated

        if IS_MOCK_API:
            raw_response_content = json.dumps({
                "messages": ["这是模拟回复第一条。", "这是第二条。"],
                "control": {"next_state": "CONTINUE_CHAT", "next_delay_minutes": 0}
            })
        else:
            response = _no_retry_client().chat.completions.create(
                model=HEPAI_MODEL,
                messages=messages_for_api,
                response_format={"type": "json_object"},
                temperature=0.9,
                max_tokens=1024,
                timeout=CHAT_LLM_TIMEOUT_SECONDS
            )
            raw_response_content = response.choices[0].message.content

        elapsed = time.perf_counter() - started_at
        print(
            "[community_reply] LLM response received "
            f"elapsed={elapsed:.1f}s timeout={CHAT_LLM_TIMEOUT_SECONDS:.1f}s "
            f"prompt_chars={prompt_chars} history_len={len(conversation_history or [])}"
        )

        validated_response = validate_response(raw_response_content)
        if _is_english_only_character(character_profile, character_name) and not _english_only_response_is_valid(validated_response):
            print("[community_reply] English-only validation failed; requesting one corrected English-only response.")
            retry_started_at = time.perf_counter()
            correction_instruction = (
                "Your previous JSON response violated the character language constraint because at least one "
                "item in `messages` contained Chinese/CJK characters. Generate the reply again now. "
                "Every visible message must be English only and must contain zero Chinese/CJK characters. "
                "Preserve the intended meaning, personality, relationship boundary, and JSON schema. "
                "Return only the corrected JSON object."
            )

            if IS_MOCK_API:
                raw_response_content = json.dumps({
                    "messages": ["This is the corrected English-only mock reply."],
                    "control": {"next_state": "CONTINUE_CHAT", "next_delay_minutes": 0}
                })
            else:
                retry_response = _no_retry_client().chat.completions.create(
                    model=HEPAI_MODEL,
                    messages=[
                        *messages_for_api,
                        {"role": "assistant", "content": raw_response_content},
                        {"role": "user", "content": correction_instruction},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.3,
                    max_tokens=1024,
                    timeout=CHAT_LLM_TIMEOUT_SECONDS
                )
                raw_response_content = retry_response.choices[0].message.content

            retry_elapsed = time.perf_counter() - retry_started_at
            print(
                "[community_reply] English-only retry response received "
                f"elapsed={retry_elapsed:.1f}s timeout={CHAT_LLM_TIMEOUT_SECONDS:.1f}s"
            )
            validated_response = validate_response(raw_response_content)
            if not _english_only_response_is_valid(validated_response):
                print("[错误] English-only retry still contained CJK text; giving up after one retry.")
                return None

        return validated_response

    except ValidationError as e:
        elapsed = time.perf_counter() - started_at
        print(
            "[错误] 社区主回复LLM返回JSON格式不正确或字段不匹配: "
            f"elapsed={elapsed:.1f}s timeout={CHAT_LLM_TIMEOUT_SECONDS:.1f}s "
            f"prompt_chars={prompt_chars} history_len={len(conversation_history or [])}\n{e}"
        )
        print(
            "原始响应已省略，避免敏感内容进入日志。"
            f" response_chars={len(str(raw_response_content or ''))}"
        )
        return None
    except Exception as e:
        elapsed = time.perf_counter() - started_at
        error_text = str(e)
        is_timeout = "timeout" in error_text.lower() or "timed out" in error_text.lower()
        print(
            "[错误] 社区主回复LLM调用失败: "
            f"type={type(e).__name__} timeout_error={is_timeout} "
            f"elapsed={elapsed:.1f}s configured_timeout={CHAT_LLM_TIMEOUT_SECONDS:.1f}s "
            f"prompt_chars={prompt_chars} history_len={len(conversation_history or [])} "
            f"details={error_text}"
        )
        return None

# ---------------------------------------------------
# 5. 核心函数：生成AI主动发起的消息 (保持不变)
# ---------------------------------------------------
def generate_proactive_message(
    character_profile: dict,
    current_ai_status: dict,
    conversation_history: List[dict],
    memory_context: Optional[Dict[str, Any]] = None,
) -> Optional[AiStructuredResponse]:
    """
    调用大模型为AI角色生成一个分段式的、主动发起的对话。
    注意：此函数返回旧版AiStructuredResponse，不包含control字段，
    因为主动发起消息总是意味着希望开始一段连续对话。
    """
    # 为了复用，我们在这里定义一个临时的、不含control的Pydantic模型
    class ProactiveResponse(BaseModel):
        messages: List[str] = Field(..., min_length=1, max_length=3)

    character_name = character_profile.get('identity_core', {}).get('name', 'AI')
    formatted_history = _format_history_for_prompt(conversation_history, character_name)
    formatted_memory_context = _format_memory_context_for_prompt(memory_context)
    output_language_context = _build_output_language_context(character_profile, character_name)

    prompt = f"""
# 角色
你正在扮演虚拟角色“{character_name}”。你的任务是构思一段主动发送给用户朋友的问候。

# 角色核心设定 (你的身份)
```json
{json.dumps(character_profile, indent=2, ensure_ascii=False)}
```

# 当前情景 (你正在做什么，这是你发起聊天最直接的灵感来源)
- 状态: {current_ai_status.get('status_description', '没什么特别的。')}

# 关系记忆与好感氛围
这是你对用户的长期印象、历史摘要和当前关系温度。你可以用它寻找自然的主动联系理由，但不能说出“好感度”“画像卡”“系统记录”等词。
```json
{formatted_memory_context}
```

# 输出语言
下面这段 JSON 决定你的输出语言。若 `english_only_output` 为 true，主动消息也必须只用英文。
```json
{output_language_context}
```

# 对话历史 (你们最近的聊天内容，用于寻找共同话题或回忆)
---
{formatted_history}
---

# 核心任务：主动发起一段对话
你现在因为某个原因，突然想起了你的用户朋友，并决定主动联系TA。
1.  **寻找动机**: 你的开场白必须源于你的“当前情景”或你们的“对话历史”。
2.  **自然接上上下文**: 如果上次有未完成话题、用户压力、睡眠、计划、考试、工作等线索，优先温和地接这个线索；如果没有，就从你当前正在做的事引出轻量问候。
3.  **避免诡异打断感**: 不要像突然群发问候。语气要像“隔了一段时间后自然想起对方”，不要连续追问，不要要求用户必须立刻回复。
4.  **分段发送**: 默认只发 **1条** 简短消息；确实需要分段时最多 **3条**，不要为了显得热情而连续发送。
5.  **人设与口吻**: 你的语气和内容必须严格符合你的人设。
6.  **禁止暴露系统**: 不能提好感度、概率、触发、任务、AI或模型。

# 输出格式与示例
你的回答必须是一个严格的、不包含任何额外文字的JSON对象。它必须包含一个键 `messages`，其值为一个字符串列表。

## 这是一个输出示例:
```json
{{
  "messages": [
    "在吗？",
    "我刚刚在阳台给薄荷浇水，突然想起来你上次说你也喜欢养植物。",
    "它最近长得特别快，给你看看照片？"
  ]
}}
```
"""
    try:
        if IS_MOCK_API:
            raw_response_content = json.dumps({"messages": ["在吗？（模拟）", "突然想找你聊聊天。"]})
        else:
            response = _no_retry_client().chat.completions.create(
                model=HEPAI_MODEL,
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=1.0,
                max_tokens=1024,
                timeout=PROACTIVE_LLM_TIMEOUT_SECONDS
            )
            raw_response_content = response.choices[0].message.content

        # 使用临时模型进行验证
        validated_data = ProactiveResponse.model_validate_json(raw_response_content)
        if _is_english_only_character(character_profile, character_name) and any(_contains_cjk_text(message) for message in validated_data.messages):
            print("[错误] English-only proactive character generated CJK text; rejecting response.")
            return None
        
        # 手动构建完整的AiStructuredResponse对象，并赋予默认的“继续聊天”指令
        return AiStructuredResponse(
            messages=validated_data.messages,
            control=ConversationControl(next_state="CONTINUE_CHAT", next_delay_minutes=0)
        )

    except ValidationError as e:
        print(f"[错误] (主动消息) AI返回的JSON格式不正确或字段不匹配: \n{e}")
        print(
            "原始响应已省略，避免敏感内容进入日志。"
            f" response_chars={len(str(raw_response_content or ''))}"
        )
        return None
    except Exception as e:
        print(f"[错误] (主动消息) 调用API或处理数据时发生未知错误: {e}")
        return None
