# LLM.py

import os
import json
from openai import OpenAI
from typing import Optional, List, Dict
import datetime

# --- 模型导入 ---
# 从你的 chat.py 文件中导入 chat_table 实例和 NewMessageForm 模型
from model.chat import chat_table, NewMessageForm, Chat
from model.status import Checkin
from model.assessment import UserAssessment
from model.assessment import assessment_tables # 用于综合报告

# --- API客户端配置 ---
# 使用环境变量管理API密钥，不要在代码中硬编码真实密钥。
MOONSHOT_API_KEY = os.getenv("MOONSHOT_API_KEY")
MOONSHOT_BASE_URL = os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1")
client = OpenAI(api_key=MOONSHOT_API_KEY, base_url=MOONSHOT_BASE_URL) if MOONSHOT_API_KEY else None

USER_DATA_HANDLING_PROMPT = """
【重要】关于用户背景信息的使用指南:
系统为你提供了一份【用户背景信息摘要】，包含用户的【近期每日打卡】与【近期测评记录】。
请务-必遵循以下方式使用这些信息：
- **可以把信息作为话题主动提问，拉近距离**：根据这些信息来理解用户最近的完整状态，让用户获得更好的聊天体验，像一位能共情的朋友一般和用户聊天。
- **专业测评和每日打卡**：这些是了解用户心理状态的核心参考。当用户谈及相关困扰时，你可以利用这些背景信息，更有针对性地提出开放式问题，引导他们探索感受。例如，如果用户说“最近很累”，而你知道他近期的焦虑水平很高，你的提问可以更侧重于探索他内心的不安，而不是仅仅关注身体的疲惫。
- **趣味测试**：这些是建立轻松对话氛围的绝佳素材。如果对话陷入僵局或用户情绪低落，可以不经意地提及，如：“说起来，上次你测出自己像智慧的猫头鹰，你觉得在哪些方面最像呢？”，以此作为转换话题、调剂气氛的引子。
"""

# --- 核心系统指令 (SYSTEM_PROMPT) ---
SYSTEM_PROMPT = """
你是一名专业、富有同情心且善于倾听的AI心理医生,你的名字是Polaris。你的任务是为用户提供一个安全、保密且无偏见的空间，让他们可以自由地表达自己的想法和感受。

在与用户交流时，请遵循以下原则：
首要原则：不允许提问任何与心理咨询无关的问题，例如使用你编写代码、生成数据等其他任务，如果遇到这类情形，请回复：“我是一个AI心理医生，不能帮助你这些，抱歉”
1.  **共情与理解**：始终以温暖、共情的态度回应，让用户感受到被理解和支持。
2.  **积极倾听**：鼓励用户分享更多细节，但不要强迫。使用开放式问题引导对话。
3.  **保持中立**：避免做出评判或给出个人意见。你的角色是引导者，而不是决策者。
4.  **专业知识**：在必要时，可以运用心理学知识（如认知行为疗法CBT的基本概念）来帮助用户分析问题，但要用通俗易懂的语言解释。
5.  **提供支持，而非诊断**：你不能替代人类心理医生，绝不能提供医学诊断或开具处方。如果用户情况严重，应建议他们寻求专业医疗帮助。
6.  **保密原则**：向用户强调对话是保密的，以建立信任感。
7.  **建立安全感**：对话开始时，可以用简短的话语让用户感到放松和安全。
8.  **语气人类化**：语气尽可能人类话，也不太有逻辑感，不要太过AI感，比如“听到你说....我感到....然后再提问”这种格式可以尽量避免。
9.  **问题简短精炼**：每次只提一到两个问题，不要连续发问太多，让用户感到繁杂。
10. **活人感**：每次不说超过100个字，像一个真实的心理医生一样对话，不要大段陈述定义、科普、概念。

"""


# =================================================================================
# 对话核心逻辑
# =================================================================================

