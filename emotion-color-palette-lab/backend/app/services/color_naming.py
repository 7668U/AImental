from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from backend.app import config

SYSTEM_PROMPT = """
你是一名“情绪色彩命名师”和“审美型中文文案助手”。

你的任务是根据用户提供的一组颜色，以及系统计算出的综合色，为这个综合色起一个优雅、自然、容易理解、适合年轻用户分享的中文颜色名。

输出原则：
1. 颜色名必须是中文，建议 2 到 5 个字，最多不超过 6 个字。
2. 名字要有画面感、温柔感、生活感，可以参考“奶茶棕、雾桃粉、青空灰、暮云紫、海盐蓝”这类风格。
3. 不要使用生僻、难懂、古风过重的词。
4. 不要营销腔，不要夸张。
5. 除颜色名之外，再输出一句副标题，语气温柔、简洁、有一点诗意，但不要矫情。
6. 输出 3 个情绪关键词。
7. 输出 1 个推荐场景方向，用于后续 AI 生成图片，必须简洁明确。
8. 如果综合色偏灰、偏低饱和，请命名得更柔和克制。
9. 如果综合色偏亮、偏暖，请命名得更温暖轻盈。
10. 输出必须是严格 JSON，不要带 markdown，不要带解释说明。

JSON 格式：
{
  "color_name": "奶茶棕",
  "subtitle": "像傍晚被阳光温过的一杯奶茶",
  "tags": ["温柔", "安稳", "恢复"],
  "scene_hint": "暖调室内窗边"
}
""".strip()


def _fallback_name(mixed_color: dict[str, Any]) -> dict[str, Any]:
    hue, saturation, lightness = mixed_color["hsl"]

    if saturation < 0.12:
        if lightness > 0.72:
            return {
                "color_name": "晨雾白",
                "subtitle": "像清晨窗边慢慢散开的薄雾",
                "tags": ["安静", "柔和", "整理"],
                "scene_hint": "清晨室内窗边",
            }
        return {
            "color_name": "青空灰",
            "subtitle": "像阴天里仍然透着一点光的天空",
            "tags": ["克制", "平稳", "呼吸"],
            "scene_hint": "雨后城市街景",
        }

    if hue < 25 or hue >= 345:
        return {
            "color_name": "玫瑰晚霞",
            "subtitle": "像傍晚落在手心里的一点暖光",
            "tags": ["温热", "松弛", "靠近"],
            "scene_hint": "黄昏窗边静物",
        }
    if hue < 55:
        return {
            "color_name": "杏光奶茶",
            "subtitle": "像午后被阳光轻轻搅开的奶茶",
            "tags": ["温柔", "安稳", "恢复"],
            "scene_hint": "暖调室内窗边",
        }
    if hue < 95:
        return {
            "color_name": "米阳光",
            "subtitle": "像晒过的棉布留住了一点春天",
            "tags": ["轻盈", "明亮", "舒展"],
            "scene_hint": "春日草地与微风",
        }
    if hue < 165:
        return {
            "color_name": "薄荷晨雾",
            "subtitle": "像清晨空气里一点干净的凉意",
            "tags": ["清新", "放松", "醒来"],
            "scene_hint": "安静卧室一角",
        }
    if hue < 225:
        return {
            "color_name": "海盐蓝",
            "subtitle": "像海风吹过后留下的清澈余温",
            "tags": ["清透", "平静", "呼吸"],
            "scene_hint": "黄昏海边",
        }
    if hue < 285:
        return {
            "color_name": "暮云紫",
            "subtitle": "像夜色到来前仍然柔软的云",
            "tags": ["沉静", "想象", "陪伴"],
            "scene_hint": "傍晚书桌与窗景",
        }
    return {
        "color_name": "雾桃粉",
        "subtitle": "像雾气里慢慢浮起的一点桃色",
        "tags": ["温软", "轻甜", "安放"],
        "scene_hint": "柔和花影与窗帘",
    }


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(0)
    return json.loads(cleaned)


def _normalize_result(payload: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    color_name = str(payload.get("color_name") or fallback["color_name"]).strip()
    subtitle = str(payload.get("subtitle") or fallback["subtitle"]).strip()
    scene_hint = str(payload.get("scene_hint") or fallback["scene_hint"]).strip()
    tags = payload.get("tags")
    if not isinstance(tags, list):
        tags = fallback["tags"]
    tags = [str(tag).strip() for tag in tags if str(tag).strip()][:3]
    if len(tags) < 3:
        tags = fallback["tags"]

    return {
        "color_name": color_name[:6] or fallback["color_name"],
        "subtitle": subtitle[:36] or fallback["subtitle"],
        "tags": tags,
        "scene_hint": scene_hint[:20] or fallback["scene_hint"],
    }


def name_mixed_color(mixed_color: dict[str, Any], selected_colors: list[dict[str, Any]]) -> dict[str, Any]:
    fallback = _fallback_name(mixed_color)
    if not config.HEPAI_API_KEY:
        return {**fallback, "source": "fallback", "error": "HEPAI_API_KEY is not configured."}

    client = OpenAI(api_key=config.HEPAI_API_KEY, base_url=config.HEPAI_BASE_URL)
    user_prompt = {
        "mixed_color": mixed_color,
        "selected_colors": selected_colors,
        "output": "请输出符合系统要求的严格 JSON。",
    }

    try:
        response = client.chat.completions.create(
            model=config.HEPAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
            ],
            temperature=0.72,
            max_tokens=360,
            stream=False,
        )
        content = response.choices[0].message.content or ""
        parsed = _extract_json(content)
        return {**_normalize_result(parsed, fallback), "source": "hepai"}
    except Exception as exc:
        return {**fallback, "source": "fallback", "error": str(exc)[:240]}

