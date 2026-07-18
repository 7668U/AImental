# AImental_backend/model/checkin_dimensions.py

import json
from typing import Any, Dict, List, Optional


MOOD_OPTIONS = [
    {"id": "happy", "label": "开心", "family": "明亮愉悦", "valence": "positive", "energy": "high", "icon": "happy"},
    {"id": "satisfied", "label": "满足", "family": "明亮愉悦", "valence": "positive", "energy": "medium", "icon": "satisfied"},
    {"id": "expectant", "label": "期待", "family": "明亮愉悦", "valence": "positive", "energy": "high", "icon": "expectant"},
    {"id": "grateful", "label": "感激", "family": "明亮愉悦", "valence": "positive", "energy": "medium", "icon": "grateful"},
    {"id": "calm", "label": "平静", "family": "安稳平静", "valence": "neutral", "energy": "low", "icon": "calm"},
    {"id": "relaxed", "label": "放松", "family": "安稳平静", "valence": "positive", "energy": "low", "icon": "relaxed"},
    {"id": "secure", "label": "安心", "family": "安稳平静", "valence": "positive", "energy": "low", "icon": "secure"},
    {"id": "focused", "label": "专注", "family": "安稳平静", "valence": "neutral", "energy": "medium", "icon": "focused"},
    {"id": "sad", "label": "难过", "family": "低落难过", "valence": "negative", "energy": "low", "icon": "sad"},
    {"id": "lost", "label": "失落", "family": "低落难过", "valence": "negative", "energy": "low", "icon": "lost"},
    {"id": "wronged", "label": "委屈", "family": "低落难过", "valence": "negative", "energy": "low", "icon": "wronged"},
    {"id": "lonely", "label": "孤独", "family": "低落难过", "valence": "negative", "energy": "low", "icon": "lonely"},
    {"id": "anxious", "label": "焦虑", "family": "焦虑紧绷", "valence": "negative", "energy": "high", "icon": "anxious"},
    {"id": "worried", "label": "担心", "family": "焦虑紧绷", "valence": "negative", "energy": "medium", "icon": "worried"},
    {"id": "irritable", "label": "烦躁", "family": "焦虑紧绷", "valence": "negative", "energy": "high", "icon": "irritable"},
    {"id": "panicked", "label": "慌乱", "family": "焦虑紧绷", "valence": "negative", "energy": "high", "icon": "panicked"},
    {"id": "angry", "label": "生气", "family": "生气受伤", "valence": "negative", "energy": "high", "icon": "angry"},
    {"id": "annoyed", "label": "厌烦", "family": "生气受伤", "valence": "negative", "energy": "medium", "icon": "annoyed"},
    {"id": "unwilling", "label": "不甘", "family": "生气受伤", "valence": "negative", "energy": "high", "icon": "unwilling"},
    {"id": "hurt", "label": "受伤", "family": "生气受伤", "valence": "negative", "energy": "low", "icon": "hurt"},
    {"id": "tired", "label": "疲惫", "family": "疲惫麻木", "valence": "negative", "energy": "low", "icon": "tired"},
    {"id": "sleepy", "label": "困倦", "family": "疲惫麻木", "valence": "neutral", "energy": "low", "icon": "sleepy"},
    {"id": "numb", "label": "麻木", "family": "疲惫麻木", "valence": "neutral", "energy": "low", "icon": "numb"},
    {"id": "confused", "label": "迷茫", "family": "疲惫麻木", "valence": "negative", "energy": "low", "icon": "confused"},
]

MOOD_LABEL_ALIASES = {
    "兴奋": "期待",
    "尴尬": "迷茫",
}

