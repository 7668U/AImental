from __future__ import annotations

import colorsys
import hashlib
import json
import os
import re
import time
from base64 import b64decode
from collections import Counter
from pathlib import Path
from typing import Any, Iterable
from urllib import error, request

from dotenv import load_dotenv
from peewee import CharField, IntegerField, Model, TextField
from security.data_encryption import EncryptedTextField

from db import status_db
from model.checkin_dimensions import get_color_meta


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=False)
load_dotenv(PROJECT_ROOT / "emotion-color-palette-lab" / ".env", override=False)

CARD_CACHE_VERSION = "ai-color-card-v1"
GENERATED_DIR = Path("static") / "emotion-color-cards"
RAW_GENERATED_DIR = GENERATED_DIR / "raw"
HEX_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")


def _now() -> int:
    return int(time.time())


def normalize_hex(value: str) -> str:
    cleaned = str(value or "").strip()
    if not HEX_RE.match(cleaned):
        raise ValueError(f"Invalid hex color: {value}")
    if not cleaned.startswith("#"):
        cleaned = f"#{cleaned}"
    return cleaned.upper()


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    hex_value = normalize_hex(value).lstrip("#")
    return (
        int(hex_value[0:2], 16),
        int(hex_value[2:4], 16),
        int(hex_value[4:6], 16),
    )


def rgb_to_hex(rgb: Iterable[int]) -> str:
    r, g, b = [max(0, min(255, int(round(channel)))) for channel in rgb]
    return f"#{r:02X}{g:02X}{b:02X}"


def rgb_to_hsl(rgb: Iterable[int]) -> list[float]:
    r, g, b = [channel / 255 for channel in rgb]
    h, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
    return [round(h * 360), round(saturation, 3), round(lightness, 3)]


def mix_colors(hex_values: list[str]) -> dict[str, Any]:
    if not hex_values:
        raise ValueError("At least one color is required.")

    channels = [hex_to_rgb(value) for value in hex_values]
    count = len(channels)
    mixed_rgb = [
        round(sum(rgb[index] for rgb in channels) / count)
        for index in range(3)
    ]

    return {
        "hex": rgb_to_hex(mixed_rgb),
        "rgb": mixed_rgb,
        "hsl": rgb_to_hsl(mixed_rgb),
    }


def fallback_color_name(mixed_color: dict[str, Any]) -> dict[str, Any]:
    hue, saturation, lightness = mixed_color["hsl"]

    if saturation < 0.12:
        if lightness > 0.72:
            return {
                "color_name": "晨雾白",
                "subtitle": "像清晨窗边慢慢散开的薄雾",
                "tags": ["安静", "柔和", "整理"],
                "scene_hint": "清晨室内窗边",
                "source": "local",
            }
        return {
            "color_name": "青空灰",
            "subtitle": "像阴天里仍然透着一点光的天空",
            "tags": ["克制", "平稳", "呼吸"],
            "scene_hint": "雨后城市街景",
            "source": "local",
        }

    if hue < 25 or hue >= 345:
        result = ("玫瑰晚霞", "像傍晚落在手心里的一点暖光", ["温热", "松弛", "靠近"], "黄昏窗边静物")
    elif hue < 55:
        result = ("杏光奶茶", "像午后被阳光轻轻搅开的奶茶", ["温柔", "安稳", "恢复"], "暖调室内窗边")
    elif hue < 95:
        result = ("米阳光", "像晒过的棉布留住了一点春天", ["轻盈", "明亮", "舒展"], "春日草地与微风")
    elif hue < 165:
        result = ("薄荷晨雾", "像清晨空气里一点干净的凉意", ["清新", "放松", "醒来"], "安静卧室一角")
    elif hue < 225:
        result = ("海盐蓝", "像海风吹过后留下的清澈余温", ["清透", "平静", "呼吸"], "黄昏海边")
    elif hue < 285:
        result = ("暮云紫", "像夜色到来前仍然柔软的云", ["沉静", "想象", "陪伴"], "傍晚书桌与窗景")
    else:
        result = ("雾桃粉", "像雾气里慢慢浮起的一点桃色", ["温软", "轻甜", "安放"], "柔和花影与窗帘")

    color_name, subtitle, tags, scene_hint = result
    return {
        "color_name": color_name,
        "subtitle": subtitle,
        "tags": tags,
        "scene_hint": scene_hint,
        "source": "local",
    }


