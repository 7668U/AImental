# services/generate_ai_status.py

import os
import json
from datetime import date, timedelta
from typing import List, Dict, Any

# Pydantic 用于定义我们期望从AI获得的、严格的JSON数据结构
from pydantic import BaseModel, Field, ValidationError

# 导入你的LLM客户端
from openai import OpenAI

# --- 1. 配置LLM客户端 ---
# 在实际项目中，建议使用环境变量管理API Key
MOONSHOT_API_KEY = os.getenv("MOONSHOT_API_KEY", "sk-6gGW4lyWgHbvwFO8My2d1ivCkFY77iFBthp3J6TIolfAtJm3")
MOONSHOT_BASE_URL = os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1")

# 注意：如果MOONSHOT_API_KEY是示例值，下面的API调用会失败。
# 请替换为您自己的有效API Key来运行。
try:
    client = OpenAI(api_key=MOONSHOT_API_KEY, base_url=MOONSHOT_BASE_URL)
except Exception as e:
    print(f"无法初始化OpenAI客户端，请检查API Key和URL配置: {e}")
    client = None

# --- 2. 定义期望的JSON输出结构 (与你的AiStatus模型对应) ---

class ScheduleItem(BaseModel):
    """
    定义单条日程的数据结构。
    这个结构直接映射到你的 `AiStatus` 数据库表字段。
    """
    start_time: str = Field(..., description="事件开始时间，格式为 'HH:MM'")
    end_time: str = Field(..., description="事件结束时间，格式为 'HH:MM'")
    
    # 对应 AiStatus.status_category
    status_category: str = Field(
        ..., 
        description="事件的内部逻辑分类。例如: 'work', 'hobby', 'social', 'chore', 'relax', 'meal', 'travel', 'exercise', 'sleep'"
    )
    
    # 对应 AiStatus.status_description
    status_description: str = Field(
        ..., 
        description="符合角色人设的、详细的情景描述，用于AI生成回复时的核心上下文。"
    )
    
    # 对应 AiStatus.reply_delay_minutes
    reply_delay_minutes: int = Field(
        ..., 
        description="建议的回复延迟分钟数。0代表可立即回复。根据事件的投入程度来决定。"
    )

class DailyScheduleResponse(BaseModel):
    """定义一整天日程表的完整数据结构"""
    schedule: List[ScheduleItem] = Field(..., description="包含当天所有日程项目的列表。")


# --- 3. 构建核心Prompt (已修复三引号问题并更新指令) ---

def build_schedule_generation_prompt(
    character_profile: Dict[str, Any], 
    recent_history: List[Dict[str, Any]],
    target_date: date
) -> str:
    """
    构建一个详细的、结构化的Prompt，用于指导LLM生成日程。
    """
    profile_str = json.dumps(character_profile, indent=2, ensure_ascii=False)
    history_str = json.dumps(recent_history, indent=2, ensure_ascii=False)
    json_schema = DailyScheduleResponse.model_json_schema()

    # 这是整个魔法的核心：一个结构清晰、指令明确的Prompt模板
    prompt_template = f"""
# 使命
你是一个富有创造力和逻辑思维的虚拟角色日程规划师。你的任务是为一个名为“{character_profile.get('identity_core', {}).get('name', '角色')}”的虚拟角色，生成一整天（24小时）的、高度真实的、符合其人设的日程表。

# 角色核心设定
你必须严格遵守以下角色设定来构思日程：
{profile_str}

# 近期历史行为 (过去{len(recent_history)}天)
为了保证行为的连续性，请参考该角色最近的活动。特别是要确保今天的第一个活动能与昨天的最后一个活动平滑衔接。
{history_str}

# 任务指令
1.  **生成目标日期**: 请为 **{target_date.strftime('%Y-%m-%d')}** 这一天生成日程。
2.  **逻辑连贯性**: 日程必须逻辑连贯，时间线合理。例如，工作后会通勤，饭前会准备或外出，睡前会有放松活动。避免出现“上一秒在开会，下一秒在深海潜水”的突兀转变。
3.  **人设一致性**: 所有活动都必须深度契合角色的职业、性格和兴趣爱好。例如，一个植物学家可能会“在实验室观察样本”，而不是“在金融市场操盘”。
4.  **时间覆盖**: 所有日程项目的时间应连续，并大致覆盖从 `00:00` 到 `23:59` 的24小时。
5.  **字段生成规则**:
    - `status_category`: 必须根据角色的个人特征以及前几天的活动轨迹来生成，可以是任意状态，但必须逻辑合理，不能出现上一秒还在吃火锅，下一秒在南极开会这样的离谱情况。这个字段是状态的一个简短描述，比如开会。
    - `status_description`: 这个字段是一个对状态详细的描述，比如，由于研究所要求出差，在孟加拉开国际原子物理会议，描述可以尽可能详细！
    - `reply_delay_minutes`: 必须根据事件的投入程度，估算一个合理的整数作为回复延迟分钟数。例如，“睡觉”或“重要会议”的延迟应该很长（如120分钟以上），而“喝咖啡”或“发呆”的延迟可以是0。
6.  **输出格式**: 你的回答**必须且只能**是一个严格遵循以下JSON Schema的JSON对象。不要添加任何额外的解释、注释或Markdown标记。

```json
{json.dumps(json_schema, indent=2, ensure_ascii=False)}
```

请现在开始生成JSON格式的日程表。
"""
    return prompt_template


