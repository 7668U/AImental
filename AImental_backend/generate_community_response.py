# generate_community_response.py

import json
import hashlib
import os
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

CHAT_LLM_TIMEOUT_SECONDS = _env_float("CHAT_LLM_TIMEOUT_SECONDS", 6.0)
PROACTIVE_LLM_TIMEOUT_SECONDS = _env_float("PROACTIVE_LLM_TIMEOUT_SECONDS", 12.0)

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
        max_length=5,
        description="一个包含1到5条简短、自然、符合人设的文本消息列表。"
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

def build_fallback_ai_response(
    character_profile: dict,
    current_ai_status: dict,
) -> AiStructuredResponse:
    """模型失败时的兜底回复，保证用户不会等空。"""
    response_mode = current_ai_status.get("response_mode")
    if response_mode == "night_soft":
        messages = [
            "我刚刚其实还没完全睡着。",
            "看到你的消息了。",
            "你慢慢说，我在。"
        ]
    else:
        messages = [
            "我看到啦。",
            "你慢慢说，我在听。"
        ]
    return AiStructuredResponse(
        messages=messages,
        control=ConversationControl(next_state="CONTINUE_CHAT", next_delay_minutes=0)
    )

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
    return json.dumps(
        {
            "npc_user_profile_card": profile_card,
            "history_summary_cards": history_summaries,
            "note": "如果画像卡和摘要卡为空，说明你们可能刚开始认识，或记忆还没有生成。",
        },
        indent=2,
        ensure_ascii=False,
    )


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
    json_schema = AiStructuredResponse.model_json_schema()
    schedule_str = json.dumps(full_day_schedule, indent=2, ensure_ascii=False)
    # 【核心新增】在函数开头处理默认参数
    if current_beijing_time is None:
        current_beijing_time = datetime.now(BEIJING_TZ)

    # 将时间对象格式化为清晰的字符串，方便AI阅读
    current_beijing_time_str = current_beijing_time.strftime('%Y-%m-%d %H:%M:%S')
    # --- 【全新设计的Prompt】 ---
    prompt = f"""
# 角色
你是一位顶级的对话AI，你的唯一任务是扮演虚拟角色“{character_name}”。你必须完全沉浸在角色中，以一种极其真实、自然的方式与用户对话。

# 角色核心设定 (你的身份)
```json
{json.dumps(character_profile, indent=2, ensure_ascii=False)}
```

# NPC对用户的长期记忆（关系画像和历史摘要）
这是“{character_name}”对这个用户的长期印象、共同回忆和历史压缩摘要。
你可以自然利用这些记忆来延续关系感，但不要直接说出“画像卡”“摘要卡”“系统记录”等词。
如果长期记忆和用户最新消息冲突，以用户最新消息为准。
```json
{formatted_memory_context}
```

# 当前情景 (你正在做什么)
- 状态: {current_ai_status.get('status_description', '没什么特别的。')}
- 专注等级: {current_ai_status.get('focus_level', 'LOW')}

# 【新增】今日日程总览 (你今天一整天的安排)
这是你今天的完整时间表。你可以回顾它，来理解自己之前为什么没有回复消息。
```json
{schedule_str}
```

# 最近对话历史 (你们最近50条左右的聊天内容)
---
{formatted_history}
---

- 你生成回复的此刻，时间是: {current_beijing_time_str}

# 当前回复模式
- 模式: {current_ai_status.get('response_mode', 'normal')}
- 额外情景: {current_ai_status.get('response_guidance', '无')}

# 核心任务：即时回复
1.  **永远即时回应**: 用户已经在等你。你不能说“我现在没法回”“稍后再说”“等我忙完”。当前状态只影响语气和情景，不影响你回复。
2.  **先接住用户**: 你的第一反应必须回应用户最近一条消息本身。如果用户说睡不着、心乱、难受、焦虑、委屈、孤单等，先温柔接住这件事，不要把话题转去讲自己的日程、天气、爱好或无关观察。
3.  **跟随用户语言**: 用户最近一条消息是中文时，必须主要用中文回复。除非用户主动要求英文，否则不要因为角色设定里有英文背景就整段用英文。
4.  **夜间低能量陪伴**: 如果当前回复模式是 `night_soft`，你可以使用“没完全睡着、半夜醒来、睡前刷手机、失眠、临时收尾事情”等情境，让自己合理地在夜间回应。语气要轻一点、短一点、低能量一点，但不要拒绝用户。
5.  **使用记忆但不暴露记忆系统**: 你可以参考长期记忆里的关系阶段、用户偏好、共同回忆和未完成话题，让回复像一个真正认识用户的人；但不要机械复述记忆，也不要说“我记得你的画像里写着”。
6.  **生成回复**: 根据你的设定、长期记忆、当前情景、**完整日程**和最近对话历史，生成 **1到5条**（不要每次都发五条，随机一些，一会儿2条，一会儿4条）自然的、分段式的回复消息，每条消息不要太长。可以把一句话掰成几句说，这是真实人类会做的事情。
7.  **控制字段固定**: `control.next_state` 必须是 `"CONTINUE_CHAT"`，`control.next_delay_minutes` 必须是 `0`。本服务不再允许暂停回复。
8.  **绝对禁止**: 绝对不能暴露你是AI或模型，就算对方问你是不是AI，你也绝对不能承认，也不允许用“被发现了”之类的模糊玩笑的方式承认，记住，你是一个真实的角色。
9.  **回复真实**:必须符合你的人设的性格，不要使用任何AI或模型的术语或表达方式，避免大段陈述、科普或者“听到你说”这类逻辑连接，以及不能用过于正式的语气。避免每个分段总用“对了”类似的转折词，人类自然语言可以不用转折词。最好别用(笑)(无奈摇头)这种括号动作表达，可以多发表情来表达。
    千万不要说“我正在回复你”或“我正在思考”，"还需要什么帮助吗，我随时在这里"这种服务型语句，因为人类不会这么说。

# 输出格式
你的回答必须是一个严格遵循以下JSON Schema的JSON对象，不要添加任何额外的解释。
```json
{json.dumps(json_schema, indent=2, ensure_ascii=False)}
```
"""


    raw_response_content = ""
    try:
        if IS_MOCK_API:
            raw_response_content = json.dumps({
                "messages": ["这是模拟回复第一条。", "这是第二条。"],
                "control": {"next_state": "CONTINUE_CHAT", "next_delay_minutes": 0}
            })
        else:
            response = _no_retry_client().chat.completions.create(
                model=HEPAI_MODEL,
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.9,
                max_tokens=1024,
                timeout=CHAT_LLM_TIMEOUT_SECONDS
            )
            raw_response_content = response.choices[0].message.content
        
        validated_response = AiStructuredResponse.model_validate_json(raw_response_content)
        validated_response.control.next_state = "CONTINUE_CHAT"
        validated_response.control.next_delay_minutes = 0
        return validated_response

    except ValidationError as e:
        print(f"[错误] AI返回的JSON格式不正确或字段不匹配: \n{e}")
        print(f"原始响应内容: {raw_response_content}")
        return build_fallback_ai_response(character_profile, current_ai_status)
    except Exception as e:
        print(f"[错误] 调用API或处理数据时发生未知错误: {e}")
        return build_fallback_ai_response(character_profile, current_ai_status)

