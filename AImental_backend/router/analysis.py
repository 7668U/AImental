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
from model.checkin_dimensions import (
    COLOR_OPTIONS,
    MOOD_OPTIONS,
    build_status_meta_from_tags,
    get_color_meta,
    get_mood_meta,
)

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

ANALYSIS_SCHEMA_VERSION = "v2"

# --- 辅助数据 ---
# 中文停用词表 (一个简单的版本，您可以根据需要扩展)
STOPWORDS = {
    '的', '了', '我', '你', '他', '她', '它', '我们', '你们', '他们', '是', '在', '有', '也',
    '不', '都', '就', '还', '个', '一', '很', '什么', '怎么', '这个', '那个', '今天', '一个'
}

COLOR_NAME_MAP = {item["hex"].upper(): item["label"] for item in COLOR_OPTIONS}
MOOD_FAMILY_ORDER = list(dict.fromkeys(item["family"] for item in MOOD_OPTIONS))


# ===================================================
# 2. 【全新】为四个独立报告设计的 AI PROMPT 模板
# ===================================================
# 每套Prompt都为AI设定了独特的专家角色和分析任务
AI_DETAILED_PROMPTS = {
    "mood": """
你是一位精通**情绪心理学**的AI分析师。你的任务是深入解读用户在 **{period_name}** 内的**心情(mood)**数据，生成一份专业、温暖的情绪状态报告。

**你的任务:**
1.  **角色**: 情绪心理学专家。
2.  **核心分析对象**: `mood`、`mood_family`、`mood_valence`、`mood_energy`。
3.  **报告重点**:
    - 总结最主要的情绪，并解读这种主导情绪可能代表的心理状态。
    - 分析 6 个情绪族的分布，判断用户更偏明亮愉悦、安稳平静、低落难过、焦虑紧绷、生气受伤还是疲惫麻木。
    - 结合正向/中性/负向和能量水平，识别用户近期是高能紧绷、低能疲惫，还是相对平稳。
    - 基于情绪分布，发现用户的潜在优势（如情绪稳定、能快速恢复等）并给予鼓励。
    - 提供1-2个针对性的、与情绪调节相关的实用小技巧。

**用户的打卡数据摘要如下 (请重点关注心情及其结构化元信息):**
---
{data_summary}
---
""",
    "tag-mood": """
你是一位**行为心理学**和**生活方式**领域的AI顾问。你的任务是深入分析用户在 **{period_name}** 内的**状态(tags/status_ids)**与**心情结构(mood_family/mood_energy/color_group)**之间的关联，揭示日常生活模式与情绪的关系。

**你的任务:**
1.  **角色**: 行为心理学顾问。
2.  **核心分析对象**: 状态标签与情绪族、能量水平、颜色组的关联。
3.  **报告重点**:
    - 注意：状态是“今天在做什么/处于什么模式”，不是直接的情绪原因，不要武断归因。
    - 找出哪些状态常和明亮、平静、低落、焦虑、疲惫等情绪族一起出现。
    - 观察哪些生活模式更容易对应高能量或低能量。
    - 分析状态和颜色组的搭配，例如“出差/加班”常搭配阴雨安静还是紧绷浓郁。
    - 基于这些发现，表扬用户积极的生活习惯。
    - 提供1-2个关于优化生活方式、趋利避害的温和建议。

**用户的打卡数据摘要如下 (请重点分析状态与心情结构的关系):**
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
2.  **核心分析对象**: `color`、`color_label`、`color_group`、`color_tone`。
3.  **报告重点**:
    - 解读用户最常选择的颜色和颜色组，例如暖光明亮、清透自然、柔和梦感、阴雨安静、紧绷浓郁、沉稳大地。
    - 分析用户选择的色彩组合。这些颜色搭配在一起，像一幅怎样的画？传达了怎样的整体感觉？
    - 将用户的“情绪色板”比喻成一种自然景观、一首诗或一幅画，进行充满艺术感的解读。
    - 给予用户基于色彩的积极心理暗示和祝福。

**用户的打卡数据摘要如下 (请重点关注颜色及其结构化元信息):**
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
    period_key = f"{ANALYSIS_SCHEMA_VERSION}-{year}-{value}-{period_type}-{analysis_type}-chart"
    
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
    period_key = f"{ANALYSIS_SCHEMA_VERSION}-{year}-{value}-{period_type}-{analysis_type}-ai"
    cache_type_key = f"{ANALYSIS_SCHEMA_VERSION}_ai_report_{analysis_type}"
    
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
# V2: 支持 24 心情、24 状态、24 色卡的结构化分析。
# ===================================================
def _distribution(counter: Counter, total: int | None = None) -> List[Dict[str, Any]]:
    denominator = total or sum(counter.values())
    if denominator <= 0:
        return []
    items = []
    for name, count in counter.most_common():
        items.append({
            "name": name,
            "value": count,
            "percent": round((count / denominator) * 100, 1)
        })
    return items


def _generate_mood_analysis(checkins: List[Dict], period_name: str) -> MoodAnalysisContent:
    total_checkins = len(checkins)
    moods_list = [r['mood'] for r in checkins if r.get('mood')]
    mood_counts = Counter(moods_list)
    dominant_mood = mood_counts.most_common(1)[0][0] if mood_counts else "无"
    mood_distribution = _distribution(mood_counts, total_checkins)

    family_counts, valence_counts, energy_counts = Counter(), Counter(), Counter()
    for record in checkins:
        meta = get_mood_meta(record.get('mood_id') or record.get('mood'))
        if not meta:
            continue
        family_counts[record.get('mood_family') or meta.get('family', '未归类')] += 1
        valence_counts[record.get('mood_valence') or meta.get('valence', 'unknown')] += 1
        energy_counts[record.get('mood_energy') or meta.get('energy', 'unknown')] += 1

    family_distribution = _distribution(family_counts, total_checkins)
    valence_distribution = _distribution(valence_counts, total_checkins)
    energy_distribution = _distribution(energy_counts, total_checkins)
    dominant_family = family_distribution[0]["name"] if family_distribution else None

    interpretation = (
        f"在{period_name}，你共记录了 {total_checkins} 天。"
        f"'{dominant_mood}' 是出现最多的心情"
        f"{f'，主要落在「{dominant_family}」情绪族' if dominant_family else ''}。"
    )
    return MoodAnalysisContent(
        total_checkins=total_checkins,
        dominant_mood=dominant_mood,
        dominant_mood_family=dominant_family,
        mood_distribution=mood_distribution,
        mood_family_distribution=family_distribution,
        valence_distribution=valence_distribution,
        energy_distribution=energy_distribution,
        interpretation=interpretation
    )

def _generate_tag_mood_analysis(checkins: List[Dict]) -> TagMoodAnalysisContent:
    tag_mood_counter, all_mood_families = {}, set()
    status_counter, status_family_counter = Counter(), Counter()
    status_family_by_label = {}

    for record in checkins:
        mood_meta = get_mood_meta(record.get('mood_id') or record.get('mood'))
        mood_family = record.get('mood_family') or mood_meta.get('family')
        status_metas = build_status_meta_from_tags(record.get('tags'), record.get('status_ids'))
        if not status_metas or not mood_family:
            continue

        all_mood_families.add(mood_family)
        for status_meta in status_metas:
            status_label = status_meta.get('label')
            status_family = status_meta.get('family', '未归类')
            if not status_label:
                continue
            if status_label not in tag_mood_counter:
                tag_mood_counter[status_label] = Counter()
            tag_mood_counter[status_label][mood_family] += 1
            status_counter[status_label] += 1
            status_family_counter[status_family] += 1
            status_family_by_label[status_label] = status_family

    if not tag_mood_counter: raise HTTPException(status_code=404, detail="无足够标签数据。")

    categories = [name for name, _ in status_counter.most_common()]
    ordered_families = [
        family for family in MOOD_FAMILY_ORDER if family in all_mood_families
    ] + sorted([family for family in all_mood_families if family not in MOOD_FAMILY_ORDER])
    series = [
        {
            "name": family,
            "data": [tag_mood_counter.get(cat, {}).get(family, 0) for cat in categories]
        }
        for family in ordered_families
    ]

    top_correlations = []
    for status_label in categories:
        counter = tag_mood_counter[status_label]
        dominant_family, dominant_count = counter.most_common(1)[0]
        total = sum(counter.values())
        top_correlations.append({
            "status": status_label,
            "status_family": status_family_by_label.get(status_label, "未归类"),
            "dominant_mood_family": dominant_family,
            "count": dominant_count,
            "total": total,
            "percent": round((dominant_count / total) * 100, 1) if total else 0,
        })

    interpretation = "状态关联已升级为按生活状态与情绪族分析，能更清楚地看见哪些日常模式常和哪些情绪质感一起出现。"
    return TagMoodAnalysisContent(
        chart_data={"categories": categories, "series": series},
        status_distribution=_distribution(status_counter),
        status_family_distribution=_distribution(status_family_counter),
        top_correlations=top_correlations[:8],
        interpretation=interpretation
    )

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
    color_counts, color_group_counts, color_tone_counts = Counter(), Counter(), Counter()

    for record in checkins:
        if not record.get('color'):
            continue
        color_meta = get_color_meta(record.get('color_id') or record.get('color'))
        hex_code = color_meta.get("hex", record.get('color')).upper()
        color_counts[hex_code] += 1
        color_group_counts[record.get('color_group') or color_meta.get("group", "自定义")] += 1
        color_tone_counts[record.get('color_tone') or color_meta.get("tone", "custom")] += 1

    color_palette = []
    for hex_code, count in color_counts.most_common(5):
        color_meta = get_color_meta(hex_code)
        color_palette.append({
            "hex": hex_code,
            "name": COLOR_NAME_MAP.get(hex_code, color_meta.get("label", "自定义色")),
            "percent": round((count / total_checkins) * 100, 1)
        })
    top_color_name = color_palette[0]['name'] if color_palette else "五彩斑斓"
    color_group_distribution = _distribution(color_group_counts, total_checkins)
    dominant_color_group = color_group_distribution[0]["name"] if color_group_distribution else None
    interpretation = (
        f"这是专属于你的情绪色卡。'{top_color_name}' 是你最常选择的颜色"
        f"{f'，主要来自「{dominant_color_group}」色彩组' if dominant_color_group else ''}。"
    )
    return ColorPaletteAnalysisContent(
        color_palette=color_palette,
        dominant_color_group=dominant_color_group,
        color_group_distribution=color_group_distribution,
        color_tone_distribution=_distribution(color_tone_counts, total_checkins),
        interpretation=interpretation
    )
