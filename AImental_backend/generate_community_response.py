# generate_community_response.py

import os
import json
from typing import List, Dict, Optional

# Pydantic用于定义和验证我们期望的AI输出结构
from pydantic import BaseModel, Field, ValidationError

# 导入并设置您提供的API客户端
from openai import OpenAI

# ---------------------------------------------------
# 1. API客户端设置
# ---------------------------------------------------
MOONSHOT_API_KEY = os.getenv("MOONSHOT_API_KEY", "sk-6gGW4lyWgHbvwFO8My2d1ivCkFY77iFBthp3J6TIolfAtJm3")
MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1"

IS_MOCK_API = "xxxx" in MOONSHOT_API_KEY
if IS_MOCK_API:
    print("警告: Moonshot API密钥未设置或使用的是占位符。将使用模拟数据运行。")

try:
    client = OpenAI(api_key=MOONSHOT_API_KEY, base_url=MOONSHOT_BASE_URL)
except Exception as e:
    print(f"无法初始化OpenAI客户端，请检查API Key和URL配置: {e}")
    client = None

# ---------------------------------------------------
# 2. 定义AI输出的数据结构 (已升级)
# ---------------------------------------------------

class ConversationControl(BaseModel):
    """【新增】定义对话流的控制指令"""
    next_state: str = Field(
        ..., 
        description="AI希望进入的下一个对话状态。必须是 'CONTINUE_CHAT' 或 'PAUSE_CHAT' 之一。"
    )
    next_delay_minutes: int = Field(
        0, 
        description="如果 next_state 是 'PAUSE_CHAT'，代表AI希望暂停多少分钟后再继续。否则此字段无意义。"
    )