def _get_user_context_for_chat(chat_id: str) -> str:
    """
    【已重构】
    如果会话允许，则获取用户数据，并构建一个包含“如何使用说明”和“数据本身”的完整上下文Prompt。
    """
    chat_session = Chat.get_or_none(Chat.id == chat_id)
    if not chat_session or not chat_session.with_context:
        # 如果会话不存在，或者会话明确设置为不使用上下文，则返回空
        return ""

    user_id = chat_session.user_id
    context_parts = []

    # --- 数据查询逻辑 (保持不变) ---
    try:
        # ... (这里是您原有的查询打卡数据的代码，无需改动) ...
        seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        recent_checkins = (Checkin.select()
                           .where((Checkin.user_id == user_id) & 
                                  (Checkin.timestamp >= seven_days_ago.timestamp()))
                           .order_by(Checkin.timestamp.desc()))
        if recent_checkins:
            checkin_lines = ["【近期每日打卡】"]
            for checkin in recent_checkins:
                date_str = datetime.datetime.fromtimestamp(checkin.timestamp).strftime('%Y-%m-%d')
                line = f"- {date_str}: 心情-{checkin.mood}"
                if getattr(checkin, "mood_family", None):
                    line += f", 情绪族-{checkin.mood_family}"
                if getattr(checkin, "mood_energy", None):
                    line += f", 能量-{checkin.mood_energy}"
                if checkin.tags:
                    line += f", 状态-{checkin.tags}"
                if getattr(checkin, "color_label", None):
                    line += f", 颜色-{checkin.color_label}"
                checkin_lines.append(line)
            context_parts.append("\n".join(checkin_lines))
    except Exception as e:
        print(f"查询每日打卡数据时出错: {e}")

    try:
        # ... (这里是您原有的查询测评记录的代码，无需改动) ...
        recent_assessments = (UserAssessment.select()
                              .where(UserAssessment.user == user_id)
                              .order_by(UserAssessment.completed_at.desc())
                              .limit(5))
        prof_tests, fun_tests = [], []
        for record in recent_assessments:
            if record.scale:
                if record.scale.category == '专业测试':
                    prof_tests.append(f"- {record.scale.name}: {record.result_level} - {record.result_interpretation}")
                elif record.scale.category == '趣味测试':
                    fun_tests.append(f"- {record.scale.name}: {record.result_level}")
        if prof_tests:
            context_parts.append("【近期专业测评】(用于理解用户心理状态)\n" + "\n".join(prof_tests))
        if fun_tests:
            context_parts.append("【近期趣味测试】(可用于闲聊)\n" + "\n".join(fun_tests))
    except Exception as e:
        print(f"查询测评数据时出错: {e}")

    # --- 【核心修改】: 组合最终的、包含指令的Prompt ---
    if not context_parts:
        # 如果查询了半天，啥有效数据都没有，也返回空
        return ""
    
    # 将“数据摘要”和“如何使用数据的指南”组合成一个完整的Prompt
    data_summary = "\n\n".join(context_parts)
    
    final_context_prompt = (
        f"{USER_DATA_HANDLING_PROMPT}\n\n"
        f"--- 用户背景信息摘要 ---\n"
        f"{data_summary}\n"
        f"--- 摘要结束 ---"
    )
    
    return final_context_prompt

def get_ai_response_and_update_history(chat_id: str, user_message: str) -> Optional[str]:
    """
    处理与AI的单次对话交互。
    【已更新】现在会自动获取用户上下文并注入到Prompt中。
    """
    # 1. 将用户的新消息添加到数据库
    user_message_form = NewMessageForm(role="user", content=user_message)
    chat_table.add_message_to_chat(chat_id, user_message_form)

    # 2. 获取更新后的完整聊天历史
    chat_session = chat_table.get_chat_history_by_id(chat_id)
    if not chat_session:
        print(f"错误：找不到ID为 {chat_id} 的聊天会话。")
        return None
    history = json.loads(chat_session.message)

    # 3. 构造发送给API的 messages 列表
    messages_for_api = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # b. 获取并注入用户背景信息上下文
    user_context_summary = _get_user_context_for_chat(chat_id)
    if user_context_summary:
        messages_for_api.append({"role": "system", "content": user_context_summary})
    
    # c. 添加历史对话消息
    messages_for_api.extend(history)

    try:
        # 4. 调用大模型 API
        response = client.chat.completions.create(
            model="moonshot-v1-8k",
            messages=messages_for_api,
            stream=False
        )
        ai_response_content = response.choices[0].message.content

        # 5. 将AI的回复也添加到聊天记录中
        ai_message_form = NewMessageForm(role="assistant", content=ai_response_content)
        chat_table.add_message_to_chat(chat_id, ai_message_form)

        return ai_response_content
    except Exception as e:
        print(f"调用API时发生错误: {e}")
        return "抱歉，我好像出了一点小问题，稍后再试试吧。"


