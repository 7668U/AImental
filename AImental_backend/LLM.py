# LLM.py

import os
import json
from openai import OpenAI
from typing import Optional, List, Dict
import datetime

# --- 【1. 新增导入】 ---
from model.user import user_table
from model.history_analysis import format_user_data_for_prompt
# --- ----------- ---

from model.chat import chat_table, NewMessageForm

# --- 配置 ---
MOONSHOT_API_KEY = os.getenv("MOONSHOT_API_KEY", "sk-6gGW4lyWgHbvwFO8My2d1ivCkFY77iFBthp3J6TIolfAtJm3")
MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1"
client = OpenAI(api_key=MOONSHOT_API_KEY, base_url=MOONSHOT_BASE_URL)

# --- 【2. 修改】基础的系统指令保持不变 ---
BASE_SYSTEM_PROMPT = """
你是一名专业、富有同情心且善于倾听的AI心理医生。你的任务是为用户提供一个安全、保密且无偏见的空间，让他们可以自由地表达自己的想法和感受。

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
"""

# --- 【3. 修改】核心函数，增加 user_id 参数并动态构建Prompt ---
def get_ai_response_and_update_history(chat_id: str, user_id: str, user_message: str) -> Optional[str]:
    """
    处理与AI的单次对话交互，并根据用户授权动态构建System Prompt。
    """
    user_message_form = NewMessageForm(role="user", content=user_message)
    chat_table.add_message_to_chat(chat_id, user_message_form)

    chat_session = chat_table.get_chat_history_by_id(chat_id)
    if not chat_session:
        print(f"错误：找不到ID为 {chat_id} 的聊天会话。")
        return None

    history = json.loads(chat_session.message)

    # --- 动态构建 System Prompt 的核心逻辑 ---
    final_system_prompt = BASE_SYSTEM_PROMPT
    user = user_table.get_user_by_id(user_id)

    # 只有在用户存在且明确授权时，才添加额外信息
    if user and user.allow_ai_read_data:
        print(f"[LLM] 用户 {user_id} 已授权，正在为其准备个性化信息...")
        try:
            background_info = format_user_data_for_prompt(user_id)
            # 将背景信息和基础指令拼接起来
            final_system_prompt = f"{BASE_SYSTEM_PROMPT}\n\n---\n\n{background_info}"
            print(f"[LLM] 已成功为用户 {user_id} 添加个性化背景信息。")
        except Exception as e:
            print(f"[LLM] 警告：为用户 {user_id} 获取个性化信息时出错: {e}。将使用默认Prompt。")
            # 出错时，保持使用基础Prompt，保证服务可用性
            final_system_prompt = BASE_SYSTEM_PROMPT
    else:
        print(f"[LLM] 用户 {user_id} 未授权，使用默认Prompt。")

    messages_for_api = [{"role": "system", "content": final_system_prompt}]
    messages_for_api.extend(history)

    try:
        response = client.chat.completions.create(
            model="moonshot-v1-8k",
            messages=messages_for_api,
            stream=False
        )
        ai_response_content = response.choices[0].message.content
        ai_message_form = NewMessageForm(role="assistant", content=ai_response_content)
        chat_table.add_message_to_chat(chat_id, ai_message_form)
        return ai_response_content
    except Exception as e:
        print(f"调用API时发生错误: {e}")
        return "抱歉，我好像出了一点小问题，稍后再试试吧。"

# --- 其他函数保持不变 ---

def generate_chat_title(first_message: str) -> str:
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

# ... (generate_ai_analysis_report 和 generate_assessment_synthesis_report 保持不变) ...

def generate_ai_analysis_report(checkin_data: List[Dict], prompt_template: str, period_name: str) -> str:
    data_summary_parts = []
    for record in checkin_data:
        date_str = datetime.datetime.fromtimestamp(record['timestamp']).strftime('%Y-%m-%d')
        record_summary = f"- 日期: {date_str}"
        if record.get('mood'): record_summary += f", 心情: {record['mood']}"
        if record.get('tags'): record_summary += f", 标签: {record['tags']}"
        if record.get('text_content'): record_summary += f", 日记: '{record['text_content']}'"
        data_summary_parts.append(record_summary)

    if not data_summary_parts:
        return "分析失败：该时间段内没有任何有效的打卡数据。"

    data_summary = "\n".join(data_summary_parts)
    final_prompt = prompt_template.format(period_name=period_name, data_summary=data_summary)

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

from model.assessment import UserAssessment

def generate_assessment_synthesis_report(user_id: str, history_ids: List[str]) -> Optional[Dict[str, str]]:
    comprehensive_data_parts = []
    all_records = list(UserAssessment.select().where(
        UserAssessment.id.in_(history_ids),
        UserAssessment.user == user_id
    ).order_by(UserAssessment.completed_at.asc()))

    if not all_records: return None

    for index, record in enumerate(all_records):
        if not (scale := record.scale): continue
        
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
            report_text += f"  - 题目: {question_text}\n    选择: {answer_text} (分值: {answer_score})\n"
            
        comprehensive_data_parts.append(report_text)

    if not comprehensive_data_parts: return None
        
    final_data_summary = "\n".join(comprehensive_data_parts)

    SYSTEM_PROMPT_FOR_SYNTHESIS = """...""" # (保持不变)

    messages_for_api = [
        {"role": "system", "content": SYSTEM_PROMPT_FOR_SYNTHESIS},
        {"role": "user", "content": final_data_summary}
    ]

    try:
        response = client.chat.completions.create(
            model="moonshot-v1-8k", messages=messages_for_api, temperature=0.6
        )
        ai_report_text = response.choices[0].message.content
        parts = {}
        eval_part = ai_report_text.split('[综合评估]')[1].split('[趋势分析]')[0].strip()
        trend_part = ai_report_text.split('[趋势分析]')[1].split('[个性化建议]')[0].strip()
        reco_part = ai_report_text.split('[个性化建议]')[1].strip()
        parts['comprehensive_evaluation'] = eval_part
        parts['trend_analysis'] = trend_part
        parts['personalized_recommendations'] = reco_part
        return parts
    except Exception as e:
        print(f"解析或调用AI报告时出错: {e}")
        return None
