# services/generate_community_response.py (部分)

import os
import json
from typing import List, Dict, Optional

# Pydantic用于定义和验证我们期望的AI输出结构
from pydantic import BaseModel, Field, ValidationError

# 导入并设置您提供的API客户端
from openai import OpenAI

# ---------------------------------------------------
# 1. API客户端设置 (假设已在文件顶部定义)
# ---------------------------------------------------
MOONSHOT_API_KEY = os.getenv("MOONSHOT_API_KEY", "sk-6gGW4lyWgHbvwFO8My2d1ivCkFY77iFBthp3J6TIolfAtJm3")
MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1"
IS_MOCK_API = "xxxx" in MOONSHOT_API_KEY
client = OpenAI(api_key=MOONSHOT_API_KEY, base_url=MOONSHOT_BASE_URL)


# ---------------------------------------------------
# 2. 定义AI输出的数据结构 (假设已在文件顶部定义)
# ---------------------------------------------------
class AiStructuredResponse(BaseModel):
    """定义AI回复的结构，用于主动和被动回复。"""
    messages: List[str] = Field(
        ..., 
        min_length=1, 
        max_length=5, 
        description="一个包含1到5条简短、自然、符合人设的文本消息列表。"
    )

# ---------------------------------------------------
# 3. 辅助函数 (假设已在文件顶部定义)
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


# ===================================================
# 核心函数：生成AI主动发起的消息 (新增函数)
# ===================================================

def generate_proactive_message(
    character_profile: dict,
    current_ai_status: dict,
    conversation_history: List[dict]
) -> Optional[AiStructuredResponse]:
    """
    【新增】
    调用大模型为AI角色生成一个分段式的、主动发起的对话。

    Args:
        character_profile (dict): 角色的完整设定信息。
        current_ai_status (dict): AI在决定发起聊天这一刻的当前状态。
        conversation_history (List[Dict]): 最近的聊天记录，用于寻找话题和避免重复。

    Returns:
        Optional[AiStructuredResponse]: 
            一个经过验证的、包含主动问候消息列表的Pydantic对象，如果失败则返回None。
    """
    
    # 复用已有的组件和逻辑
    schema_definition = json.dumps(AiStructuredResponse.model_json_schema(), indent=2, ensure_ascii=False)
    character_name = character_profile.get('identity_core', {}).get('name', 'AI')
    formatted_history = _format_history_for_prompt(conversation_history, character_name)

    # --- 专为“主动发起聊天”设计的Prompt ---
    prompt = f"""
# 角色
你正在扮演虚拟角色“{character_name}”。你的任务是构思一段主动发送给用户朋友的问候。

# 角色核心设定 (你的身份)
```json
{json.dumps(character_profile, indent=2, ensure_ascii=False)}
```

# 当前情景 (你正在做什么，这是你发起聊天最直接的灵感来源)
- 状态标题: {current_ai_status.get('status_title', '无')}
- 具体描述: {current_ai_status.get('status_description', '没什么特别的。')}

# 对话历史 (你们最近的聊天内容，用于寻找共同话题或回忆)
---
{formatted_history}
---

# 核心任务：主动发起一段对话
你现在因为某个原因，突然想起了你的用户朋友，并决定主动联系TA。你需要构思一段自然、真诚的开场白。
1.  **寻找动机**: 你的开场白必须源于你的“当前情景”或你们的“对话历史”。
    -   **情景触发**: 你现在做的事让你想起了TA吗？(例如：你在听歌，想分享给TA；你看到了有趣的东西，想拍给TA看。)
    -   **回忆触发**: 你是否想起了上次聊天时TA提到的某件事？(例如：TA说最近压力大，你想关心一下；TA推荐的电影你刚看完，想分享感受。)
    -   **纯粹想念**: 就是突然想打个招呼，问问对方“在干嘛？”或“今天过得怎么样？”。
2.  **分段发送**: 同样，你**必须**将你的完整问候拆分成 **1到5条** 简短的、口语化的独立消息。
3.  **人设与口吻**: 你的语气和内容必须严格符合你的人设。一个内向的角色可能会更含蓄，一个活泼的角色可能会更直接。
4.  **禁止暴露**: 绝对不能暴露你是AI或模型。

# 输出格式 (Output Format)
你必须严格按照以下JSON Schema格式返回一个JSON对象，**不要包含任何额外的解释、注释或markdown标记。**

```json
{schema_definition}
```
"""

    try:
        if IS_MOCK_API:
            # --- 用于测试的模拟API调用 ---
            print("警告: 正在使用模拟API返回 (主动消息)。")
            mock_response_content = json.dumps({
                "messages": [
                    "在吗？",
                    "我刚刚在阳台给薄荷浇水，突然想起来你上次说你也喜欢养植物。",
                    "它最近长得特别快，给你看看照片？"
                ]
            })
        else:
            # --- 真实的API调用 ---
            response = client.chat.completions.create(
                model="moonshot-v1-32k",
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=1.0, # 较高的温度让开场白更具创造性和多样性
            )
            mock_response_content = response.choices[0].message.content
        
        # 使用Pydantic进行验证和解析
        validated_response = AiStructuredResponse.model_validate_json(mock_response_content)
        
        return validated_response

    except ValidationError as e:
        print(f"[错误] (主动消息) AI返回的JSON格式不正确或字段不匹配: \n{e}")
        return None
    except Exception as e:
        print(f"[错误] (主动消息) 调用API或处理数据时发生未知错误: {e}")
        return None