STATUS_OPTIONS = [
    {"id": "sunny", "label": "元气满满", "family": "能量气场", "type": "energy", "icon": "sunny"},
    {"id": "charge", "label": "充电", "family": "能量气场", "type": "energy", "icon": "charge"},
    {"id": "low_battery", "label": "低电量", "family": "能量气场", "type": "energy", "icon": "low_battery"},
    {"id": "cloud", "label": "放空", "family": "能量气场", "type": "energy", "icon": "cloud"},
    {"id": "brick", "label": "搬砖", "family": "工作学习", "type": "work", "icon": "brick"},
    {"id": "book", "label": "学习", "family": "工作学习", "type": "work", "icon": "book"},
    {"id": "meeting", "label": "开会", "family": "工作学习", "type": "work", "icon": "meeting"},
    {"id": "overtime", "label": "加班", "family": "工作学习", "type": "work", "icon": "overtime"},
    {"id": "commute", "label": "通勤", "family": "出行移动", "type": "travel", "icon": "commute"},
    {"id": "business_trip", "label": "出差", "family": "出行移动", "type": "travel", "icon": "business_trip"},
    {"id": "travel", "label": "旅行", "family": "出行移动", "type": "travel", "icon": "travel"},
    {"id": "home", "label": "回家", "family": "出行移动", "type": "travel", "icon": "home"},
    {"id": "food", "label": "美食", "family": "生活日常", "type": "daily", "icon": "food"},
    {"id": "sleep", "label": "睡觉", "family": "生活日常", "type": "daily", "icon": "sleep"},
    {"id": "housework", "label": "家务", "family": "生活日常", "type": "daily", "icon": "housework"},
    {"id": "shopping", "label": "购物", "family": "生活日常", "type": "daily", "icon": "shopping"},
    {"id": "sports", "label": "运动", "family": "运动健康", "type": "health", "icon": "sports"},
    {"id": "fitness", "label": "健身", "family": "运动健康", "type": "health", "icon": "fitness"},
    {"id": "outdoor", "label": "户外", "family": "运动健康", "type": "health", "icon": "outdoor"},
    {"id": "wellness", "label": "养生", "family": "运动健康", "type": "health", "icon": "wellness"},
    {"id": "stay_home", "label": "宅家", "family": "休闲社交", "type": "leisure", "icon": "stay_home"},
    {"id": "entertainment", "label": "娱乐", "family": "休闲社交", "type": "leisure", "icon": "entertainment"},
    {"id": "party", "label": "聚会", "family": "休闲社交", "type": "leisure", "icon": "party"},
    {"id": "no_disturb", "label": "勿扰", "family": "休闲社交", "type": "leisure", "icon": "no_disturb"},
]

STATUS_LABEL_ALIASES = {
    "工作": "搬砖",
    "生病": "养生",
    "出游": "旅行",
    "出行": "旅行",
    "远足": "旅行",
    "吃饭": "美食",
    "喝咖啡": "美食",
    "做饭": "美食",
    "散步": "户外",
    "拉伸": "健身",
    "独处": "放空",
    "躺平": "放空",
    "充电中": "充电",
    "低电量": "低电量",
    "勿扰模式": "勿扰",
    "刷手机": "娱乐",
    "听歌": "娱乐",
    "追剧": "娱乐",
    "打游戏": "娱乐",
}