# --- 4. 核心生成与解析函数 (已更新) ---

def generate_daily_schedule(
    character_profile: Dict[str, Any], 
    recent_history: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    调用LLM API为指定角色生成一天的日程表。

    Args:
        character_profile (Dict): 角色的完整设定。
        recent_history (List[Dict]): 角色最近几天的日程历史。

    Returns:
        List[Dict[str, Any]]: 成功时返回日程列表，失败时返回空列表。
    """
    if not client:
        print("错误: LLM客户端未初始化。")
        return []

    target_date = date.today() + timedelta(days=1) # 默认生成明天的日程
    
    # 1. 构建Prompt
    prompt = build_schedule_generation_prompt(character_profile, recent_history, target_date)
    
    print(f"--- 正在为角色 '{character_profile.get('identity_core', {}).get('name')}' 生成 {target_date} 的日程 ---")

    try:
        # 2. 调用API
        response = client.chat.completions.create(
            model="moonshot-v1-8k",  # 或者你选择的其他模型
            messages=[
                {"role": "system", "content": "你是一个遵循指令的JSON生成助手。"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}, # 强制要求返回JSON对象
            temperature=0.7,
            max_tokens=2048  # <-- 【核心修复】在这里增加 max_tokens 参数
        )
        
        raw_response_content = response.choices[0].message.content
        
        # 3. 解析和验证
        validated_data = DailyScheduleResponse.model_validate_json(raw_response_content)
        
        print(f"✅ 成功生成并验证了日程。")
        
        # 将Pydantic模型转换为纯字典列表返回
        schedule_list = [item.model_dump() for item in validated_data.schedule]
        return schedule_list

    except ValidationError as e:
        print(f"❌ 数据验证失败: AI返回的JSON格式不符合预定义的Schema。错误详情: {e}")
        print("原始响应内容:", raw_response_content)
        return []
    except Exception as e:
        print(f"❌ 调用LLM API时发生未知错误: {e}")
        return []


# --- 5. 示例：如何使用这个脚本 ---

if __name__ == "__main__":
    print("🚀 开始执行AI日程生成脚本示例...")

    # 准备一个角色的Profile
    lingjian_profile = {
        "identity_core": { "name": "林间", "age": 28, "gender": "女", "occupation": "植物学在读博士" },
        "personality_traits": { "mbti": "INFJ", "personality_tags": ["温柔", "理性", "有耐心", "轻微社恐"] },
        "lifestyle": { "hobbies": ["侍弄花草", "手冲咖啡", "阅读旧书"], "daily_routine": "早睡早起，上午效率最高。" }
    }

    # 准备一份模拟的近期历史
    mock_recent_history = [
        { "date": (date.today() - timedelta(days=1)).strftime('%Y-%m-%d'), "summary": "全天在实验室整理数据，晚上阅读了关于苔藓植物的文献直到深夜。" }
    ]

    # 调用核心函数
    generated_schedule = generate_daily_schedule(
        character_profile=lingjian_profile,
        recent_history=mock_recent_history
    )

    # 打印结果
    if generated_schedule:
        print("\n--- 生成的日程表示例 ---")
        print(json.dumps(generated_schedule, indent=2, ensure_ascii=False))
        print("\n脚本执行完毕。")
    else:
        print("\n未能成功生成日程表。请检查API Key配置和错误信息。")

