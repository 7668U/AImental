from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.app import config
from backend.app.services.color_mix import mix_colors
from backend.app.services.color_naming import name_mixed_color
from backend.app.services.image_generation import generate_background

app = FastAPI(title="Emotion Color Palette Lab", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

config.GENERATED_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/generated", StaticFiles(directory=config.GENERATED_DIR), name="generated")
app.mount("/static", StaticFiles(directory=config.FRONTEND_DIR), name="frontend")


class GenerateCardRequest(BaseModel):
    color_ids: list[int] = Field(min_length=7, max_length=30)
    generate_image: bool = True


class RegenerateBackgroundRequest(BaseModel):
    mixed_hex: str
    color_name: str
    subtitle: str
    tags: list[str] = Field(default_factory=list)
    scene_hint: str


def _load_colors() -> list[dict[str, Any]]:
    with config.COLOR_DATA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def _selected_colors(color_ids: list[int]) -> list[dict[str, Any]]:
    colors = _load_colors()
    by_id = {item["id"]: item for item in colors}
    unique_ids = []
    for color_id in color_ids:
        if color_id not in unique_ids:
            unique_ids.append(color_id)

    if len(unique_ids) != len(color_ids):
        raise HTTPException(status_code=400, detail="请不要重复选择同一个颜色。")

    missing = [color_id for color_id in unique_ids if color_id not in by_id]
    if missing:
        raise HTTPException(status_code=400, detail=f"未知颜色 ID: {missing}")

    return [by_id[color_id] for color_id in unique_ids]


def _date_text() -> str:
    return datetime.now().strftime("%Y.%m")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(config.FRONTEND_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "hepai": {
            "base_url": config.HEPAI_BASE_URL,
            "model": config.HEPAI_MODEL,
            "image_model": config.HEPAI_IMAGE_MODEL,
            "configured": bool(config.HEPAI_API_KEY),
        },
        "image_generation": {
            "provider": "hepai-images",
            "size": config.IMAGE_SIZE,
            "quality": config.IMAGE_QUALITY,
            "configured": bool(config.HEPAI_API_KEY and config.HEPAI_IMAGE_MODEL),
        },
    }


@app.get("/api/colors")
def colors() -> dict[str, Any]:
    return {"colors": _load_colors()}


@app.post("/api/generate-card-data")
def generate_card_data(payload: GenerateCardRequest) -> dict[str, Any]:
    selected = _selected_colors(payload.color_ids)
    mixed = mix_colors([color["hex"] for color in selected])
    naming = name_mixed_color(mixed, selected)

    image = None
    if payload.generate_image:
        image = generate_background(mixed, naming)

    return {
        "selected_colors": selected,
        "mixed_color": mixed,
        "naming_result": naming,
        "image_result": {
            "background_image_url": image.background_image_url if image else None,
            "source": image.source if image else "canvas-fallback",
            "prompt": image.prompt if image else None,
            "error": image.error if image else None,
        },
        "canvas_config": {
            "width": 1080,
            "height": 1440,
            "layout": "vertical-emotion-card",
        },
        "date_text": _date_text(),
    }


@app.post("/api/regenerate-background")
def regenerate_background(payload: RegenerateBackgroundRequest) -> dict[str, Any]:
    mixed = mix_colors([payload.mixed_hex])
    naming = {
        "color_name": payload.color_name,
        "subtitle": payload.subtitle,
        "tags": payload.tags[:3],
        "scene_hint": payload.scene_hint,
    }
    image = generate_background(mixed, naming)
    return {
        "background_image_url": image.background_image_url,
        "source": image.source,
        "prompt": image.prompt,
        "error": image.error,
    }
