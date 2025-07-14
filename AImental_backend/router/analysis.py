# routers/analysis.py

import json
import jieba # 导入jieba
from fastapi import APIRouter, Depends, HTTPException, Path
from typing import Any, Dict, List, Tuple
from collections import Counter
from itertools import chain

# 从 model 导入所有需要的模块
from model.analysis import (
    analysis_table,
    MoodAnalysisContent,
    TagMoodAnalysisContent,
    WordCloudAnalysisContent,
    ColorPaletteAnalysisContent
)
from model.status import checkin_table

# 认证依赖
from .auth import get_current_user_id

from LLM import generate_ai_analysis_report
# 导入Pydantic基础模型
from pydantic import BaseModel
import datetime
import calendar

# ===================================================
# 1. 路由和辅助数据
# ===================================================
router = APIRouter(
    prefix="/report",
    tags=["Analysis - 数据分析报告"],
    dependencies=[Depends(get_current_user_id)]
)

# --- 辅助数据 ---
# 中文停用词表 (一个简单的版本，您可以根据需要扩展)
STOPWORDS = {
    '的', '了', '我', '你', '他', '她', '它', '我们', '你们', '他们', '是', '在', '有', '也',
    '不', '都', '就', '还', '个', '一', '很', '什么', '怎么', '这个', '那个', '今天', '一个'
}

# 情绪色彩名称映射 (您可以自定义更丰富的名称)
COLOR_NAME_MAP = {
    '#FFC107': '暖阳橙', '#81D4FA': '晴空蓝', '#A5D6A7': '薄荷绿',
    '#B0BEC5': '烟波灰', '#F48FB1': '落樱粉', '#C5CAE9': '香芋紫',
    '#FF8A80': '珊瑚红', '#FFF59D': '柠檬黄', '#80CBC4': '青碧色',
    '#7986CB': '鸢尾蓝', '#BCAAA4': '奶咖棕', '#F5F5F5': '云朵白'
}


# ===================================================
# 2. 【全新】为四个独立报告设计的 AI PROMPT 模板
# ===================================================
# 每套Prompt都为AI设定了独特的专家角色和分析任务
AI_DETAILED_PROMPTS = {
    "mood": """
你是一位精通**情绪心理学**的AI分析师。你的任务是深入解读用户在 **{period_name}** 内的**心情(mood)**数据，生成一份专业、温暖的情绪状态报告。

**你的任务:**
1.  **角色**: 情绪心理学专家。
2.  **核心分析对象**: 仅限`mood`字段。
3.  **报告重点**:
    - 总结最主要的情绪，并解读这种主导情绪可能代表的心理状态。
    - 分析情绪的多样性。情绪种类是丰富还是单一？这说明了什么？
    - 观察情绪的波动性。情绪变化是平缓还是剧烈？这背后可能有哪些原因？
    - 基于情绪分布，发现用户的潜在优势（如情绪稳定、能快速恢复等）并给予鼓励。
    - 提供1-2个针对性的、与情绪调节相关的实用小技巧。

**用户的打卡数据摘要如下 (你只需关注 mood 字段):**
---
{data_summary}
---
""",
    "tag-mood": """
你是一位**行为心理学**和**生活方式**领域的AI顾问。你的任务是深入分析用户在 **{period_name}** 内的**活动标签(tags)**与**心情(mood)**之间的关联，揭示生活方式对情绪的深层影响。

**你的任务:**
1.  **角色**: 行为心理学顾问。
2.  **核心分析对象**: `tags` 和 `mood` 字段的关联。
3.  **报告重点**:
    - 找出用户的“快乐源泉”。哪些活动（标签）最常与积极情绪（如开心、放松）一同出现？
    - 识别潜在的“压力来源”。哪些活动（标签）可能与负面情绪（如疲惫、难过）高度相关？
    - 分析是否存在显著的行为-情绪模式。例如，“运动后总是更开心”或“工作日普遍感到疲惫”。
    - 基于这些发现，表扬用户积极的生活习惯。
    - 提供1-2个关于优化生活方式、趋利避害的温和建议。

**用户的打卡数据摘要如下 (请重点分析 tags 和 mood 的关系):**
---
{data_summary}
---
""",
    "word-cloud": """
你是一位擅长**叙事疗法**的AI心理倾听者。你的任务是通过分析用户在 **{period_name}** 内的**日记内容(text_content)**，解读他们内心的叙事、关注点和潜在的情感需求。

**你的任务:**
1.  **角色**: 叙事治疗师。
2.  **核心分析对象**: 仅限`text_content`字段。
3.  **报告重点**:
    - 从用户的高频词汇中，识别并总结出近期的核心议题或生活焦点。
    - 分析这些关键词所反映的潜在情感或态度。它们是积极的、消极的还是中性的？
    - 用户在日记中是更多地向内探索自我，还是在记录外部事件？
    - 发现并赞美用户在文字中流露出的自我关怀、深刻反思或积极心态。
    - 基于用户的叙事，提出一个开放性的、能引发用户进一步思考的启发性问题。

**用户的打卡数据摘要如下 (你只需关注 text_content 字段):**
---
{data_summary}
---
""",
    "color": """
你是一位富有创意的**色彩心理学**和**艺术疗法**专家。你的任务是解读用户在 **{period_name}** 内所选**颜色(color)**的象征意义，为他们生成一份充满美感和想象力的情绪色彩报告。

**你的任务:**
1.  **角色**: 色彩心理学与艺术疗法专家。
2.  **核心分析对象**: 仅限`color`字段。
3.  **报告重点**:
    - 解读用户最常选择的主色调。这种颜色在色彩心理学中通常象征着什么？它可能反映了用户怎样的潜意识心境？
    - 分析用户选择的色彩组合。这些颜色搭配在一起，像一幅怎样的画？传达了怎样的整体感觉？
    - 将用户的“情绪色板”比喻成一种自然景观、一首诗或一幅画，进行充满艺术感的解读。
    - 给予用户基于色彩的积极心理暗示和祝福。

**用户的打卡数据摘要如下 (你只需关注 color 字段):**
---
{data_summary}
---
"""
}
# ===================================================
# 2. 核心辅助函数
# ===================================================
def _get_period_info(period_type: str, year: int, value: int) -> Tuple[int, int, str]:
    """根据周期类型，计算开始/结束时间戳和周期名称。"""
    if period_type == 'monthly':
        if not 1 <= value <= 12:
            raise HTTPException(status_code=400, detail="月份必须在1-12之间。")
        start_dt = datetime.datetime(year, value, 1)
        _, num_days = calendar.monthrange(year, value)
        end_dt = start_dt + datetime.timedelta(days=num_days)
        period_name = f"{year}年{value}月"
    elif period_type == 'quarterly':
        if not 1 <= value <= 4:
            raise HTTPException(status_code=400, detail="季度必须在1-4之间。")
        start_month = (value - 1) * 3 + 1
        end_month = start_month + 2
        start_dt = datetime.datetime(year, start_month, 1)
        _, end_day = calendar.monthrange(year, end_month)
        end_dt = datetime.datetime(year, end_month, end_day) + datetime.timedelta(days=1)
        period_name = f"{year}年第{value}季度"
    elif period_type == 'yearly':
        start_dt = datetime.datetime(year, 1, 1)
        end_dt = datetime.datetime(year + 1, 1, 1)
        period_name = f"{year}年"
    else:
        raise HTTPException(status_code=400, detail="无效的周期类型。")

    return int(start_dt.timestamp()), int(end_dt.timestamp()), period_name