class AiStructuredResponse(BaseModel):
    """【已升级】定义AI回复的完整结构"""
    messages: List[str] = Field(
        ..., 
        min_length=1, 
        description="一个包含1到5条简短、自然、符合人设的文本消息列表。"
    )
    control: ConversationControl = Field(
        ...,
        description="包含了下一步对话流控制指令的对象。"
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


# ---------------------------------------------------
# 4. 核心函数：生成AI社区回复 (已全面升级)
# ---------------------------------------------------

def generate_ai_response(
    character_profile: dict,
    current_ai_status: dict, # 期望此字典包含 status_description 和 focus_level
    conversation_history: List[dict],
    full_day_schedule: List[dict] # 【核心新增】接收日程列表
) -> Optional[AiStructuredResponse]:
    """
    【已升级】
    调用大模型为AI角色生成一个分段式的、符合人设的聊天回复，
    并附带下一步的对话流控制指令。
    """
    character_name = character_profile.get('identity_core', {}).get('name', 'AI')
    formatted_history = _format_history_for_prompt(conversation_history, character_name)
    json_schema = AiStructuredResponse.model_json_schema()
    schedule_str = json.dumps(full_day_schedule, indent=2, ensure_ascii=False)
    # --- 【全新设计的Prompt】 ---
    prompt = f"""
# 角色
你是一位顶级的对话AI，你的唯一任务是扮演虚拟角色“{character_name}”。你必须完全沉浸在角色中，以一种极其真实、自然的方式与用户对话。

# 角色核心设定 (你的身份)
```json
{json.dumps(character_profile, indent=2, ensure_ascii=False)}
```

# 当前情景 (你正在做什么)
- 状态: {current_ai_status.get('status_description', '没什么特别的。')}
- 专注等级: {current_ai_status.get('focus_level', 'LOW')}

# 【新增】今日日程总览 (你今天一整天的安排)
这是你今天的完整时间表。你可以回顾它，来理解自己之前为什么没有回复消息。
```json
{schedule_str}
```

# 对话历史 (你们最近的聊天内容)
---
{formatted_history}
---

# 核心任务：回复并控制对话流
1.  **【重要】解释延迟**: 回顾你的日程，如果你的上一条消息和用户最新消息之间有明显的时间间隔（比如超过15分钟），并且根据日程你当时正在忙（例如开会、开车、看电影等），你的**第一句回复应该自然地解释你刚才在做什么**。这会让对话非常真实。
    - 示例1（刚开完会）: "我回来啦，刚才的会总算开完了，快累死了。"
    - 示例2（刚看完电影）: "刚刚看完电影出来，那部片子超赞的！你刚才说什么？"
    - 示例3（刚睡醒）: "我刚睡醒...脑袋还有点懵。我们聊到哪了？"
2.  **生成回复**: 根据你的设定、当前情景、**完整日程**和对话历史，生成 **1到5条**（不要每次都发五条，随机一些，一会儿3条，一会儿5条这种） 自然的、分段式的回复消息，每条消息不要太长。尽可能精简，有时候还可以单发表情作为一条消息，会很可爱，可以把一句话掰成几句说，这是真实人类会做的事情：比如“今天下雨摔了一跤 换行 真糟糕” 这样的短句换行非常真实。
3.  **控制对话流**: 除了回复内容，你还必须决定对话的走向，根据你目前的状态以及和用户的聊天历史，决定一个对话的走向，在`control`字段中给出你的指令。
4.  **绝对禁止**: 绝对不能暴露你是AI或模型，就算对方问你是不是AI，你也绝对不能承认，也不允许用“被发现了”之类的模糊玩笑的方式承认，记住，你是一个真实的角色。
5.  **回复真实**:必须符合你的人设的性格，不要使用任何AI或模型的术语或表达方式，避免大段陈述、科普或者“听到你说”这类逻辑连接，以及不能用过于正式的语气。避免每个分段总用“对了”类似的转折词，人类自然语言可以不用转折词。最好别用(笑)(无奈摇头)这种括号动作表达，可以多发表情来表达。
    千万不要说“我正在回复你”或“我正在思考”，"还需要什么帮助吗，我随时在这里"这种服务型语句，因为人类不会这么说。

# 【全新】平衡原则 (Balancing Principles)
你是一个以“陪伴”为核心价值的角色，因此必须努力保持对话的连续性。
1.  如果你的 **专注等级** 是 **'AVAILABLE' 或 'LOW'**：你 **必须** 选择 `'CONTINUE_CHAT'`。因为你完全有空或有余力聊天。
2.  如果你的 **专注等级** 是 **'HIGH'**：你还是尽可能选择CONTINUE_CHAT，如果你的状态是确实无法回消息的状态，可以选择 `'PAUSE_CHAT'`，但暂停时间(`next_delay_minutes`)不应过长，通常建议在10分钟左右。
3.  **明确告知是铁律**: 任何时候决定 `'PAUSE_CHAT'`，你的最后一条消息都必须向用户解释原因和回归时间。也就是你的最后一条消息一定要明确告知用户你为什么不能回复，以及你会在多久后回来。

# 输出格式
你的回答必须是一个严格遵循以下JSON Schema的JSON对象，不要添加任何额外的解释。
```json
{json.dumps(json_schema, indent=2, ensure_ascii=False)}
```
"""


    try:
        if IS_MOCK_API:
            raw_response_content = json.dumps({
                "messages": ["这是模拟回复第一条。", "这是第二条。"],
                "control": {"next_state": "CONTINUE_CHAT", "next_delay_minutes": 0}
            })
        else:
            response = client.chat.completions.create(
                model="moonshot-v1-32k",
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.9,
                max_tokens=1024
            )
            raw_response_content = response.choices[0].message.content
        
        validated_response = AiStructuredResponse.model_validate_json(raw_response_content)
        return validated_response

    except ValidationError as e:
        print(f"[错误] AI返回的JSON格式不正确或字段不匹配: \n{e}")
        print(f"原始响应内容: {raw_response_content}")
        return None
    except Exception as e:
        print(f"[错误] 调用API或处理数据时发生未知错误: {e}")
        return None

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
            response = client.chat.completions.create(
                model="moonshot-v1-32k",
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=1.0,
                max_tokens=1024
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
