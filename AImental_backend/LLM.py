# LLM.py

import os
import json
from openai import OpenAI
from typing import Optional, List, Dict
import datetime
# 从你的 chat.py 文件中导入 chat_table 实例和 NewMessageForm 模型
# 假设 LLM.py 和 chat.py 在同一个目录下
from model.chat import chat_table, NewMessageForm

# --- 配置 ---
# 强烈建议使用环境变量来管理你的 API 密钥，而不是硬编码在代码里
# 你可以在系统环境中设置 'DEEPSEEK_API_KEY'
# 或者在项目根目录创建一个 .env 文件，并使用 python-dotenv 库加载
# pip install python-dotenv
# from dotenv import load_dotenv
# load_dotenv()


# DEEPSEEK_API_KEY = "sk-3a432e1f477845c085c01a3f77545b3f"
# DEEPSEEK_BASE_URL = "https://api.deepseek.com"
# 初始化 DeepSeek API 客户端
# client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

# export MOONSHOT_API_KEY="sk-..."
MOONSHOT_API_KEY = "sk-6gGW4lyWgHbvwFO8My2d1ivCkFY77iFBthp3J6TIolfAtJm3" 
MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1"
# 初始化 Kimi (Moonshot AI) API 客户端
client = OpenAI(api_key=MOONSHOT_API_KEY, base_url=MOONSHOT_BASE_URL)

