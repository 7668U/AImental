# services/generate_favorability.py

import os
import json
from datetime import date
from typing import Optional, List, Dict

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
# 2. 定义AI评估的输出结构 (TypeChat Schema)
# ---------------------------------------------------

class FavorabilityAssessment(BaseModel):
    """
    定义AI对好感度评估的结构。
    """
    new_favorability_score: int = Field(
        ..., 
        ge=0, 
        le=100, 
        description="评估后得出的新的好感度分数 (必须在0到100之间)。"
    )
    change_reason: str = Field(
        ..., 
        description="一句话解释为什么好感度发生了这样的变化，例如'用户分享了开心的事'或'最近没有联系，关系有些疏远'。"
    )
    analysis: str = Field(
        ...,
        description="对本次评估的简短分析，总结对话的情感动态。"
    )


# ---------------------------------------------------
# 3. 辅助函数：格式化输入数据
# ---------------------------------------------------
def _format_chat_history(history: List[Dict]) -> str:
    """将最近的聊天记录格式化为对AI更友好的文本。"""
    if not history:
        return "最近没有聊天记录。"
    
    transcript = []
    for message in history:
        role = "用户" if message.get('role') == 'user' else "AI角色"
        content = message.get('content', '')
        transcript.append(f"{role}: {content}")
        
    return "\n".join(transcript)

def _format_favorability_history(history: List[Dict]) -> str:
    """将好感度历史格式化为趋势描述。"""
    if not history:
        return "这是你们好感度的初始评估。"
        
    trend_strs = [f"- {item.get('date')}: {item.get('score')}分 ({item.get('reason', '无原因')})" for item in history]
    return "\n".join(trend_strs)


# ---------------------------------------------------
# 4. 核心函数：评估好感度
# ---------------------------------------------------

def assess_favorability(
    character_profile: dict,
    recent_chat_history: List[dict],
    favorability_history: List[dict]
) -> Optional[FavorabilityAssessment]:
    """
    调用大模型，分析对话内容和历史趋势，评估并更新好感度。

    Args:
        character_profile (dict): 角色的完整设定信息。
        recent_chat_history (List[dict]): 最近的聊天记录 (例如过去7天)。
        favorability_history (List[dict]): 过去的好感度变更记录。

    Returns:
        Optional[FavorabilityAssessment]: 一个包含评估结果的Pydantic对象，失败则返回None。
    """
    if not client:
        print("错误: LLM客户端未初始化。")
        return None

    schema_definition = json.dumps(FavorabilityAssessment.model_json_schema(), indent=2, ensure_ascii=False)
    character_name = character_profile.get('identity_core', {}).get('name', 'AI')
    
    # 格式化输入数据
    formatted_chat = _format_chat_history(recent_chat_history)
    formatted_favorability = _format_favorability_history(favorability_history)

    # --- 精心设计的Prompt ---
    prompt = f"""
# 角色
你是一位精准的情感与关系分析师。你的任务是基于提供的材料，客观评估用户与虚拟角色“{character_name}”之间的好感度。

# 分析材料

## 1. 虚拟角色设定 (TA的性格)
```json
{json.dumps(character_profile, indent=2, ensure_ascii=False)}
```

## 2. 最近的聊天记录 (他们聊了什么)
---
{formatted_chat}
---

## 3. 历史好感度趋势 (关系如何演变)
---
{formatted_favorability}
---

# 核心任务：进行评估
你需要综合以上所有信息，给出一个新的好感度分数（0-100）。评估时请遵循以下逻辑：
1.  **正面互动**: 如果用户表达了关心、分享了积极情绪、进行了有深度的交流，好感度应**显著上升**。
2.  **负面互动**: 如果对话中有争吵、误解或冷漠，好感度应**显著下降**。
3.  **日常互动**: 平淡的日常聊天可以使好感度**小幅上升或保持**。
4.  **无互动**: 如果“最近的聊天记录”为空，表示双方最近没有联系，好感度应**小幅自然下降**（-1到-3分），模拟现实中关系的疏远。
5.  **性格影响**: 必须考虑角色的性格。一个开朗的角色好感度更容易提升，一个高冷、内向的角色则需要更多努力才能提升好感度。
6.  **趋势延续**: 评估结果应参考“历史好感度趋势”，新的分数不应与之前的趋势发生毫无理由的剧烈波动。

# 输出格式
你的回答必须是严格遵循以下JSON Schema的JSON对象，不要添加任何其他文字。
```json
{schema_definition}
```
"""

    try:
        if IS_MOCK_API:
            print("警告: 正在使用模拟API返回。")
            mock_response_content = json.dumps({
                "new_favorability_score": 65,
                "change_reason": "用户分享了工作中的趣事，进行了一次愉快的交流。",
                "analysis": "对话氛围积极，用户表现出主动分享的意愿，关系呈上升趋势。"
            })
        else:
            response = client.chat.completions.create(
                model="moonshot-v1-8k",
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.5 # 使用较低的温度让评估更客观、稳定
            )
            mock_response_content = response.choices[0].message.content
        
        return FavorabilityAssessment.model_validate_json(mock_response_content)
        
    except (ValidationError, Exception) as e:
        print(f"[错误] 生成好感度评估时出错: {e}")
        return None
