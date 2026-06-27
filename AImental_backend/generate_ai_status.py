# generate_ai_status.py

import json
from datetime import date, timedelta
from typing import List, Dict, Any

# Pydantic 用于定义我们期望从AI获得的、严格的JSON数据结构
from pydantic import BaseModel, Field, ValidationError

from llm_config import HEPAI_MODEL, client

# --- 1. 配置LLM客户端 ---
# LLM 调用统一走 HEPAI 的 OpenAI-compatible API，配置见 llm_config.py。

# --- 2. 定义期望的JSON输出结构 (已升级) ---

class ScheduleItem(BaseModel):
    """
    【已升级】定义单条日程的数据结构。
    这个结构直接映射到你的 `AiStatus` 数据库表字段。
    """
    start_time: str = Field(..., description="事件开始时间，格式为 'HH:MM'")
    end_time: str = Field(..., description="事件结束时间，格式为 'HH:MM'")
    
    status_category: str = Field(
        ..., 
        description="用简短但稍微具体的中文概括当前状态，八个字以内，比如在孟加拉出差、开会、刷手机准备睡觉等，但注意要是一个完整的状态，不能只是名词，比如不能说科幻电影，要说看科幻电影"
    )
    
    status_description: str = Field(
        ..., 
        description="符合角色人设的、详细的情景描述，用于AI生成回复时的核心上下文。越详细越好，可以细化到很具体的小事。"
    )
    
    reply_delay_minutes: int = Field(
        ..., 
        description="建议的回复延迟分钟数。0代表可立即回复。根据事件的投入程度来决定。"
    )

    # --- 【核心新增】 ---
    focus_level: str = Field(
        ...,
        description="根据事件的重要性，从 'UNINTERRUPTIBLE', 'HIGH', 'LOW', 'AVAILABLE' 四个选项中选择一个。"
    )
    # --- ------------ ---

class DailyScheduleResponse(BaseModel):
    """定义一整天日程表的完整数据结构"""
    schedule: List[ScheduleItem] = Field(..., description="包含当天所有日程项目的列表。")


# --- 3. 构建核心Prompt (已升级) ---

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
    # 【重要】使用更新后的模型来生成Schema
    json_schema = DailyScheduleResponse.model_json_schema()

    prompt_template = f"""
# 使命
你是一个富有创造力和逻辑思维的虚拟角色日程规划师。你的任务是为一个名为“{character_profile.get('identity_core', {}).get('name', '角色')}”的虚拟角色，生成一整天（24小时）的、高度真实的、符合其人设的日程表。（重要：一定要拉满24小时，无时间间隙，必须从零点生成到23:59:59无死角！！！！）

# 角色核心设定
你必须严格遵守以下角色设定来构思日程：
{profile_str}

# 近期历史行为 (过去{len(recent_history)}天)
为了保证行为的连续性，请参考该角色最近的活动。特别是要确保今天的第一个活动能与昨天的最后一个活动平滑衔接。
{history_str}

# 任务指令
1.  **生成目标日期**: 请为 **{target_date.strftime('%Y-%m-%d')}** 这一天生成日程。
2.  **逻辑连贯性**: 日程必须逻辑连贯，时间线合理。
3.  **人设一致性**: 所有活动都必须深度契合角色的职业、性格和兴趣爱好。
4.  **时间覆盖**: 所有日程项目的时间应连续，并大致覆盖从 `00:00` 到 `23:59` 的24小时。
5.  **【已升级】字段生成规则**:
    - `status_category`: 必须根据角色的个人特征以及前几天的活动轨迹来生成，可以是任意状态，但必须逻辑合理,这个部分简短一点儿的中文就行，五个字以内，必须是中文哦。
    - `status_description`: 对status_category字段状态的详细描述，越详细越好，可以描述很具体的事件，必须符合人设。
    - `reply_delay_minutes`: 根据事件的投入程度，估算一个合理的整数作为回复延迟分钟数。（除了睡觉状态，其他状态的延迟时间至多30分钟）
    - **`focus_level`**: 你必须为每个事件评估一个专注等级。
        - 如果是 **睡觉**，必须设为 **'UNINTERRUPTIBLE'**。 延迟时间完全不限，可以睡醒再回复，也就是覆盖睡觉的时间
        - 如果是 **重要工作、会议、开车、考试** 等，设为 **'HIGH'**。 延迟时间大概5分钟左右即可
        - 如果是 **日常活动、学习、爱好** 等，设为 **'LOW'**。        延迟时间10秒左右
        - 如果是 **休息、喝茶、放空** 等，设为 **'AVAILABLE'**。      延迟时间为0 秒回
    注意，一天只能生成最多一个UNINTERRUPTIBLE和一个HIGH状态
6.  **输出格式**: 你的回答**必须且只能**是一个严格遵循以下JSON Schema的JSON对象。不要添加任何额外的解释、注释或Markdown标记。

```json
{json.dumps(json_schema, indent=2, ensure_ascii=False)}
```

请现在开始生成JSON格式的日程表。
"""
    return prompt_template


# --- 4. 核心生成与解析函数 (逻辑不变) ---

def generate_daily_schedule(
    character_profile: Dict[str, Any], 
    recent_history: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    调用LLM API为指定角色生成一天的日程表。
    """
    if not client:
        print("错误: LLM客户端未初始化。")
        return []

    target_date = date.today() + timedelta(days=1)
    
    prompt = build_schedule_generation_prompt(character_profile, recent_history, target_date)
    
    print(f"--- 正在为角色 '{character_profile.get('identity_core', {}).get('name')}' 生成 {target_date} 的日程 ---")

    try:
        response = client.chat.completions.create(
            model=HEPAI_MODEL,
            messages=[
                {"role": "system", "content": "你是一个遵循指令的JSON生成助手。"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=2048
        )
        
        raw_response_content = response.choices[0].message.content
        
        validated_data = DailyScheduleResponse.model_validate_json(raw_response_content)
        
        print(f"✅ 成功生成并验证了日程。")
        
        schedule_list = [item.model_dump() for item in validated_data.schedule]
        return schedule_list

    except ValidationError as e:
        print(f"❌ 数据验证失败: AI返回的JSON格式不符合预定义的Schema。错误详情: {e}")
        print("原始响应内容:", raw_response_content)
        return []
    except Exception as e:
        print(f"❌ 调用LLM API时发生未知错误: {e}")
        return []


