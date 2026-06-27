from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
LAB_ROOT = BACKEND_DIR.parent
PROJECT_ROOT = LAB_ROOT.parent
FRONTEND_DIR = LAB_ROOT / "frontend"
GENERATED_DIR = LAB_ROOT / "generated"
RAW_GENERATED_DIR = GENERATED_DIR / "raw"
COLOR_DATA_PATH = APP_DIR / "data" / "colors.json"
IMAGE_TOOL_PATH = PROJECT_ROOT / "tools" / "imagegen" / "generate-gpt-image-2.mjs"

load_dotenv(PROJECT_ROOT / ".env", override=False)
load_dotenv(LAB_ROOT / ".env", override=False)

HEPAI_API_KEY = os.getenv("HEPAI_API_KEY", "").strip()
HEPAI_BASE_URL = os.getenv("HEPAI_BASE_URL", "https://aiapi.ihep.ac.cn/apiv2").strip()
HEPAI_MODEL = os.getenv("HEPAI_MODEL", "hepai/deepseek-v4-pro").strip()
HEPAI_IMAGE_MODEL = os.getenv("HEPAI_IMAGE_MODEL", "openai/gpt-image-2").strip()

IMAGE_SIZE = os.getenv("HEPAI_IMAGE_SIZE", os.getenv("FHL_IMAGE_SIZE", "1088x1456")).strip()
IMAGE_QUALITY = os.getenv("HEPAI_IMAGE_QUALITY", os.getenv("FHL_IMAGE_QUALITY", "low")).strip()
