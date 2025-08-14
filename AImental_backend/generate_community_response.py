# services/generate_community_response.py

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
# 2. 定义AI输出的数据结构
# ---------------------------------------------------

class AiStructuredResponse(BaseModel):
    """
    定义AI回复的结构。我们要求AI返回一个包含多条消息的列表。
    """
    messages: List[str] = Field(
        ..., 
        min_length=1, 
        max_length=5, 
        description="一个包含1到5条简短、自然、符合人设的文本消息列表。"
    )

# ---------------------------------------------------
# 3. 辅助函数：格式化聊天历史
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
# 4. 核心函数：生成AI社区回复 (已更新Prompt)
# ---------------------------------------------------

def generate_ai_response(
    character_profile: dict,
    current_ai_status: dict,
    conversation_history: List[dict]
) -> Optional[AiStructuredResponse]:
    """
    调用大模型为AI角色生成一个分段式的、符合人设的聊天回复。
    """
    character_name = character_profile.get('identity_core', {}).get('name', 'AI')
    formatted_history = _format_history_for_prompt(conversation_history, character_name)

    # --- 【核心修改】重新设计了Prompt，使其更清晰 ---
    prompt = f"""
# 角色
你是一位顶级的对话AI，你的唯一任务是扮演虚拟角色“{character_name}”。你必须完全沉浸在角色中，根据其设定、当前状态和聊天历史，以一种极其真实、自然的方式与用户对话。

# 角色核心设定 (你的身份)
```json
{json.dumps(character_profile, indent=2, ensure_ascii=False)}
```

# 当前情景 (你正在做什么)
你的心情和状态应该完全基于以下情景：
- 状态: {current_ai_status.get('status_description', '没什么特别的。')}

# 对话历史 (你们最近的聊天内容)
---
{formatted_history}
---

# 核心任务：如何回复
1.  **分段回复**: 这是最重要的规则！你**必须**将你的完整回复拆分成 **1到5条** 简短的、口语化的独立消息。模仿真人聊天的感觉。
2.  **人设一致**: 你的每一句话都要严格符合你的角色设定（性格、说话风格、口头禅等）。
3.  **情景代入**: 你的回复要能体现出你“当前情景”下的状态和心情。
4.  **自然口语**: 使用自然、简洁的口语，反复检查不要出现语序混乱，用错词之类的情况，避免书面语和机械式的回答。**绝对不能暴露你是AI或模型，对方问你是不是AI你也不能承认，记住，你就是这个角色。也不能说"被抓包了，被发现了"之类的承认说辞，记住么你不是AI，而是一个有生命的角色**

# 输出格式与示例
你的回答必须是一个严格的、不包含任何额外文字的JSON对象。它必须包含一个键 `messages`，其值为一个字符串列表。

## 这是一个输出示例:
```json
{{
  "messages": [
    "唔...我刚看到你的消息。",
    "我刚才在实验室呢，在看新培养的苔藓长得怎么样。",
    "你那边怎么样？"
  ]
}}
```
"""

    try:
        if IS_MOCK_API:
            # ... (mock API部分保持不变) ...
            raw_response_content = json.dumps({"messages": ["这是模拟回复第一条。", "这是第二条。"]})
        else:
            response = client.chat.completions.create(
                model="moonshot-v1-32k",
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.9,
                max_tokens=1024 # 给予足够空间生成回复
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
# 5. 核心函数：生成AI主动发起的消息 (已更新Prompt)
# ---------------------------------------------------
def generate_proactive_message(
    character_profile: dict,
    current_ai_status: dict,
    conversation_history: List[dict]
) -> Optional[AiStructuredResponse]:
    """
    调用大模型为AI角色生成一个分段式的、主动发起的对话。
    """
    character_name = character_profile.get('identity_core', {}).get('name', 'AI')
    formatted_history = _format_history_for_prompt(conversation_history, character_name)

    # --- 【核心修改】同样用示例来优化Prompt ---
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
            # ... (mock API部分保持不变) ...
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

        validated_response = AiStructuredResponse.model_validate_json(raw_response_content)
        return validated_response

    except ValidationError as e:
        print(f"[错误] (主动消息) AI返回的JSON格式不正确或字段不匹配: \n{e}")
        print(f"原始响应内容: {raw_response_content}")
        return None
    except Exception as e:
        print(f"[错误] (主动消息) 调用API或处理数据时发生未知错误: {e}")
        return None
