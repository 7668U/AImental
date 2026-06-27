from __future__ import annotations

import json
import uuid
from base64 import b64decode
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, request

from backend.app import config


@dataclass
class ImageResult:
    background_image_url: str | None
    local_path: str | None
    raw_path: str | None
    prompt: str
    source: str
    error: str | None = None


def _sanitize_error(text: str, model: str | None = None) -> str:
    if not text:
        return "HEPAI Images API failed."

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    joined = " ".join(lines)
    model_label = f" for {model}" if model else ""
    return f"HEPAI Images API failed{model_label}: {joined[:500]}"


def _images_api_request(
    *,
    api_key: str,
    base_url: str,
    model: str,
    prompt: str,
    output_path: Path,
    raw_path: Path,
) -> ImageResult:
    body = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": config.IMAGE_SIZE,
        "quality": config.IMAGE_QUALITY,
        "output_format": "png",
    }
    url = f"{base_url.rstrip('/')}/images/generations"
    payload = json.dumps(body).encode("utf-8")
    req = request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with request.urlopen(req, timeout=240) as response:
            response_text = response.read().decode("utf-8")
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return ImageResult(None, None, None, prompt, "fallback", _sanitize_error(raw, model))
    except Exception as exc:
        return ImageResult(None, None, None, prompt, "fallback", str(exc)[:500])

    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(response_text, encoding="utf-8")

    data = json.loads(response_text)
    item = (data.get("data") or [{}])[0]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if item.get("b64_json"):
        output_path.write_bytes(b64decode(item["b64_json"]))
    elif item.get("url"):
        with request.urlopen(item["url"], timeout=240) as image_response:
            output_path.write_bytes(image_response.read())
    else:
        return ImageResult(None, None, str(raw_path), prompt, "fallback", "HEPAI Images API returned no image.")

    return ImageResult(
        background_image_url=f"/generated/{output_path.name}",
        local_path=str(output_path),
        raw_path=str(raw_path),
        prompt=prompt,
        source="hepai-images",
        error=f"model={model}; quality={data.get('quality')}; size={data.get('size')}",
    )


def build_image_prompt(mixed_color: dict[str, Any], naming_result: dict[str, Any]) -> str:
    tags = ", ".join(naming_result.get("tags", []))
    return f"""
Generate a refined vertical 3:4 emotional color-card background image at exactly 1088x1456 pixels if supported.

Color name: {naming_result.get("color_name", "")}
Main mixed color: {mixed_color.get("hex", "")}
Subtitle mood: {naming_result.get("subtitle", "")}
Mood keywords: {tags}
Scene direction: {naming_result.get("scene_hint", "")}

Visual requirements:
- No text, no letters, no numbers, no logo, no watermark, no signature.
- Overall palette should stay close to {mixed_color.get("hex", "")}.
- Gentle, healing, low-saturation, clean, premium editorial atmosphere.
- Leave a large calm negative-space area in the center for one short Chinese color name.
- Keep important objects away from the outer edges, especially the top and bottom 12%.
- Use a soft scene or abstract still-life based on "{naming_result.get("scene_hint", "")}".
- Avoid frontal human faces and complicated character relationships.
- Suitable as a polished background for a vertical 3:4 1080x1440 share card without cropping.
""".strip()


def generate_background(mixed_color: dict[str, Any], naming_result: dict[str, Any]) -> ImageResult:
    prompt = build_image_prompt(mixed_color, naming_result)
    if not config.HEPAI_API_KEY or not config.HEPAI_IMAGE_MODEL:
        return ImageResult(None, None, None, prompt, "fallback", "Missing HEPAI image configuration.")

    config.GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    config.RAW_GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    output_name = f"emotion-bg-hepai-{uuid.uuid4().hex[:10]}.png"
    raw_name = f"{Path(output_name).stem}.json"

    return _images_api_request(
        api_key=config.HEPAI_API_KEY,
        base_url=config.HEPAI_BASE_URL,
        model=config.HEPAI_IMAGE_MODEL,
        prompt=prompt,
        output_path=config.GENERATED_DIR / output_name,
        raw_path=config.RAW_GENERATED_DIR / raw_name,
    )