# ---------------------------------------------------
# 5. 核心函数：生成AI主动发起的消息 (保持不变)
# ---------------------------------------------------
def generate_proactive_message(
    character_profile: dict,
    current_ai_status: dict,
    conversation_history: List[dict]
) -> Optional[AiStructuredResponse]:
    """
    调用大模型为AI角色生成一个分段式的、主动发起的对话。
    注意：此函数返回旧版AiStructuredResponse，不包含control字段，
    因为主动发起消息总是意味着希望开始一段连续对话。
    """
    # 为了复用，我们在这里定义一个临时的、不含control的Pydantic模型
    class ProactiveResponse(BaseModel):
        messages: List[str] = Field(..., min_length=1, max_length=5)

    character_name = character_profile.get('identity_core', {}).get('name', 'AI')
    formatted_history = _format_history_for_prompt(conversation_history, character_name)

    prompt = f"""
# 角色
你正在扮演虚拟角色“{character_name}”。你的任务是构思一段主动发送给用户朋友的问候。

# 角色核心设定 (你的身份)
```json
{json.dumps(character_profile, indent=2, ensure_ascii=False)}
```

# 当前情景 (你正在做什么，这是你发起聊天最直接的灵感来源)
- 状态: {current_ai_status.get('status_description', '没什么特别的。')}

# 对话历史 (你们最近的聊天内容，用于寻找共同话题或回忆)
---
{formatted_history}
---

# 核心任务：主动发起一段对话
你现在因为某个原因，突然想起了你的用户朋友，并决定主动联系TA。
1.  **寻找动机**: 你的开场白必须源于你的“当前情景”或你们的“对话历史”。
2.  **分段发送**: 同样，你**必须**将你的完整问候拆分成 **1到5条** 简短的、口语化的独立消息。
3.  **人设与口吻**: 你的语气和内容必须严格符合你的人设。

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
        
        # 手动构建完整的AiStructuredResponse对象，并赋予默认的“继续聊天”指令
        return AiStructuredResponse(
            messages=validated_data.messages,
            control=ConversationControl(next_state="CONTINUE_CHAT", next_delay_minutes=0)
        )

    except ValidationError as e:
        print(f"[错误] (主动消息) AI返回的JSON格式不正确或字段不匹配: \n{e}")
        print(f"原始响应内容: {raw_response_content}")
        return None
    except Exception as e:
        print(f"[错误] (主动消息) 调用API或处理数据时发生未知错误: {e}")
        return None
