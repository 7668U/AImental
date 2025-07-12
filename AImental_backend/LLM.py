# LLM.py

import os
import json
from openai import OpenAI
from typing import Optional

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
DEEPSEEK_API_KEY = "sk-b55d99ca5c3f41058f8f3e6380b41dac"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# 初始化 DeepSeek API 客户端
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

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
8.  **语气人类化**：语气尽可能人类话，不要太过AI感。
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
            model="deepseek-chat",  # 使用适合对话的模型
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
            model="deepseek-chat",
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