# ===================================================
# 3. 统一的图表数据接口
# ===================================================
@router.get(
    "/chart/{analysis_type}/{period_type}/{year}/{value}",
    response_model=Any,
    summary="获取用于生成图表的分析数据"
)
def get_chart_data(
    analysis_type: str = Path(..., description="分析模块: 'mood', 'tag-mood', 'word-cloud', 'color'"),
    period_type: str = Path(..., description="周期类型: 'monthly', 'quarterly', 'yearly'"),
    year: int = Path(..., description="年份"),
    value: int = Path(..., description="月份(1-12) 或 季度(1-4)"),
    current_user_id: str = Depends(get_current_user_id),
    force_refresh: bool = False
):
    """
    为所有分析模块提供标准化的图表数据。
    - analysis_type: 'mood', 'tag-mood', 'word-cloud', 'color'
    """
    start_ts, end_ts, period_name = _get_period_info(period_type, year, value)
    period_key = f"{year}-{value}-{period_type}-{analysis_type}-chart"
    
    # 1. 检查缓存
    if not force_refresh:
        cached = analysis_table.get_analysis(current_user_id, period_key, analysis_type)
        if cached:
            return json.loads(cached.content)

    # 2. 获取数据
    checkins = checkin_table.get_checkins_by_period(current_user_id, start_ts, end_ts)
    if not checkins:
        raise HTTPException(status_code=404, detail="该时间段内无打卡记录。")
    
    # 3. 根据类型分发到不同分析函数
    if analysis_type == 'mood':
        result_model = _generate_mood_analysis(checkins, period_name)
    elif analysis_type == 'tag-mood':
        result_model = _generate_tag_mood_analysis(checkins)
    elif analysis_type == 'word-cloud':
        result_model = _generate_word_cloud_analysis(checkins)
    elif analysis_type == 'color':
        result_model = _generate_color_analysis(checkins)
    else:
        raise HTTPException(status_code=400, detail="未知的分析类型。")

    # 4. 存入缓存并返回
    analysis_table.save_analysis(current_user_id, period_key, analysis_type, result_model)
    return result_model