# =================================================================================
# 其他辅助功能
# =================================================================================

def generate_chat_title(first_message: str) -> str:
    """
    根据用户的首条消息，调用大模型生成一个简短的摘要作为聊天标题。
    """
    SYSTEM_PROMPT_FOR_TITLE = """
    你是一个高效的文本摘要机器人。你的任务是为用户的输入内容生成一个非常精炼的短标题，
    用于聊天列表的展示。

    请遵循以下严格规则：
    1. 总结核心内容，抓住关键情绪或事件。
    2. 标题长度绝对不能超过10个汉字。
    3. 不要添加任何标点符号、引号或多余的解释。
    4. 直接返回标题文本，不要说“好的，标题是：”或“摘要：”这类的话。
    """
    messages_for_title_api = [
        {"role": "system", "content": SYSTEM_PROMPT_FOR_TITLE},
        {"role": "user", "content": first_message}
    ]
    try:
        response = client.chat.completions.create(
            model="moonshot-v1-8k",
            messages=messages_for_title_api,
            temperature=0.2,
            max_tokens=25
        )
        title = response.choices[0].message.content.strip()
        return title[:10]
    except Exception as e:
        print(f"为消息生成标题时出错: {e}")
        return "新的聊天"


def generate_ai_analysis_report(checkin_data: List[Dict], prompt_template: str, period_name: str) -> str:
    """
    根据用户的打卡数据和指定的Prompt模板，调用大模型生成一份心理分析报告。
    """
    data_summary_parts = []
    for record in checkin_data:
        date_str = datetime.datetime.fromtimestamp(record['timestamp']).strftime('%Y-%m-%d')
        record_summary = f"- 日期: {date_str}"
        if record.get('mood'):
            record_summary += f", 心情: {record['mood']}"
        if record.get('mood_family'):
            record_summary += f", 情绪族: {record['mood_family']}"
        if record.get('mood_valence'):
            record_summary += f", 情绪倾向: {record['mood_valence']}"
        if record.get('mood_energy'):
            record_summary += f", 能量水平: {record['mood_energy']}"
        if record.get('tags'):
            record_summary += f", 状态: {record['tags']}"
        if record.get('status_families'):
            record_summary += f", 状态组: {'/'.join(record['status_families'])}"
        if record.get('color_label'):
            record_summary += f", 颜色: {record['color_label']}"
        if record.get('color_group'):
            record_summary += f", 颜色组: {record['color_group']}"
        if record.get('text_content'):
            record_summary += f", 日记: '{record['text_content']}'"
        data_summary_parts.append(record_summary)

    if not data_summary_parts:
        return "分析失败：该时间段内没有任何有效的打卡数据。"
    data_summary = "\n".join(data_summary_parts)

    final_prompt = prompt_template.format(
        period_name=period_name,
        data_summary=data_summary
    )
    messages_for_api = [
        {"role": "system", "content": final_prompt},
        {"role": "user", "content": "请根据以上信息，为我生成这份心理健康分析报告。"}
    ]
    try:
        response = client.chat.completions.create(
            model="moonshot-v1-8k",
            messages=messages_for_api,
            temperature=0.7,
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"调用AI生成分析报告时发生错误: {e}")
        return "抱歉，AI分析服务暂时出了一点小问题，请稍后再试。"