class EmotionColorCardCache(Model):
    palette_key = CharField(primary_key=True, max_length=64)
    palette_signature = EncryptedTextField(
        purpose="emotion_color_card_cache.palette_signature"
    )
    mixed_hex = EncryptedTextField(
        purpose="emotion_color_card_cache.mixed_hex"
    )
    mixed_color = EncryptedTextField(
        purpose="emotion_color_card_cache.mixed_color"
    )
    selected_colors = EncryptedTextField(
        purpose="emotion_color_card_cache.selected_colors"
    )
    color_name = EncryptedTextField(
        purpose="emotion_color_card_cache.color_name"
    )
    subtitle = EncryptedTextField(
        purpose="emotion_color_card_cache.subtitle"
    )
    tags = EncryptedTextField(
        purpose="emotion_color_card_cache.tags",
        null=True,
    )
    scene_hint = EncryptedTextField(
        purpose="emotion_color_card_cache.scene_hint",
        null=True,
    )
    background_image_url = CharField(max_length=1024, null=True)
    local_path = CharField(max_length=1024, null=True)
    raw_path = CharField(max_length=1024, null=True)
    prompt = EncryptedTextField(
        purpose="emotion_color_card_cache.prompt",
        null=True,
    )
    source = CharField(max_length=50, default="fallback")
    error = EncryptedTextField(
        purpose="emotion_color_card_cache.error",
        null=True,
    )
    created_at = IntegerField(default=_now)
    updated_at = IntegerField(default=_now)

    class Meta:
        database = status_db
        table_name = "emotion_color_card_cache"


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _json_loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _image_api_config() -> dict[str, str]:
    hepai_key = os.getenv("HEPAI_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if hepai_key:
        return {
            "api_key": hepai_key,
            "base_url": os.getenv("HEPAI_BASE_URL", "https://aiapi.ihep.ac.cn/apiv2").strip(),
            "model": os.getenv("HEPAI_IMAGE_MODEL", "openai/gpt-image-2").strip(),
            "size": os.getenv("AI_COLOR_IMAGE_SIZE", os.getenv("HEPAI_IMAGE_SIZE", "1088x1456")).strip(),
            "quality": os.getenv("AI_COLOR_IMAGE_QUALITY", os.getenv("HEPAI_IMAGE_QUALITY", "low")).strip(),
            "source": "hepai-images",
        }

    return {
        "api_key": openai_key,
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com").strip(),
        "model": (
            os.getenv("AI_COLOR_IMAGE_MODEL")
            or os.getenv("IMAGE_STUDIO_IMAGE_MODEL")
            or os.getenv("VITE_IMAGE_STUDIO_IMAGE_MODEL")
            or "gpt-image-2"
        ).strip(),
        "size": os.getenv("AI_COLOR_IMAGE_SIZE", os.getenv("FHL_IMAGE_SIZE", "1088x1456")).strip(),
        "quality": os.getenv("AI_COLOR_IMAGE_QUALITY", os.getenv("FHL_IMAGE_QUALITY", "low")).strip(),
        "source": "fhl-images" if "fhl" in os.getenv("OPENAI_BASE_URL", "").lower() else "images-api",
    }


def _image_generation_url(base_url: str) -> str:
    root = base_url.rstrip("/")
    lowered = root.lower()
    if lowered.endswith("/v1") or lowered.endswith("/apiv2"):
        return f"{root}/images/generations"
    return f"{root}/v1/images/generations"


def _sanitize_error(text: str, model: str | None = None) -> str:
    if not text:
        return "Images API failed."

    redacted = re.sub(r"sk-[A-Za-z0-9_-]+", "sk-REDACTED", text)
    lines = [line.strip() for line in redacted.splitlines() if line.strip()]
    joined = " ".join(lines)
    model_label = f" for {model}" if model else ""
    return f"Images API failed{model_label}: {joined[:500]}"


def _build_palette(checkins: list[dict[str, Any]]) -> dict[str, Any]:
    color_counts: Counter[str] = Counter()
    color_meta_by_hex: dict[str, dict[str, Any]] = {}

    for record in checkins:
        raw_color = record.get("color_id") or record.get("color") or record.get("color_label")
        if not raw_color:
            continue
        color_meta = get_color_meta(raw_color)
        hex_code = normalize_hex(color_meta.get("hex") or record.get("color"))
        color_counts[hex_code] += 1
        color_meta_by_hex[hex_code] = color_meta

    if not color_counts:
        raise ValueError("该时间段内没有可用于生成色卡的颜色记录。")

    total = sum(color_counts.values())
    weighted_colors: list[str] = []
    for hex_code, count in color_counts.items():
        weighted_colors.extend([hex_code] * count)

    selected_colors = []
    for hex_code, count in sorted(color_counts.items(), key=lambda item: (-item[1], item[0])):
        meta = color_meta_by_hex.get(hex_code) or get_color_meta(hex_code)
        selected_colors.append({
            "id": meta.get("id") or hex_code,
            "name": meta.get("label") or "自定义色",
            "hex": hex_code,
            "group": meta.get("group") or "自定义",
            "count": count,
            "percent": round((count / total) * 100, 1),
        })

    signature_items = [
        {"hex": hex_code, "count": count}
        for hex_code, count in sorted(color_counts.items())
    ]
    signature = _json_dumps(signature_items)
    palette_key = hashlib.sha256(f"{CARD_CACHE_VERSION}:{signature}".encode("utf-8")).hexdigest()[:24]

    return {
        "palette_key": palette_key,
        "palette_signature": signature,
        "mixed_color": mix_colors(weighted_colors),
        "selected_colors": selected_colors,
    }


def build_image_prompt(
    mixed_color: dict[str, Any],
    naming_result: dict[str, Any],
    selected_colors: list[dict[str, Any]],
) -> str:
    tags = ", ".join(naming_result.get("tags", []))
    palette_text = "; ".join(
        f"{item['name']} {item['hex']} {item['percent']}%"
        for item in selected_colors[:8]
    )
    return f"""
Generate a refined vertical 3:4 emotional color-card background image at exactly 1088x1456 pixels if supported.
Use a photorealistic style, like a real camera photograph, not manga, not anime, not cartoon, not illustration, not painterly concept art.

Color name: {naming_result.get("color_name", "")}
Main mixed color: {mixed_color.get("hex", "")}
Observed check-in palette: {palette_text}
Subtitle mood: {naming_result.get("subtitle", "")}
Mood keywords: {tags}
Scene direction: {naming_result.get("scene_hint", "")}

Visual requirements:
- No text, no letters, no numbers, no logo, no watermark, no signature.
- Must look realistic and photographic, with natural materials, real scenery, real atmosphere, and believable depth of field.
- Prefer real landscapes, real interiors, or real still-life scenes; avoid manga style, anime style, cartoon rendering, vector art, 3D render, and flat illustration.
- Overall palette should stay close to {mixed_color.get("hex", "")} and the observed check-in palette.
- Gentle, healing, low-saturation, clean, premium editorial photography atmosphere.
- Use clear, beautiful light and shadow: soft sunlight, dusk glow, window light, misty backlight, reflections, or layered natural shadows that support the color mood.
- Leave a large, quiet negative-space area in the exact center for an overlaid Chinese color name.
- Keep important objects away from the outer edges, especially the top and bottom 12%.
- Keep the center free of faces, hard lines, high-contrast objects, and busy texture.
- Use a soft scene or abstract still-life based on "{naming_result.get("scene_hint", "")}".
- Avoid frontal human faces and complicated character relationships.
- Suitable as a polished background for a mini program emotional color card.
""".strip()


def _call_images_api(
    *,
    prompt: str,
    output_path: Path,
    raw_path: Path,
) -> dict[str, Any]:
    config = _image_api_config()
    if not config["api_key"] or not config["model"]:
        return {
            "background_image_url": None,
            "local_path": None,
            "raw_path": None,
            "source": "fallback",
            "error": "Missing image API configuration.",
        }

    body = {
        "model": config["model"],
        "prompt": prompt,
        "n": 1,
        "size": config["size"],
        "quality": config["quality"],
        "output_format": "png",
    }
    payload = json.dumps(body).encode("utf-8")
    req = request.Request(
        _image_generation_url(config["base_url"]),
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
    )

    try:
        with request.urlopen(req, timeout=240) as response:
            response_text = response.read().decode("utf-8")
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return {
            "background_image_url": None,
            "local_path": None,
            "raw_path": None,
            "source": "fallback",
            "error": _sanitize_error(raw, config["model"]),
        }
    except Exception as exc:
        return {
            "background_image_url": None,
            "local_path": None,
            "raw_path": None,
            "source": "fallback",
            "error": _sanitize_error(str(exc), config["model"]),
        }

    RAW_GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(response_text, encoding="utf-8")

    data = json.loads(response_text)
    item = (data.get("data") or [{}])[0]
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    if item.get("b64_json"):
        output_path.write_bytes(b64decode(item["b64_json"]))
    elif item.get("url"):
        with request.urlopen(item["url"], timeout=240) as image_response:
            output_path.write_bytes(image_response.read())
    else:
        return {
            "background_image_url": None,
            "local_path": None,
            "raw_path": str(raw_path).replace("\\", "/"),
            "source": "fallback",
            "error": "Images API returned no image.",
        }

    return {
        "background_image_url": f"/static/emotion-color-cards/{output_path.name}",
        "local_path": str(output_path).replace("\\", "/"),
        "raw_path": str(raw_path).replace("\\", "/"),
        "source": config["source"],
        "error": f"model={data.get('model') or config['model']}; quality={data.get('quality')}; size={data.get('size')}",
    }


def _cache_file_is_available(record: EmotionColorCardCache) -> bool:
    if not record.background_image_url:
        return False
    if not record.local_path:
        return True
    return Path(record.local_path).exists()


def _record_to_payload(record: EmotionColorCardCache, *, cached: bool) -> dict[str, Any]:
    return {
        "palette_key": record.palette_key,
        "palette_signature": _json_loads(record.palette_signature, []),
        "selected_colors": _json_loads(record.selected_colors, []),
        "mixed_color": _json_loads(record.mixed_color, {"hex": record.mixed_hex}),
        "naming_result": {
            "color_name": record.color_name,
            "subtitle": record.subtitle,
            "tags": _json_loads(record.tags, []),
            "scene_hint": record.scene_hint,
            "source": "local",
        },
        "image_result": {
            "background_image_url": record.background_image_url,
            "source": record.source,
            "cached": cached,
            "prompt": record.prompt,
            "error": record.error,
        },
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


class EmotionColorCardCacheTable:
    def __init__(self, db_connection):
        self.db = db_connection
        self.db.create_tables([EmotionColorCardCache], safe=True)

    def get_or_generate(self, checkins: list[dict[str, Any]], *, force_refresh: bool = False) -> dict[str, Any]:
        palette = _build_palette(checkins)
        cached = EmotionColorCardCache.get_or_none(
            EmotionColorCardCache.palette_key == palette["palette_key"]
        )
        if cached and not force_refresh and _cache_file_is_available(cached):
            return _record_to_payload(cached, cached=True)

        mixed_color = palette["mixed_color"]
        selected_colors = palette["selected_colors"]
        naming_result = fallback_color_name(mixed_color)
        prompt = build_image_prompt(mixed_color, naming_result, selected_colors)
        output_path = GENERATED_DIR / f"emotion-color-card-{palette['palette_key']}.png"
        raw_path = RAW_GENERATED_DIR / f"emotion-color-card-{palette['palette_key']}.json"
        image_result = _call_images_api(
            prompt=prompt,
            output_path=output_path,
            raw_path=raw_path,
        )

        defaults = {
            "palette_signature": palette["palette_signature"],
            "mixed_hex": mixed_color["hex"],
            "mixed_color": _json_dumps(mixed_color),
            "selected_colors": _json_dumps(selected_colors),
            "color_name": naming_result["color_name"],
            "subtitle": naming_result["subtitle"],
            "tags": _json_dumps(naming_result["tags"]),
            "scene_hint": naming_result["scene_hint"],
            "background_image_url": image_result["background_image_url"],
            "local_path": image_result["local_path"],
            "raw_path": image_result["raw_path"],
            "prompt": prompt,
            "source": image_result["source"],
            "error": image_result["error"],
            "updated_at": _now(),
        }
        EmotionColorCardCache.insert(
            palette_key=palette["palette_key"],
            created_at=_now(),
            **defaults,
        ).on_conflict(
            conflict_target=[EmotionColorCardCache.palette_key],
            update=defaults,
        ).execute()

        record = EmotionColorCardCache.get(EmotionColorCardCache.palette_key == palette["palette_key"])
        return _record_to_payload(record, cached=False)


emotion_color_card_cache_table = EmotionColorCardCacheTable(status_db)