COLOR_OPTIONS = [
    {"id": "warm_sun_orange", "label": "暖阳橙", "hex": "#FFB35C", "group": "暖光明亮", "tone": "warm", "description": "开心、被鼓励、有活力"},
    {"id": "cream_yellow", "label": "奶油黄", "hex": "#FFE08A", "group": "暖光明亮", "tone": "warm", "description": "轻松、满足、治愈"},
    {"id": "peach_pink", "label": "蜜桃粉", "hex": "#FF9FB2", "group": "暖光明亮", "tone": "warm", "description": "温柔、亲近、被照顾"},
    {"id": "coral_red", "label": "珊瑚红", "hex": "#FF7A70", "group": "暖光明亮", "tone": "warm", "description": "热烈、兴奋、行动感"},
    {"id": "mint_green", "label": "薄荷绿", "hex": "#8FD7A5", "group": "清透自然", "tone": "cool", "description": "安心、恢复、舒服"},
    {"id": "lake_blue", "label": "湖水蓝", "hex": "#6EC6D9", "group": "清透自然", "tone": "cool", "description": "平静、清醒、流动"},
    {"id": "sky_blue", "label": "晴空蓝", "hex": "#8BB8FF", "group": "清透自然", "tone": "cool", "description": "开阔、自由、专注"},
    {"id": "lime_green", "label": "青柠绿", "hex": "#B7E36D", "group": "清透自然", "tone": "fresh", "description": "新鲜、轻快、元气"},
    {"id": "lavender_purple", "label": "薰衣紫", "hex": "#B9A7F0", "group": "柔和梦感", "tone": "soft", "description": "敏感、柔软、想象"},
    {"id": "cherry_mist_pink", "label": "樱雾粉", "hex": "#F6B6C8", "group": "柔和梦感", "tone": "soft", "description": "细腻、浪漫、松弛"},
    {"id": "berry_red", "label": "浅莓红", "hex": "#D96C8A", "group": "柔和梦感", "tone": "soft", "description": "心动、委屈、情绪浓"},
    {"id": "moonlight_white", "label": "月光白", "hex": "#F5F1E8", "group": "柔和梦感", "tone": "light", "description": "空白、安静、轻盈"},
    {"id": "fog_blue_gray", "label": "雾灰蓝", "hex": "#91A7B4", "group": "阴雨安静", "tone": "gray", "description": "疲惫、缓慢、低能量"},
    {"id": "raindrop_blue", "label": "雨滴蓝", "hex": "#6F8FBF", "group": "阴雨安静", "tone": "cool", "description": "难过、失落、想安静"},
    {"id": "cloud_gray", "label": "云朵灰", "hex": "#C7CDD1", "group": "阴雨安静", "tone": "gray", "description": "麻木、平淡、无力"},
    {"id": "deep_sea_blue", "label": "深海蓝", "hex": "#4B6584", "group": "阴雨安静", "tone": "dark", "description": "沉重、孤独、压抑"},
    {"id": "flame_red", "label": "火焰红", "hex": "#E85D5D", "group": "紧绷浓郁", "tone": "intense", "description": "生气、冲突、不甘"},
    {"id": "caramel_brown", "label": "焦糖棕", "hex": "#B9794A", "group": "紧绷浓郁", "tone": "intense", "description": "烦躁、消耗、压力"},
    {"id": "midnight_purple", "label": "午夜紫", "hex": "#665C99", "group": "紧绷浓郁", "tone": "intense", "description": "焦虑、混乱、难眠"},
    {"id": "ink_green", "label": "墨绿", "hex": "#557C70", "group": "紧绷浓郁", "tone": "dark", "description": "克制、防御、自我保护"},
    {"id": "wood_tan", "label": "木色", "hex": "#C8A27A", "group": "沉稳大地", "tone": "earth", "description": "稳定、生活感、真实"},
    {"id": "cocoa_brown", "label": "可可棕", "hex": "#8B6A5A", "group": "沉稳大地", "tone": "earth", "description": "疲惫、踏实、厚重"},
    {"id": "turquoise_green", "label": "松石绿", "hex": "#4FA39A", "group": "沉稳大地", "tone": "earth", "description": "平衡、恢复、慢慢变好"},
    {"id": "charcoal_black", "label": "炭黑", "hex": "#3F3F46", "group": "沉稳大地", "tone": "dark", "description": "沉默、封闭、很累"},
]

LEGACY_COLOR_ALIASES = {
    "#FF8A80": "#FF7A70",
    "#FFB74D": "#FFB35C",
    "#FFC107": "#FFE08A",
    "#FFF59D": "#FFE08A",
    "#81D4FA": "#8BB8FF",
    "#A5D6A7": "#8FD7A5",
    "#80CBC4": "#4FA39A",
    "#B39DDB": "#B9A7F0",
    "#C5CAE9": "#B9A7F0",
    "#F48FB1": "#F6B6C8",
    "#BCAAA4": "#C8A27A",
    "#B0BEC5": "#C7CDD1",
    "#7986CB": "#6F8FBF",
    "#F5F5F5": "#F5F1E8",
}


