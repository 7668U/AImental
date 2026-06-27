from pathlib import Path
import os

from dotenv import load_dotenv
from openai import OpenAI


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

load_dotenv(PROJECT_ROOT / ".env", override=False)
load_dotenv(BACKEND_DIR / ".env", override=True)

HEPAI_API_KEY = os.getenv("HEPAI_API_KEY", "").strip()
HEPAI_BASE_URL = os.getenv("HEPAI_BASE_URL", "https://aiapi.ihep.ac.cn/apiv2").strip()
HEPAI_MODEL = os.getenv("HEPAI_MODEL", "hepai/deepseek-v4-pro").strip()


def create_llm_client():
    if not HEPAI_API_KEY:
        return None
    try:
        return OpenAI(api_key=HEPAI_API_KEY, base_url=HEPAI_BASE_URL)
    except Exception as exc:
        print(f"Unable to initialize HEPAI OpenAI-compatible client: {exc}")
        return None


client = create_llm_client()
IS_MOCK_API = client is None