# ===================================================
# 4. 统一的AI分析报告接口
# ===================================================
@router.get(
    "/ai/{analysis_type}/{period_type}/{year}/{value}",
    response_model=Dict[str, str],
    summary="获取针对特定模块的AI深度分析报告"
)
def get_ai_detailed_report(
    analysis_type: str = Path(..., description="分析模块: 'mood', 'tag-mood', 'word-cloud', 'color'"),
    period_type: str = Path(..., description="周期类型: 'monthly', 'quarterly', 'yearly'"),
    year: int = Path(..., description="年份"),
    value: int = Path(..., description="月份(1-12) 或 季度(1-4)"),
    current_user_id: str = Depends(get_current_user_id),
    force_refresh: bool = False
):
    """为所有分析模块提供标准化的AI报告。"""
    if analysis_type not in AI_DETAILED_PROMPTS:
        raise HTTPException(status_code=400, detail="无效的分析模块类型。")

    start_ts, end_ts, period_name = _get_period_info(period_type, year, value)
    period_key = f"{year}-{value}-{period_type}-{analysis_type}-ai"
    cache_type_key = f"ai_report_{analysis_type}"
    
    # 1. 检查缓存
    if not force_refresh:
        cached = analysis_table.get_analysis(current_user_id, period_key, cache_type_key)
        if cached:
            return {"report_text": json.loads(cached.content).get("report_text")}

    # 2. 获取数据
    checkins = checkin_table.get_checkins_by_period(current_user_id, start_ts, end_ts)
    if not checkins:
        raise HTTPException(status_code=404, detail="该时间段内无打卡记录，无法生成AI报告。")

    # 3. 调用LLM生成报告
    prompt_template = AI_DETAILED_PROMPTS[analysis_type]
    report_text = generate_ai_analysis_report(checkins, prompt_template, period_name)

    # 4. 存入缓存并返回
    class AIReportContent(BaseModel):
        report_text: str
    content_model = AIReportContent(report_text=report_text)
    analysis_table.save_analysis(current_user_id, period_key, cache_type_key, content_model)

    return {"report_text": report_text}

# ===================================================
# 5. 各分析模块的具体实现逻辑 (私有函数)
# (这些函数无需修改，因为它们已接收列表作为输入)
# ===================================================
def _generate_mood_analysis(checkins: List[Dict], period_name: str) -> MoodAnalysisContent:
    total_checkins = len(checkins)
    moods_list = [r['mood'] for r in checkins]
    mood_counts = Counter(moods_list)
    dominant_mood = mood_counts.most_common(1)[0][0] if mood_counts else "无"
    mood_distribution = []
    for mood, count in mood_counts.items():
        mood_distribution.append({"name": mood, "value": count, "percent": round((count / total_checkins) * 100, 1)})
    mood_distribution.sort(key=lambda x: x['value'], reverse=True)
    interpretation = f"在{period_name}，你共记录了 {total_checkins} 天。'{dominant_mood}' 是你的主导情绪。"
    return MoodAnalysisContent(total_checkins=total_checkins, dominant_mood=dominant_mood, mood_distribution=mood_distribution, interpretation=interpretation)

def _generate_tag_mood_analysis(checkins: List[Dict]) -> TagMoodAnalysisContent:
    tag_mood_counter, all_moods = {}, set()
    for record in checkins:
        mood, tags_str = record.get('mood'), record.get('tags')
        if not tags_str or not mood: continue
        all_moods.add(mood)
        for tag in [t.strip() for t in tags_str.split(',')]:
            if tag not in tag_mood_counter: tag_mood_counter[tag] = Counter()
            tag_mood_counter[tag][mood] += 1
    if not tag_mood_counter: raise HTTPException(status_code=404, detail="无足够标签数据。")
    categories = list(tag_mood_counter.keys())
    series = [{"name": mood, "data": [tag_mood_counter.get(cat, {}).get(mood, 0) for cat in categories]} for mood in sorted(list(all_moods))]
    interpretation = "我们发现了一些有趣的关联：某些活动似乎总是伴随着特定的心情。"
    return TagMoodAnalysisContent(chart_data={"categories": categories, "series": series}, interpretation=interpretation)

def _generate_word_cloud_analysis(checkins: List[Dict], top_n: int = 30) -> WordCloudAnalysisContent:
    all_text = "".join([r['text_content'] for r in checkins if r.get('text_content')])
    if not all_text.strip(): raise HTTPException(status_code=404, detail="无足够日记内容。")
    words = [word for word in jieba.lcut(all_text) if len(word) > 1 and word not in STOPWORDS]
    word_counts = Counter(words)
    word_list = [{"name": word, "value": count} for word, count in word_counts.most_common(top_n)]
    top_word = word_list[0]['name'] if word_list else "..."
    interpretation = f"在你的日记中，'{top_word}' 是你最常提及的词语。"
    return WordCloudAnalysisContent(word_list=word_list, interpretation=interpretation)

def _generate_color_analysis(checkins: List[Dict]) -> ColorPaletteAnalysisContent:
    total_checkins = len(checkins)
    colors_list = [r['color'] for r in checkins if r.get('color')]
    color_counts = Counter(colors_list)
    color_palette = []
    for hex_code, count in color_counts.most_common(5):
        color_palette.append({"hex": hex_code, "name": COLOR_NAME_MAP.get(hex_code, "自定义色"), "percent": round((count / total_checkins) * 100, 1)})
    top_color_name = color_palette[0]['name'] if color_palette else "五彩斑斓"
    interpretation = f"这是专属于你的'情绪色卡'。'{top_color_name}' 是你最偏爱的色彩。"
    return ColorPaletteAnalysisContent(color_palette=color_palette, interpretation=interpretation)