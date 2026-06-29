# routers/analysis.py

import json
import hashlib
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
from model.emotion_color_card import emotion_color_card_cache_table

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
AI_REPORT_SCHEMA_VERSION = "v4"
MIN_ANALYSIS_CHECKIN_DAYS = 6

# --- 辅助数据 ---
# 中文停用词表 (一个简单的版本，您可以根据需要扩展)
STOPWORDS = {
    '的', '了', '我', '你', '他', '她', '它', '我们', '你们', '他们', '是', '在', '有', '也',
    '不', '都', '就', '还', '个', '一', '很', '什么', '怎么', '这个', '那个', '今天', '一个'
}

COLOR_NAME_MAP = {item["hex"].upper(): item["label"] for item in COLOR_OPTIONS}
MOOD_FAMILY_ORDER = list(dict.fromkeys(item["family"] for item in MOOD_OPTIONS))


# ===================================================
# 2. 为四个独立报告设计的 AI PROMPT 模板
# ===================================================
AI_REPORT_STYLE_RULES = """
你要根据用户在 {period_name} 的打卡数据，生成一份小程序里的心情分析文案。

输出必须是严格 JSON，只包含两个字符串字段：summary_text 和 report_text。

模块边界：
- 只能使用下面提供的“本模块数据摘要”，不要主动引入摘要里没有出现的维度。
- 四个模块各自分析不同内容，不要把其他模块的话题揉进来。

summary_text 的要求：
- 只写 1 到 2 句，最多 70 个中文字符。
- 只提最明显、最有信息量的特征。
- 不要泛泛安慰，不要写成报告导语。

report_text 的要求：
- 直接进入分析，不要寒暄，不要自我介绍，不要说“作为/我是/你的顾问/亲爱的/来访者/请查收”。
- 不要使用 Markdown，不要出现 #、*、---、编号标题、列表符号或书信格式。
- 写 3 到 5 个自然段，每段 1 到 2 句，整体控制在 250 到 450 字。
- 语气亲切、平实、像产品里的温和解读，不要过度专业化，不要诊断，不要承诺疗效。
- 可以使用“可能、看起来、比较像、值得留意”这类谨慎表达。
- 不要重复图表已经显而易见的信息，要解释最值得注意的模式。
"""