def _index_by(key: str, options: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    return {item[key]: item for item in options}


MOODS_BY_ID = _index_by("id", MOOD_OPTIONS)
MOODS_BY_LABEL = _index_by("label", MOOD_OPTIONS)
STATUSES_BY_ID = _index_by("id", STATUS_OPTIONS)
STATUSES_BY_LABEL = _index_by("label", STATUS_OPTIONS)
COLORS_BY_ID = _index_by("id", COLOR_OPTIONS)
COLORS_BY_HEX = {item["hex"].upper(): item for item in COLOR_OPTIONS}
COLORS_BY_LABEL = _index_by("label", COLOR_OPTIONS)


def normalize_hex(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().upper()
    return LEGACY_COLOR_ALIASES.get(normalized, normalized)


def normalize_mood_label(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return MOOD_LABEL_ALIASES.get(value.strip(), value.strip())


def normalize_status_label(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return STATUS_LABEL_ALIASES.get(value.strip(), value.strip())


def get_mood_meta(value: Optional[str]) -> Dict[str, Any]:
    normalized = normalize_mood_label(value)
    if not normalized:
        return {}
    item = MOODS_BY_LABEL.get(normalized) or MOODS_BY_ID.get(normalized)
    if item:
        return dict(item)
    return {
        "id": normalized,
        "label": normalized,
        "family": "未归类",
        "valence": "unknown",
        "energy": "unknown",
        "icon": normalized,
    }


def get_status_meta(value: Optional[str]) -> Dict[str, Any]:
    normalized = normalize_status_label(value)
    if not normalized:
        return {}
    item = STATUSES_BY_LABEL.get(normalized) or STATUSES_BY_ID.get(normalized)
    if item:
        return dict(item)
    return {
        "id": normalized,
        "label": normalized,
        "family": "未归类",
        "type": "unknown",
        "icon": normalized,
    }


def get_color_meta(value: Optional[str]) -> Dict[str, Any]:
    if not value:
        return {}
    normalized_hex = normalize_hex(value)
    item = (
        COLORS_BY_HEX.get(normalized_hex or "")
        or COLORS_BY_ID.get(value)
        or COLORS_BY_LABEL.get(value)
    )
    if item:
        return dict(item)
    return {
        "id": value,
        "label": "自定义色",
        "hex": normalized_hex or value,
        "group": "自定义",
        "tone": "custom",
        "description": "",
    }


def split_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def coerce_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass
        return split_csv(stripped)
    return []


def dump_list(values: List[str]) -> str:
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"))


def load_list(value: Any) -> List[str]:
    return coerce_list(value)


def build_status_meta_from_tags(tags: Optional[str], status_ids: Any = None) -> List[Dict[str, Any]]:
    labels = [normalize_status_label(label) for label in split_csv(tags)]
    labels = [label for label in labels if label]

    if not labels:
        ids = coerce_list(status_ids)
        labels = [
            (STATUSES_BY_ID.get(status_id) or {}).get("label", status_id)
            for status_id in ids
        ]

    seen = set()
    metas = []
    for label in labels:
        meta = get_status_meta(label)
        key = meta.get("id") or meta.get("label")
        if key and key not in seen:
            seen.add(key)
            metas.append(meta)
    return metas


def enrich_checkin_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload)

    mood_meta = get_mood_meta(data.get("mood") or data.get("mood_id"))
    if mood_meta:
        data["mood"] = mood_meta["label"]
        data["mood_id"] = data.get("mood_id") or mood_meta["id"]
        data["mood_family"] = data.get("mood_family") or mood_meta["family"]
        data["mood_valence"] = data.get("mood_valence") or mood_meta["valence"]
        data["mood_energy"] = data.get("mood_energy") or mood_meta["energy"]

    status_metas = build_status_meta_from_tags(
        data.get("tags"),
        data.get("status_ids"),
    )[:1]
    if status_metas:
        status_labels = [meta["label"] for meta in status_metas]
        data["tags"] = ",".join(status_labels)
        data["status_ids"] = dump_list([meta["id"] for meta in status_metas])
        data["status_families"] = dump_list(list(dict.fromkeys(meta["family"] for meta in status_metas)))

    color_meta = get_color_meta(data.get("color") or data.get("color_id") or data.get("color_label"))
    if color_meta:
        data["color"] = color_meta["hex"]
        data["color_id"] = data.get("color_id") or color_meta["id"]
        data["color_label"] = data.get("color_label") or color_meta["label"]
        data["color_group"] = data.get("color_group") or color_meta["group"]
        data["color_tone"] = data.get("color_tone") or color_meta["tone"]
        data["color_description"] = data.get("color_description") or color_meta["description"]

    if isinstance(data.get("status_ids"), list):
        data["status_ids"] = dump_list(data["status_ids"])
    if isinstance(data.get("status_families"), list):
        data["status_families"] = dump_list(data["status_families"])

    return data
