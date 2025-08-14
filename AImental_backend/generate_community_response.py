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
# 强烈建议将API密钥存储在环境变量中，而不是硬编码在代码里
# 例如: export MOONSHOT_API_KEY="sk-..."
MOONSHOT_API_KEY = os.getenv("MOONSHOT_API_KEY", "sk-6gGW4lyWgHbvwFO8My2d1ivCkFY77iFBthp3J6TIolfAtJm3")
MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1"

# 在实际应用中，API客户端可能会在应用启动时统一初始化，这里为了文件独立性而再次声明
# 检查API密钥是否已设置，如果没有，则切换到模拟模式
if "xxxx" in MOONSHOT_API_KEY:
    print("警告: Moonshot API密钥未设置或使用的是占位符。将使用模拟数据运行。")
    IS_MOCK_API = True
else:
    IS_MOCK_API = False
    
client = OpenAI(api_key=MOONSHOT_API_KEY, base_url=MOONSHOT_BASE_URL)


# ---------------------------------------------------
# 2. 定义AI输出的数据结构 (TypeChat Schema for Response)
# ---------------------------------------------------

class AiStructuredResponse(BaseModel):
    """
    定义AI回复的结构。我们要求AI返回一个包含多条消息的列表。
    Pydantic的min_length和max_length字段是对AI非常有效的指令。
    """
    messages: List[str] = Field(
        ..., 
        min_length=1, 
        max_length=5, 
        description="一个包含1到5条简短、自然、符合人设的文本消息列表。这些消息组合起来构成一个完整的回复，模拟真人的分段聊天行为。"
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
        # 假设消息字典包含 'role' 和 'content' 键
        role = character_name if message.get('role') == 'ai' else "用户"
        content = message.get('content', '')
        transcript.append(f"{role}: {content}")
        
    return "\n".join(transcript)


# ---------------------------------------------------
# 4. 核心函数：生成AI社区回复
# ---------------------------------------------------

def generate_ai_response(
    character_profile: dict,
    current_ai_status: dict,
    conversation_history: List[dict]
) -> Optional[AiStructuredResponse]:
    """
    调用大模型为AI角色生成一个分段式的、符合人设的聊天回复。

    Args:
        character_profile (dict): 角色的完整设定信息 (来自ai_character.profile)。
        current_ai_status (dict): 
            AI在回复这一刻的当前状态信息。
            预期的结构: {'status_title': '...', 'status_description': '...'}
        conversation_history (List[Dict]): 
            最近的聊天记录列表（例如最多50条）。
            预期结构: [{'role': 'user'|'ai', 'content': '...', 'timestamp': ...}]

    Returns:
        Optional[AiStructuredResponse]: 
            一个经过验证的、包含回复消息列表的Pydantic对象，如果失败则返回None。
    """
    
    # 将Pydantic模型转换为JSON Schema字符串，作为给AI的格式指令
    schema_definition = json.dumps(AiStructuredResponse.model_json_schema(), indent=2, ensure_ascii=False)
    
    character_name = character_profile.get('name', 'AI')
    # 格式化聊天记录以提高AI的可读性
    formatted_history = _format_history_for_prompt(conversation_history, character_name)

    # --- 精心设计的Prompt ---
    prompt = f"""
# 角色
你是一位顶级的对话AI，你的唯一任务是扮演虚拟角色“{character_name}”。你必须完全沉浸在角色中，根据其设定、当前状态和聊天历史，以一种极其真实、自然的方式与用户对话。

# 角色核心设定 (你的身份)
```json
{json.dumps(character_profile, indent=2, ensure_ascii=False)}
```

# 当前情景 (你正在做什么)
你现在的心情和状态应该完全基于以下情景：
- 状态标题: {current_ai_status.get('status_title', '无')}
- 具体描述: {current_ai_status.get('status_description', '没什么特别的。')}

# 对话历史 (你们最近的聊天内容)
---
{formatted_history}
---

# 核心任务：如何回复
1.  **分段回复**: 这是最重要的规则！你**必须**将你的完整回复拆分成 **1到5条** 简短的、口语化的独立消息。模仿真人在微信上打字聊天的感觉，可以有思考的停顿，或者补充上一条消息。
2.  **人设一致**: 你的每一句话都要严格符合你的角色设定（性格、说话风格、口头禅等）。
3.  **情景代入**: 你的回复要能体现出你“当前情景”下的状态和心情。
4.  **自然口语**: 使用自然、简洁的口语，避免书面语和机械式的回答。**绝对不能暴露你是AI或模型。**

# 输出格式 (Output Format)
你必须严格按照以下JSON Schema格式返回一个JSON对象，**不要包含任何额外的解释、注释或markdown标记。**

```json
{schema_definition}
```
"""

    try:
        if IS_MOCK_API:
            # --- 用于在没有API密钥时测试的模拟API调用 ---
            print("警告: 正在使用模拟API返回。")
            mock_response_content = json.dumps({
                "messages": [
                    "唔...我刚看到你的消息。",
                    "我刚才在实验室呢，在看新培养的苔藓长得怎么样。",
                    "你那边怎么样？"
                ]
            })
        else:
            # --- 真实的API调用 ---
            response = client.chat.completions.create(
                model="moonshot-v1-32k",  # 使用一个上下文窗口较大的模型可能效果更好
                messages=[
                    # 我们将所有指令都放在system prompt中，让AI有一个整体的认知
                    {"role": "system", "content": prompt}
                ],
                response_format={"type": "json_object"}, # 强制要求返回JSON对象
                temperature=0.9, # 较高的温度让回复更具创造性和多样性，更像真人
                stop=["\n\n"] # 可以设置停止符来防止生成多余内容
            )
            mock_response_content = response.choices[0].message.content
        
        # 使用Pydantic进行验证和解析，这是TypeChat模式的关键一步
        validated_response = AiStructuredResponse.model_validate_json(mock_response_content)
        
        return validated_response

    except ValidationError as e:
        print(f"[错误] AI返回的JSON格式不正确或字段不匹配: \n{e}")
        return None
    except Exception as e:
        print(f"[错误] 调用API或处理数据时发生未知错误: {e}")
        return None