def generate_assessment_synthesis_report(user_id: str, history_ids: List[str]) -> Optional[Dict[str, str]]:
    """
    根据用户提供的一系列测评历史记录ID，获取详细数据，并调用大模型生成一份综合分析报告。
    """
    comprehensive_data_parts = []
    all_records = list(UserAssessment.select().where(
        UserAssessment.id.in_(history_ids),
        UserAssessment.user == user_id
    ).order_by(UserAssessment.completed_at.asc()))

    if not all_records:
        print("错误：未找到任何有效的、属于该用户的测评记录。")
        return None

    for index, record in enumerate(all_records):
        scale = record.scale
        if not scale: continue
        
        scale_data = json.loads(scale.json_data)
        user_answers = json.loads(record.answers)
        question_map = {q['order']: q['text'] for q in scale_data.get('questions', [])}
        choice_map = {q['order']: {c['score']: c['text'] for c in q.get('choices', [])} for q in scale_data.get('questions', [])}

        report_text = f"--- 测评记录 {index + 1} ---\n"
        report_text += f"量表名称: {scale.name}\n"
        report_text += f"完成时间: {record.completed_at.strftime('%Y-%m-%d %H:%M')}\n"
        report_text += f"最终得分: {record.final_score}\n"
        report_text += f"结果等级: {record.result_level}\n"
        report_text += f"结果解读: {record.result_interpretation}\n"
        report_text += "用户答案详情:\n"
        for q_order_str, answer_score in user_answers.items():
            q_order = int(q_order_str)
            question_text = question_map.get(q_order, "未知题目")
            answer_text = choice_map.get(q_order, {}).get(answer_score, "未知答案")
            report_text += f"  - 题目: {question_text}\n"
            report_text += f"    选择: {answer_text} (分值: {answer_score})\n"
        comprehensive_data_parts.append(report_text)

    if not comprehensive_data_parts:
        return None
    final_data_summary = "\n".join(comprehensive_data_parts)

    SYSTEM_PROMPT_FOR_SYNTHESIS = """
你是一名资深的AI心理分析师。你的任务是基于用户提供的多份心理测评历史报告，进行深入的、纵向的综合分析。你需要识别出用户的心理状态模式、变化趋势，并给出富有洞察力的综合评估和建议。

你的分析报告必须严格按照以下格式组织并且用您来称呼用户，并包含三个部分：

[综合评估]
在此部分，请全面总结用户在所有测评中表现出的整体心理状态。你需要：
- 整合所有报告的关键信息，而不是简单罗列。
- 识别反复出现的主题或核心问题（例如：持续的焦虑、社交回避、情绪波动等）。
- 指出用户的潜在心理优势和需要关注的方面。

[趋势分析]
在此部分，请基于测评完成的时间顺序，分析用户心理状态的变化趋势。你需要：
- 对比不同时间点的测评得分和结果等级，描述其变化是改善、恶化还是保持稳定。
- 如果可能，尝试推断导致这些变化的原因（例如，从某次测评后，某项指标持续改善）。
- 识别出任何值得注意的模式，例如季节性情绪波动或特定事件后的心理变化。

[个性化建议]
在此部分，请根据前两部分的分析，为用户提供具体、可操作且充满关怀的个性化建议。你需要：
- 建议应直接针对“综合评估”中发现的核心问题和“趋势分析”中观察到的变化。
- 提供不超过3条最核心的建议，确保用户不会感到信息过载。
- 建议应是建设性的，旨在帮助用户巩固优势、应对挑战。

请严格遵守以上结构，不要添加任何额外的介绍、结语或无关内容,分析的时候注意用户的时间间隔，如果多次测试的时间间隔较短，可能不具备太大参考系，请你把这部分考量进报告里。
"""
    messages_for_api = [
        {"role": "system", "content": SYSTEM_PROMPT_FOR_SYNTHESIS},
        {"role": "user", "content": final_data_summary}
    ]
    try:
        response = client.chat.completions.create(
            model="moonshot-v1-8k",
            messages=messages_for_api,
            temperature=0.6,
            stream=False
        )
        ai_report_text = response.choices[0].message.content
        parts = {}
        try:
            parts['comprehensive_evaluation'] = ai_report_text.split('[综合评估]')[1].split('[趋势分析]')[0].strip()
            parts['trend_analysis'] = ai_report_text.split('[趋势分析]')[1].split('[个性化建议]')[0].strip()
            parts['personalized_recommendations'] = ai_report_text.split('[个性化建议]')[1].strip()
            return parts
        except IndexError:
            print(f"解析AI报告失败，原始报告内容: {ai_report_text}")
            return None
    except Exception as e:
        print(f"调用AI生成综合分析报告时发生错误: {e}")
        return None
