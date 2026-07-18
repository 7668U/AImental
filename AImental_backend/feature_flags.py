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
# 心灵社区开发模式：开启后不调用 LLM 生成 AI 日程，
# 而是把历史上某天已生成的完整日程克隆到目标日期作为测试数据，启动即可用。
COMMUNITY_DEV_MODE = env_bool("COMMUNITY_DEV_MODE", False)
# 可选：指定克隆日程的来源日期（YYYY-MM-DD）。留空则自动选用该角色最近一个有日程的历史日期。
COMMUNITY_DEV_SCHEDULE_SOURCE_DATE = (os.getenv("COMMUNITY_DEV_SCHEDULE_SOURCE_DATE") or "").strip()
ENABLE_VIP_MOCK_PAYMENT = env_bool("ENABLE_VIP_MOCK_PAYMENT", False)
ENABLE_VIP_LOCAL_VIRTUAL_PAYMENT = env_bool(
    "ENABLE_VIP_LOCAL_VIRTUAL_PAYMENT",
    True,
)
ENABLE_VIP_TEST_TOOLS = env_bool(
    "ENABLE_VIP_TEST_TOOLS",
    ENABLE_VIP_LOCAL_VIRTUAL_PAYMENT or ENABLE_VIP_MOCK_PAYMENT,
)