# AI心理医生的系统指令 (System Prompt)
# 这是非常关键的一步，它定义了AI的角色、语气和行为准则
SYSTEM_PROMPT = """
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

def get_ai_response_and_update_history(chat_id: str, user_message: str) -> Optional[str]:
    """
    处理与AI的单次对话交互。

    该函数完成以下操作：
    1. 将用户的新消息添加到数据库。
    2. 从数据库获取完整的聊天历史。
    3. 调用大模型API获取回复。
    4. 将AI的回复添加到数据库。
    5. 返回AI的回复内容。

    Args:
        chat_id (str): 当前聊天的唯一ID。
        user_message (str): 用户发送的最新消息内容。

    Returns:
        Optional[str]: 成功时返回AI的回复字符串，失败则返回None。
    """
    # --- 1. 将用户的最新消息添加到聊天记录中 ---
    user_message_form = NewMessageForm(role="user", content=user_message)
    chat_table.add_message_to_chat(chat_id, user_message_form)

    # --- 2. 获取更新后的完整聊天历史 ---
    chat_session = chat_table.get_chat_history_by_id(chat_id)
    if not chat_session:
        print(f"错误：找不到ID为 {chat_id} 的聊天会话。")
        return None

    # 从数据库取出的 message 是 JSON 字符串，需要解析为 Python 列表
    history = json.loads(chat_session.message)

    # --- 3. 构造发送给API的 messages 列表 ---
    # 在最前面插入系统指令，来设定AI的角色
    messages_for_api = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages_for_api.extend(history)

    try:
        # --- 4. 调用 DeepSeek API ---
        response = client.chat.completions.create(
            model="moonshot-v1-8k",  # 使用适合对话的模型
            messages=messages_for_api,
            stream=False  # 根据你的需求，也可以设置为 True 进行流式传输
        )

        ai_response_content = response.choices[0].message.content

        # --- 5. 将AI的回复也添加到聊天记录中 ---
        ai_message_form = NewMessageForm(role="assistant", content=ai_response_content)
        chat_table.add_message_to_chat(chat_id, ai_message_form)

        # --- 6. 返回AI的回复 ---
        return ai_response_content

    except Exception as e:
        print(f"调用API时发生错误: {e}")
        # 这里可以根据需要添加更复杂的错误处理逻辑
        return "抱歉，我好像出了一点小问题，稍后再试试吧。"

def generate_chat_title(first_message: str) -> str:
    """
    根据用户的首条消息，调用大模型生成一个简短的摘要作为聊天标题。

    Args:
        first_message (str): 用户发送的第一条消息内容。

    Returns:
        str: 返回一个10个字以内的摘要标题。如果生成失败，则返回一个默认标题。
    """
    # --- 专用于生成标题的系统指令 ---
    # 这个指令非常直接，告诉AI它的唯一任务就是做摘要，并规定了严格的格式。
    SYSTEM_PROMPT_FOR_TITLE = """
    你是一个高效的文本摘要机器人。你的任务是为用户的输入内容生成一个非常精炼的短标题，
    用于聊天列表的展示。

    请遵循以下严格规则：
    1. 总结核心内容，抓住关键情绪或事件。
    2. 标题长度绝对不能超过10个汉字。
    3. 不要添加任何标点符号、引号或多余的解释。
    4. 直接返回标题文本，不要说“好的，标题是：”或“摘要：”这类的话。
    """

    # 构造仅用于生成标题的API消息列表
    messages_for_title_api = [
        {"role": "system", "content": SYSTEM_PROMPT_FOR_TITLE},
        {"role": "user", "content": first_message}
    ]

    try:
        # --- 调用 DeepSeek API 来生成标题 ---
        response = client.chat.completions.create(
            model="moonshot-v1-8k",
            messages=messages_for_title_api,
            temperature=0.2,  # 使用较低的温度，让标题生成更具确定性
            max_tokens=25     # 限制最大输出长度，节省token
        )

        # 提取并清理AI返回的标题内容
        title = response.choices[0].message.content.strip()

        # 再次确认，确保标题不会超过10个字符
        return title[:10]

    except Exception as e:
        print(f"为消息生成标题时出错: {e}")
        # 如果API调用失败，返回一个安全的默认标题
        return "新的聊天"
    
    

def generate_ai_analysis_report(checkin_data: List[Dict], prompt_template: str, period_name: str) -> str:
    """
    根据用户的打卡数据和指定的Prompt模板，调用大模型生成一份心理分析报告。

    Args:
        checkin_data (List[Dict]): 从数据库查询出的打卡记录列表。
        prompt_template (str): 一个包含 {period_name} 和 {data_summary} 占位符的字符串模板。
        period_name (str): 时间段的名称，例如 "2025年7月", "2025年第三季度"。

    Returns:
        str: 大模型生成的分析报告文本。如果失败则返回错误提示。
    """
    # --- 1. 将结构化的打卡数据转换为简洁的文本摘要 ---
    # 这个步骤至关重要，它将数据整理成对LLM友好的格式，并过滤掉空数据以节省Token
    data_summary_parts = []
    for record in checkin_data:
        # 将Unix时间戳转换为日期字符串
        date_str = datetime.datetime.fromtimestamp(record['timestamp']).strftime('%Y-%m-%d')
        
        # 只添加存在的数据项，确保摘要的紧凑性
        record_summary = f"- 日期: {date_str}"
        if record.get('mood'):
            record_summary += f", 心情: {record['mood']}"
        if record.get('tags'):
            record_summary += f", 标签: {record['tags']}"
        if record.get('text_content'):
            record_summary += f", 日记: '{record['text_content']}'"
        
        data_summary_parts.append(record_summary)

    # 如果没有任何数据，提前返回
    if not data_summary_parts:
        return "分析失败：该时间段内没有任何有效的打卡数据。"

    data_summary = "\n".join(data_summary_parts)

    # --- 2. 使用模板构建最终的系统指令 (System Prompt) ---
    final_prompt = prompt_template.format(
        period_name=period_name,
        data_summary=data_summary
    )

    # --- 3. 构造发送给API的 messages 列表 ---
    messages_for_api = [
        {"role": "system", "content": final_prompt},
        {"role": "user", "content": "请根据以上信息，为我生成这份心理健康分析报告。"}
    ]

    try:
        # --- 4. 调用 DeepSeek API ---
        response = client.chat.completions.create(
            model="moonshot-v1-8k",
            messages=messages_for_api,
            temperature=0.7,  # 使用稍高的温度，让报告更具创造性和个性
            stream=False
        )
        ai_report = response.choices[0].message.content
        return ai_report

    except Exception as e:
        print(f"调用AI生成分析报告时发生错误: {e}")
        return "抱歉，AI分析服务暂时出了一点小问题，请稍后再试。"
    
    

# =================================================================================
# 以下是新增的函数，用于生成用户多份历史测评的综合分析报告
# =================================================================================

from model.assessment import assessment_tables, UserAssessment 
import json

# ... (other functions like get_ai_response_and_update_history, etc.) ...


# ✅ 2. 【替换旧函数】用下面这个修正后的完整函数，替换掉旧的 generate_assessment_synthesis_report
def generate_assessment_synthesis_report(user_id: str, history_ids: List[str]) -> Optional[Dict[str, str]]:
    """
    根据用户提供的一系列测评历史记录ID，获取详细数据，并调用大模型生成一份综合分析报告。

    Args:
        user_id (str): 发起请求的用户ID，用于安全校验。
        history_ids (List[str]): 用户选择用于分析的测评记录ID列表 (UserAssessment IDs)。

    Returns:
        Optional[Dict[str, str]]: 一个包含'comprehensive_evaluation', 'trend_analysis', 
                                   'personalized_recommendations'三个键的字典。如果失败则返回None。
    """
    # --- 1. 数据准备：获取并格式化所有相关的测评详情 ---
    comprehensive_data_parts = []
    
    # 【已修复】直接从 UserAssessment 模型本身进行查询，而不是通过 assessment_tables 实例
    all_records = list(UserAssessment.select().where(
        UserAssessment.id.in_(history_ids),
        UserAssessment.user == user_id
    ).order_by(UserAssessment.completed_at.asc()))

    if not all_records:
        print("错误：未找到任何有效的、属于该用户的测评记录。")
        return None

    for index, record in enumerate(all_records):
        scale = record.scale
        if not scale:
            continue
        
        scale_data = json.loads(scale.json_data)
        user_answers = json.loads(record.answers)
        
        question_map = {q['order']: q['text'] for q in scale_data.get('questions', [])}
        
        choice_map = {}
        for q in scale_data.get('questions', []):
            choice_map[q['order']] = {c['score']: c['text'] for c in q.get('choices', [])}

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

    # --- 2. Prompt工程：设计一个专门用于综合分析的系统指令 ---
    SYSTEM_PROMPT_FOR_SYNTHESIS = """
你是一名资深的AI心理分析师。你的任务是基于用户提供的多份心理测评历史报告，进行深入的、纵向的综合分析。你需要识别出用户的心理状态模式、变化趋势，并给出富有洞察力的综合评估和建议。

你的分析报告必须严格按照以下格式组织，并包含三个部分：

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

请严格遵守以上结构，不要添加任何额外的介绍、结语或无关内容。
"""

    # --- 3. 构造并调用大模型API ---
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

        # --- 4. 解析AI返回的结构化报告 ---
        parts = {}
        try:
            eval_part = ai_report_text.split('[综合评估]')[1].split('[趋势分析]')[0].strip()
            trend_part = ai_report_text.split('[趋势分析]')[1].split('[个性化建议]')[0].strip()
            reco_part = ai_report_text.split('[个性化建议]')[1].strip()
            
            parts['comprehensive_evaluation'] = eval_part
            parts['trend_analysis'] = trend_part
            parts['personalized_recommendations'] = reco_part
            
            return parts
        except IndexError:
            print(f"解析AI报告失败，原始报告内容: {ai_report_text}")
            return None

    except Exception as e:
        print(f"调用AI生成综合分析报告时发生错误: {e}")
        return None