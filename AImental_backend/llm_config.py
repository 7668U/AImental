from pathlib import Path
import os

from dotenv import load_dotenv
from openai import OpenAI

from llm_security import (
    LLMSecurityError,
    SecureLLMClient,
    build_security_config,
    redact_secrets,
    validate_base_url,
)


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

load_dotenv(PROJECT_ROOT / ".env", override=False)
load_dotenv(BACKEND_DIR / ".env", override=True)

HEPAI_API_KEY = os.getenv("HEPAI_API_KEY", "").strip()
HEPAI_BASE_URL = os.getenv("HEPAI_BASE_URL", "https://aiapi.ihep.ac.cn/apiv2").strip() or "https://aiapi.ihep.ac.cn/apiv2"
HEPAI_MODEL = os.getenv("HEPAI_MODEL", "hepai/deepseek-v4-pro").strip() or "hepai/deepseek-v4-pro"
LLM_SECURITY = build_security_config(model=HEPAI_MODEL)


def create_llm_client():
    if not HEPAI_API_KEY:
        return None
    try:
        validate_base_url(HEPAI_BASE_URL, LLM_SECURITY.allowed_hosts)
        raw_client = OpenAI(
            api_key=HEPAI_API_KEY,
            base_url=HEPAI_BASE_URL,
            timeout=LLM_SECURITY.default_timeout_seconds,
            max_retries=LLM_SECURITY.max_retries,
        )
        return SecureLLMClient(
            raw_client,
            LLM_SECURITY,
            secrets=[HEPAI_API_KEY],
        )
    except LLMSecurityError as exc:
        print(f"Refusing to initialize LLM client: {exc}")
        return None
    except Exception as exc:
        print(f"Unable to initialize HEPAI OpenAI-compatible client: {redact_secrets(exc, [HEPAI_API_KEY])}")
        return None


client = create_llm_client()
IS_MOCK_API = client is None