AI_DETAILED_PROMPTS = {
    "mood": AI_REPORT_STYLE_RULES + """
分析重点：
- 只分析心情本身：mood、mood_family、mood_valence、mood_energy。
- 不要分析生活状态、文字高频词、颜色或色彩组。
- summary_text 只概括最突出的心情或情绪族，例如“这段时间最常出现的是平静，整体更偏稳定低起伏。”
- report_text 说明主导心情、情绪族倾向、能量状态，以及一个温和的小建议。

用户打卡数据摘要：
{data_summary}
""",
    "tag-mood": AI_REPORT_STYLE_RULES + """
分析重点：
- 只分析生活状态 tags/status_ids 与心情、情绪族、能量状态的关联。
- 不要分析颜色、色彩组、文字高频词或日记主题。
- 不要把状态写成直接原因，只说“常一起出现、比较容易同框、值得留意”。
- summary_text 只概括最明显的关联，例如“你常在学习状态下记录到平静，说明这段时间学习和稳定感关系更近。”
- report_text 说明最常出现的状态、它对应的心情或情绪族，以及一个生活节奏上的轻建议。

用户打卡数据摘要：
{data_summary}
""",
    "word-cloud": AI_REPORT_STYLE_RULES + """
分析重点：
- 只分析 text_content 的高频词、反复出现的主题，以及这些词所在记录对应的心情或情绪族。
- 不要分析生活状态、颜色、色彩组。
- summary_text 直接指出最明显的词或主题，例如“这段时间你最常提到‘学习’，记录重点更偏向日常推进和自我整理。”
- report_text 说明高频词、词语与心情的对应关系，以及一个可以继续记录的小问题。

用户打卡数据摘要：
{data_summary}
""",
    "color": AI_REPORT_STYLE_RULES + """
分析重点：
- 只分析 color、color_label、color_group、color_tone。
- 不要分析生活状态、文字高频词或具体事件。
- summary_text 只概括最明显的色彩偏向，例如“这段时间你的色彩更偏暖光明亮，整体给人的感觉比较柔和、轻快。”
- report_text 说明主色、色彩组、整体画面感，以及一个温和的色彩观察建议。

用户打卡数据摘要：
{data_summary}
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
    checkins = checkin_table.get_checkins_by_period(current_user_id, start_ts, end_ts)
    if not checkins:
        raise HTTPException(status_code=404, detail="该时间段内无打卡记录。")
    if len(checkins) < MIN_ANALYSIS_CHECKIN_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"{period_name} 的打卡数据不大于 5 天，无法进行分析。",
        )
    data_signature = _build_checkin_cache_signature(checkins)
    period_key = f"{ANALYSIS_SCHEMA_VERSION}-{year}-{value}-{period_type}-{analysis_type}-{data_signature}-chart"
    
    # 1. 检查缓存
    if not force_refresh:
        cached = analysis_table.get_analysis(current_user_id, period_key, analysis_type)
        if cached:
            return json.loads(cached.content)

    # 2. 获取数据
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
    cache_type_key = f"{AI_REPORT_SCHEMA_VERSION}_ai_report_{analysis_type}"

    checkins = checkin_table.get_checkins_by_period(current_user_id, start_ts, end_ts)
    if not checkins:
        raise HTTPException(status_code=404, detail="该时间段内无打卡记录，无法生成AI报告。")
    if len(checkins) < MIN_ANALYSIS_CHECKIN_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"{period_name} 的打卡数据不大于 5 天，无法进行分析。",
        )
    data_signature = _build_checkin_cache_signature(checkins)
    period_key = f"{AI_REPORT_SCHEMA_VERSION}-{year}-{value}-{period_type}-{analysis_type}-{data_signature}-ai"
    
    # 1. 检查缓存
    if not force_refresh:
        cached = analysis_table.get_analysis(current_user_id, period_key, cache_type_key)
        if cached:
            cached_content = json.loads(cached.content)
            return {
                "summary_text": cached_content.get("summary_text", ""),
                "report_text": cached_content.get("report_text", ""),
            }

    # 2. 获取数据
    # 3. 调用LLM生成报告
    prompt_template = AI_DETAILED_PROMPTS[analysis_type]
    focus_summary = _build_ai_focus_summary(checkins, analysis_type)
    report_payload = generate_ai_analysis_report(
        checkins,
        prompt_template,
        period_name,
        analysis_type,
        focus_summary
    )

    # 4. 存入缓存并返回
    class AIReportContent(BaseModel):
        summary_text: str
        report_text: str
    content_model = AIReportContent(
        summary_text=report_payload.get("summary_text", ""),
        report_text=report_payload.get("report_text", "")
    )
    analysis_table.save_analysis(current_user_id, period_key, cache_type_key, content_model)

    return content_model.model_dump()


@router.get(
    "/color-card/{period_type}/{year}/{value}",
    response_model=Dict[str, Any],
    summary="获取情绪色卡 AI 背景图，按综合色板缓存复用"
)
def get_color_card_background(
    period_type: str = Path(..., description="周期类型: 'monthly', 'quarterly', 'yearly'"),
    year: int = Path(..., description="年份"),
    value: int = Path(..., description="月份(1-12) 或 季度(1-4)"),
    current_user_id: str = Depends(get_current_user_id),
    force_refresh: bool = False,
):
    start_ts, end_ts, period_name = _get_period_info(period_type, year, value)
    checkins = checkin_table.get_checkins_by_period(current_user_id, start_ts, end_ts)
    if not checkins:
        raise HTTPException(status_code=404, detail="该时间段内无打卡记录。")
    if len(checkins) < MIN_ANALYSIS_CHECKIN_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"{period_name} 的打卡数据不大于 5 天，无法生成色卡。",
        )

    try:
        return emotion_color_card_cache_table.get_or_generate(checkins, force_refresh=force_refresh)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/eligibility/{period_type}/{year}/{value}",
    response_model=Dict[str, Any],
    summary="检查当前周期打卡天数是否足够分析"
)
def get_analysis_eligibility(
    period_type: str = Path(..., description="周期类型: 'monthly', 'quarterly', 'yearly'"),
    year: int = Path(..., description="年份"),
    value: int = Path(..., description="月份(1-12) 或 季度(1-4)"),
    current_user_id: str = Depends(get_current_user_id),
):
    start_ts, end_ts, period_name = _get_period_info(period_type, year, value)
    checkins = checkin_table.get_checkins_by_period(current_user_id, start_ts, end_ts)
    checkin_days = len(checkins)
    return {
        "can_analyze": checkin_days >= MIN_ANALYSIS_CHECKIN_DAYS,
        "checkin_days": checkin_days,
        "min_days": MIN_ANALYSIS_CHECKIN_DAYS,
        "period_name": period_name,
    }

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


def _split_tag_labels(tags: str | None) -> List[str]:
    if not tags:
        return []
    return [tag.strip() for tag in tags.split(",") if tag.strip()]


def _build_checkin_cache_signature(checkins: List[Dict]) -> str:
    """Return a short signature for the current check-in contents."""
    signature_payload = []
    tracked_fields = [
        "id",
        "timestamp",
        "updated_at",
        "mood",
        "mood_id",
        "mood_family",
        "mood_valence",
        "mood_energy",
        "tags",
        "status_ids",
        "status_families",
        "text_content",
        "color",
        "color_id",
        "color_label",
        "color_group",
        "color_tone",
    ]
    for record in sorted(checkins, key=lambda item: (item.get("timestamp") or 0, item.get("id") or "")):
        signature_payload.append({
            field: record.get(field)
            for field in tracked_fields
        })
    raw = json.dumps(signature_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _build_ai_focus_summary(checkins: List[Dict], analysis_type: str) -> str:
    if analysis_type == "tag-mood":
        pair_counter, status_counter = Counter(), Counter()
        for record in checkins:
            mood_family = record.get("mood_family") or record.get("mood") or "未标注心情"
            for tag in _split_tag_labels(record.get("tags")):
                status_counter[tag] += 1
                pair_counter[(tag, mood_family)] += 1
        top_pairs = [
            f"{status} + {mood_family}: {count}次"
            for (status, mood_family), count in pair_counter.most_common(8)
        ]
        top_statuses = [f"{name}: {count}次" for name, count in status_counter.most_common(6)]
        return "\n".join([
            "只看生活状态与心情/情绪族的对应关系，不涉及颜色或文字主题。",
            f"高频状态：{'；'.join(top_statuses) or '暂无'}",
            f"状态-情绪族高频配对：{'；'.join(top_pairs) or '暂无'}",
        ])

    if analysis_type == "word-cloud":
        word_counter, word_mood_counter = Counter(), {}
        for record in checkins:
            text = record.get("text_content") or ""
            mood_label = record.get("mood") or record.get("mood_family") or "未标注心情"
            for word in jieba.lcut(text):
                if len(word) <= 1 or word in STOPWORDS:
                    continue
                word_counter[word] += 1
                word_mood_counter.setdefault(word, Counter())[mood_label] += 1
        top_words = []
        for word, count in word_counter.most_common(10):
            mood_name, mood_count = word_mood_counter[word].most_common(1)[0]
            top_words.append(f"{word}: {count}次，最常对应{mood_name}{mood_count}次")
        return "\n".join([
            "只看日记文字的高频词，以及这些词所在记录对应的心情，不涉及状态或颜色。",
            f"高频词与对应心情：{'；'.join(top_words) or '暂无'}",
        ])

    if analysis_type == "color":
        color_counter, group_counter, tone_counter = Counter(), Counter(), Counter()
        for record in checkins:
            color_name = record.get("color_label") or record.get("color")
            if color_name:
                color_counter[color_name] += 1
            if record.get("color_group"):
                group_counter[record["color_group"]] += 1
            if record.get("color_tone"):
                tone_counter[record["color_tone"]] += 1
        return "\n".join([
            "只看颜色选择、色彩组和色调，不涉及状态、文字或具体事件。",
            f"高频颜色：{'；'.join(f'{name}: {count}次' for name, count in color_counter.most_common(6)) or '暂无'}",
            f"高频色彩组：{'；'.join(f'{name}: {count}次' for name, count in group_counter.most_common(6)) or '暂无'}",
            f"高频色调：{'；'.join(f'{name}: {count}次' for name, count in tone_counter.most_common(6)) or '暂无'}",
        ])

    mood_counter, family_counter, valence_counter, energy_counter = Counter(), Counter(), Counter(), Counter()
    for record in checkins:
        if record.get("mood"):
            mood_counter[record["mood"]] += 1
        if record.get("mood_family"):
            family_counter[record["mood_family"]] += 1
        if record.get("mood_valence"):
            valence_counter[record["mood_valence"]] += 1
        if record.get("mood_energy"):
            energy_counter[record["mood_energy"]] += 1
    return "\n".join([
        "只看心情、情绪族、情绪倾向和能量状态，不涉及状态、文字或颜色。",
        f"高频心情：{'；'.join(f'{name}: {count}次' for name, count in mood_counter.most_common(6)) or '暂无'}",
        f"情绪族分布：{'；'.join(f'{name}: {count}次' for name, count in family_counter.most_common(6)) or '暂无'}",
        f"情绪倾向：{'；'.join(f'{name}: {count}次' for name, count in valence_counter.most_common(6)) or '暂无'}",
        f"能量状态：{'；'.join(f'{name}: {count}次' for name, count in energy_counter.most_common(6)) or '暂无'}",
    ])


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
