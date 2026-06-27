import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

load_dotenv(PROJECT_ROOT / ".env", override=False)
load_dotenv(BACKEND_DIR / ".env", override=True)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


ENABLE_COMMUNITY_BACKEND = env_bool("ENABLE_COMMUNITY_BACKEND", False)
