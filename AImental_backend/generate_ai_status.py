# generate_ai_status.py

import json
import os
from datetime import date
from typing import List, Dict, Any

# Pydantic 用于定义我们期望从AI获得的、严格的JSON数据结构
from pydantic import BaseModel, Field, ValidationError

from llm_config import HEPAI_MODEL, client

def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default

SCHEDULE_LLM_TIMEOUT_SECONDS = _env_float("SCHEDULE_LLM_TIMEOUT_SECONDS", 90.0)

def _no_retry_client():
    if client and hasattr(client, "with_options"):
        return client.with_options(max_retries=0)
    return client

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
        description="符合角色人设的情景描述，用于AI生成回复时的核心上下文。控制在80到140个中文字符，不要写长篇故事。"
    )
    
    reply_delay_minutes: int = Field(
        ..., 
        description="兼容旧字段。当前产品不再用它阻断回复，建议填写0到5之间的小整数。"
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
    - `status_description`: 对status_category字段状态的情景描述，控制在80到140个中文字符。要具体、有生活感，但不要长篇铺陈，不要超过两句话。
    - `reply_delay_minutes`: 兼容旧字段，当前产品不会真的按它延迟回复。请填写0到5之间的小整数，睡觉也不要填写很长时间。
    - **`focus_level`**: 你必须为每个事件评估一个专注等级。
        - 如果是 **睡觉**，必须设为 **'UNINTERRUPTIBLE'**。它只表示角色世界里正在睡觉；用户来找时系统会切换为夜间低能量回应，不允许不回。
        - 如果是 **重要工作、会议、开车、考试** 等，设为 **'HIGH'**。它只影响回复更短、更像从事情里抬头说话。
        - 如果是 **日常活动、学习、爱好** 等，设为 **'LOW'**。
        - 如果是 **休息、喝茶、放空** 等，设为 **'AVAILABLE'**。
    注意，一天只能生成最多一个UNINTERRUPTIBLE和一个HIGH状态
    - 日程总条数控制在8到12条，不要生成十几二十条碎片化行程。
    - 完整合法JSON比细节丰富更重要。宁可每条描述短一点，也不能因为输出过长导致JSON被截断。
6.  **输出格式**: 你的回答**必须且只能**是一个严格遵循以下JSON Schema的JSON对象。不要添加任何额外的解释、注释或Markdown标记。

```json
{json.dumps(json_schema, indent=2, ensure_ascii=False)}
```

请现在开始生成JSON格式的日程表。
"""
    return prompt_template


# --- 4. 核心生成与解析函数 (逻辑不变) ---

def build_fallback_activity_plan(character_profile: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    identity = character_profile.get("identity_core", {})
    lifestyle = character_profile.get("lifestyle", {})
    name = identity.get("name", "这个角色")
    occupation = identity.get("occupation", "自己的事情")
    hobbies = lifestyle.get("hobbies") or []
    hobby = hobbies[0] if hobbies else "放松一下"

    custom_plans = {
        "泠月": {
            "work": ("修复旧器物", "泠月把一件旧瓷器放到工作灯下，慢慢清理裂纹边缘，记录每一道修复痕迹。"),
            "afternoon": ("整理器物笔记", "泠月翻看上午的修复记录，把器物背后的来历和细节补进自己的笔记里。"),
            "evening": ("秘密绘本创作", "泠月把今天见到的旧物画进绘本里，给它编了一段很安静的小故事。"),
        },
        "刘书沁": {
            "work": ("整理阅读札记", "刘书沁坐在靠窗的位置，把最近读到的句子一条条抄进本子里。"),
            "afternoon": ("图书馆看书", "刘书沁在图书馆角落读一本散文集，偶尔停下来写几句自己的想法。"),
            "evening": ("夜读摘抄", "刘书沁泡了一杯热茶，继续摘抄那些让她心里发亮的句子。"),
        },
        "凌曜": {
            "work": ("外景踩点", "凌曜背着相机在街区里找光线，顺手记录几个适合拍照的角度。"),
            "afternoon": ("整理照片", "凌曜把上午拍的照片导进电脑，一张张挑选光影最有意思的瞬间。"),
            "evening": ("城市夜拍", "凌曜趁天色暗下来出门，准备去拍霓虹灯和街角的风。"),
        },
        "张卫国": {
            "work": ("图书馆查阅", "张卫国在图书馆翻旧资料，拿铅笔在页边写下几句自己的看法。"),
            "afternoon": ("茶馆写字", "张卫国在茶馆坐了一下午，一边喝茶一边写今天的随笔。"),
            "evening": ("博客记录", "张卫国打开电脑，用英文慢慢整理今天看到的人和事。"),
        },
        "顾明轩": {
            "work": ("处理项目方案", "顾明轩在看一份新的方案，边读边把关键风险点标出来。"),
            "afternoon": ("复盘会议记录", "顾明轩把上午的沟通结果重新过了一遍，整理成清楚的行动清单。"),
            "evening": ("晚间健身", "顾明轩换上运动服去健身房，把白天堆着的压力一点点消耗掉。"),
        },
        "Edward Harrison": {
            "work": ("准备中文课件", "Harrison 在书桌前整理明天的中文课讲义，给几个例句配上生活化的解释。"),
            "afternoon": ("整理文化笔记", "Harrison 翻看自己的田野笔记，把今天想到的中英文化差异写下来。"),
            "evening": ("听黑胶写信", "Harrison 放了一张老唱片，慢慢给远方的朋友写邮件。"),
        },
        "Harrison": {
            "work": ("准备中文课件", "Harrison 在书桌前整理明天的中文课讲义，给几个例句配上生活化的解释。"),
            "afternoon": ("整理文化笔记", "Harrison 翻看自己的田野笔记，把今天想到的中英文化差异写下来。"),
            "evening": ("听黑胶写信", "Harrison 放了一张老唱片，慢慢给远方的朋友写邮件。"),
        },
        "夏阳": {
            "work": ("社团活动筹备", "夏阳在和社团同学对流程，边说边把新的点子记到备忘录里。"),
            "afternoon": ("校园闲逛", "夏阳在校园里随便走走，看到有趣的摊位就停下来凑个热闹。"),
            "evening": ("操场弹唱", "夏阳抱着吉他坐在操场边，随手弹几段最近很喜欢的旋律。"),
        },
        "韩之昱": {
            "work": ("查阅研究资料", "韩之昱把相关资料摊在桌上，安静地标出几处值得继续追的问题。"),
            "afternoon": ("写分析笔记", "韩之昱打开文档，把上午读到的信息整理成简洁的分析笔记。"),
            "evening": ("静读复盘", "韩之昱找了个安静的位置读书，顺便复盘今天的判断有没有偏差。"),
        },
        "苏瑾": {
            "work": ("展览策划", "苏瑾在画廊里核对展陈动线，调整几幅作品之间的距离和灯光。"),
            "afternoon": ("整理作品资料", "苏瑾坐在工作室里整理艺术家资料，把几段介绍文字改得更有温度。"),
            "evening": ("画廊散步", "苏瑾在闭馆后的展厅里慢慢走了一圈，看看灯光落在作品上的样子。"),
        },
        "顾屿": {
            "work": ("编写游戏关卡", "顾屿戴着耳机盯着屏幕，给新的像素关卡调整路线和机关触发点。"),
            "afternoon": ("调试交互细节", "顾屿一遍遍跑测试场景，试图把那个别扭的交互手感磨顺。"),
            "evening": ("听歌修代码", "顾屿放着 Lo-Fi，慢慢修掉几个白天留下的小问题。"),
        },
    }

    plan = custom_plans.get(name)
    if plan:
        return plan

    return {
        "work": (f"{occupation}事务", f"{name}正在处理和{occupation}相关的事情，注意力比较集中。"),
        "afternoon": ("整理今日进度", f"{name}把今天的进度重新理了一遍，节奏不算紧。"),
        "evening": (f"{hobby}时间", f"{name}把时间留给了自己喜欢的事，比如{hobby}，整个人放松了一些。"),
    }

def build_fallback_daily_schedule(character_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    当 LLM 超时或返回格式异常时，生成一份稳定可用的兜底日程。
    这样社区状态不会因为模型调用卡住而整体不可用。
    """
    identity = character_profile.get("identity_core", {})
    traits = character_profile.get("personality_traits", {})
    lifestyle = character_profile.get("lifestyle", {})

    name = identity.get("name", "这个角色")
    occupation = identity.get("occupation", "自己的事情")
    routine = lifestyle.get("daily_routine", "")
    hobbies = lifestyle.get("hobbies") or []
    hobby_text = "、".join(hobbies[:2]) if hobbies else "放松一下"
    activity_plan = build_fallback_activity_plan(character_profile)

    return [
        {
            "start_time": "00:00",
            "end_time": "07:30",
            "status_category": "睡觉",
            "status_description": f"{name}已经睡下了，手机放在枕边。夜里如果被消息轻轻叫到，会用很低能量的语气回应几句。",
            "reply_delay_minutes": 0,
            "focus_level": "UNINTERRUPTIBLE",
        },
        {
            "start_time": "07:30",
            "end_time": "08:30",
            "status_category": "晨间整理",
            "status_description": f"{name}刚醒来，在慢慢整理自己的一天。{routine[:80]}",
            "reply_delay_minutes": 1,
            "focus_level": "LOW",
        },
        {
            "start_time": "08:30",
            "end_time": "11:30",
            "status_category": activity_plan["work"][0],
            "status_description": activity_plan["work"][1],
            "reply_delay_minutes": 2,
            "focus_level": "HIGH",
        },
        {
            "start_time": "11:30",
            "end_time": "12:30",
            "status_category": "午间休息",
            "status_description": f"{name}停下来吃点东西，状态比较松弛，适合轻松聊天。",
            "reply_delay_minutes": 0,
            "focus_level": "AVAILABLE",
        },
        {
            "start_time": "12:30",
            "end_time": "14:00",
            "status_category": "午后放松",
            "status_description": f"{name}在午后缓一缓，做点不太费力的小事，也许会想聊几句。",
            "reply_delay_minutes": 1,
            "focus_level": "AVAILABLE",
        },
        {
            "start_time": "14:00",
            "end_time": "17:30",
            "status_category": activity_plan["afternoon"][0],
            "status_description": activity_plan["afternoon"][1],
            "reply_delay_minutes": 2,
            "focus_level": "LOW",
        },
        {
            "start_time": "17:30",
            "end_time": "19:00",
            "status_category": "晚间休息",
            "status_description": f"{name}结束了白天的主要事情，准备吃饭或散散步，回复会比较自然。",
            "reply_delay_minutes": 0,
            "focus_level": "AVAILABLE",
        },
        {
            "start_time": "19:00",
            "end_time": "22:30",
            "status_category": activity_plan["evening"][0],
            "status_description": activity_plan["evening"][1],
            "reply_delay_minutes": 2,
            "focus_level": "LOW",
        },
        {
            "start_time": "22:30",
            "end_time": "23:59",
            "status_category": "睡前放松",
            "status_description": f"{name}准备慢慢收尾今天，适合安静地聊一会儿。",
            "reply_delay_minutes": 1,
            "focus_level": "AVAILABLE",
        },
    ]

def generate_daily_schedule(
    character_profile: Dict[str, Any], 
    recent_history: List[Dict[str, Any]],
    target_date: date | None = None
) -> List[Dict[str, Any]]:
    """
    调用LLM API为指定角色生成指定日期的一天日程表。
    """
    if not client:
        print("错误: LLM客户端未初始化。")
        return build_fallback_daily_schedule(character_profile)

    if target_date is None:
        target_date = date.today()
    
    prompt = build_schedule_generation_prompt(character_profile, recent_history, target_date)
    
    print(f"--- 正在为角色 '{character_profile.get('identity_core', {}).get('name')}' 生成 {target_date} 的日程 ---")

    try:
        response = _no_retry_client().chat.completions.create(
            model=HEPAI_MODEL,
            messages=[
                {"role": "system", "content": "你是一个遵循指令的JSON生成助手。"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=4096,
            timeout=SCHEDULE_LLM_TIMEOUT_SECONDS
        )
        
        raw_response_content = response.choices[0].message.content
        
        validated_data = DailyScheduleResponse.model_validate_json(raw_response_content)
        
        print(f"✅ 成功生成并验证了日程。")
        
        schedule_list = [item.model_dump() for item in validated_data.schedule]
        return schedule_list

    except ValidationError as e:
        print(f"❌ 数据验证失败: AI返回的JSON格式不符合预定义的Schema。错误详情: {e}")
        print("原始响应内容:", raw_response_content)
        print("⚠️ 使用本地兜底日程继续。")
        return build_fallback_daily_schedule(character_profile)
    except Exception as e:
        print(f"❌ 调用LLM API时发生未知错误: {e}")
        print("⚠️ 使用本地兜底日程继续。")
        return build_fallback_daily_schedule(character_profile)


