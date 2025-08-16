# services/generate_friend_response.py

import os
import json
from typing import Optional

# Pydantic用于定义和验证我们期望的AI输出结构，这是实现可靠性的关键
from pydantic import BaseModel, Field, ValidationError

# 导入并设置您提供的API客户端
from openai import OpenAI

# ---------------------------------------------------
# 1. API客户端设置
# ---------------------------------------------------
# 强烈建议将API密钥存储在环境变量中，而不是硬编码在代码里
MOONSHOT_API_KEY = os.getenv("MOONSHOT_API_KEY", "sk-6gGW4lyWgHbvwFO8My2d1ivCkFY77iFBthp3J6TIolfAtJm3")
MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1"

# 检查API密钥是否已设置，如果没有，则切换到模拟模式以便于测试
IS_MOCK_API = "xxxx" in MOONSHOT_API_KEY
if IS_MOCK_API:
    print("警告: Moonshot API密钥未设置或使用的是占位符。将使用模拟数据运行。")

try:
    client = OpenAI(api_key=MOONSHOT_API_KEY, base_url=MOONSHOT_BASE_URL)
except Exception as e:
    print(f"无法初始化OpenAI客户端，请检查API Key和URL配置: {e}")
    client = None


# ---------------------------------------------------
# 2. 定义AI决策的输出结构 (TypeChat Schema)
# ---------------------------------------------------

class FriendRequestDecision(BaseModel):
    """
    定义AI对好友请求的决策结构。
    这个模型将作为AI必须遵守的“格式合同”。
    """
    decision: bool = Field(..., description="是否同意好友申请 (true表示同意, false表示拒绝)")
    reasoning: str = Field(..., description="AI做出此决定的、符合其人设的内心想法（用于调试或丰富角色）。")
    initial_message: Optional[str] = Field(None, description="如果同意，这是发送给用户的第一条消息。如果拒绝，此字段为null。")


# ---------------------------------------------------
# 3. 核心函数：生成好友申请的回复 (已更新Prompt)
# ---------------------------------------------------

def generate_friend_request_decision(
    character_profile: dict,
    user_verification_message: str
) -> Optional[FriendRequestDecision]:
    """
    调用大模型，让AI角色决定是否接受好友申请。
    """
    if not client:
        print("错误: LLM客户端未初始化。")
        return None

    character_name = character_profile.get('identity_core', {}).get('name', 'AI')
    
    # --- 【核心修改】我们重新设计了Prompt，使其更清晰 ---
    prompt = f"""
# 角色
你正在扮演虚拟角色“{character_name}”。

# 角色核心设定 (你的身份)
```json
{json.dumps(character_profile, indent=2, ensure_ascii=False)}
```

# 情景
一个陌生用户想添加你为好友，并给你发来了以下的验证信息,你是一个真是的角色，不要暴露你是AI，请你说话语言自然，不要有人机感，口语化地回复用户的验证消息，更不要逻辑发言“收到你的验证消息，回复...”这种情况必须避免。

# 用户的验证信息
"{user_verification_message}"

# 核心任务：做出决定
你需要根据你的性格和对方的留言，决定是否同意这个好友申请，并严格按照下面的JSON格式给出你的“内心决策”。
1.  **性格判断**: 如果你的性格是外向、好奇的，你可能更容易同意。如果你的性格是内向、谨慎或高冷的，你可能会更挑剔，甚至拒绝。
2.  **留言判断**: 对方的留言是否真诚、有趣或让你产生好奇？
3.  **生成内心独白**: 在 `reasoning` 字段中，简单说明你为什么会做出这个决定。
4.  **撰写初次问候**: 如果你同意了，在 `initial_message` 字段中写一句符合你风格的、作为初次见面的问候语。如果拒绝，`initial_message` 必须为 `null`。

# 输出格式与示例
你的回答必须是一个严格的、不包含任何其他文字的JSON对象。

## 这是一个【同意】时的输出示例:
```json
{{
  "decision": true,
  "reasoning": "唔...听起来是个有趣的人，验证消息也挺真诚的，那就认识一下吧。",
  "initial_message": "你好，我是{character_name}。很高兴认识你。"
}}
```

## 这是一个【拒绝】时的输出示例:
```json
{{
  "decision": false,
  "reasoning": "感觉有点随意，还是先保持距离吧，我不太喜欢和陌生人说话。",
  "initial_message": null
}}
```
"""
    # 注意: 上面示例中的 {{ 和 }} 是为了在f-string中正确显示花括号

    try:
        if IS_MOCK_API:
            print("警告: 正在使用模拟API返回。")
            mock_response_content = json.dumps({
                "decision": True,
                "reasoning": "唔...听起来是个有趣的人，验证消息也挺真诚的，那就认识一下吧。",
                "initial_message": f"你好，我是{character_name}。很高兴认识你。"
            })
            raw_response_content = mock_response_content
        else:
            # --- 真实的API调用 ---
            response = client.chat.completions.create(
                model="moonshot-v1-8k",
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"}, # 强制要求返回JSON对象
                temperature=1.0, # 使用较高的温度让决策更多样化，更像真人
                max_tokens=512 # 给决策任务一个合理的token限制
            )
            raw_response_content = response.choices[0].message.content
        
        # 使用Pydantic进行验证和解析，这是最关键的一步
        return FriendRequestDecision.model_validate_json(raw_response_content)
        
    except ValidationError as e:
        print(f"[错误] AI返回的JSON格式不正确或字段不匹配: \n{e}")
        # 在Pydantic v2中，e.json()可以更清晰地打印错误
        print(f"原始响应内容: {raw_response_content}")
        return None
    except Exception as e:
        print(f"[错误] 调用API或处理数据时发生未知错误: {e}")
        return None
