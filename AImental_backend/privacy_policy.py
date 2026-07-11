import hashlib
import json
import os
from datetime import date
from typing import Any, Dict


PRIVACY_POLICY_VERSION = os.getenv("PRIVACY_POLICY_VERSION", "2026-07-11").strip()
PRIVACY_POLICY_EFFECTIVE_DATE = os.getenv(
    "PRIVACY_POLICY_EFFECTIVE_DATE", "2026-07-11"
).strip()
PRIVACY_OPERATOR_NAME = os.getenv(
    "PRIVACY_OPERATOR_NAME", "Feel Yourself 小程序运营者"
).strip()
PRIVACY_CONTACT = os.getenv(
    "PRIVACY_CONTACT", "小程序内「我的 - 意见反馈」"
).strip()


def get_privacy_policy() -> Dict[str, Any]:
    return {
        "version": PRIVACY_POLICY_VERSION,
        "effective_date": PRIVACY_POLICY_EFFECTIVE_DATE,
        "title": "用户隐私保护协议",
        "summary": (
            "为了提供登录、情绪记录、心理测评、AI 陪伴和纸飞机等功能，"
            "我们会在你明确同意后处理必要信息，并采用加密、访问控制和最小必要原则保护数据。"
        ),
        "operator": PRIVACY_OPERATOR_NAME,
        "contact": PRIVACY_CONTACT,
        "sections": [
            {
                "title": "我们会处理哪些信息",
                "content": (
                    "登录时处理微信提供的用户标识；在你主动填写或上传时处理昵称、头像、"
                    "生日、性别、情绪日记、定位、照片、测评答案与结果、聊天内容、笔记、"
                    "反馈和纸飞机内容。未使用对应功能时，我们不会主动收集该类内容。"
                ),
            },
            {
                "title": "这些信息如何使用",
                "content": (
                    "用于账号识别、保存和同步你的记录、生成测评与趋势分析、提供你主动选择的"
                    "个性化 AI 互动、处理反馈，以及保障服务稳定与安全。我们不会把你的个人信息"
                    "用于与上述目的无关的用途。"
                ),
            },
            {
                "title": "我们如何保护数据",
                "content": (
                    "敏感数据库字段和用户上传文件使用行业通行的认证加密保护；查询标识采用"
                    "不可逆盲索引；访问需要身份校验，密钥与业务数据分离并支持轮换。"
                    "同时我们会限制内部访问、减少日志中的个人信息，并持续改进安全措施。"
                ),
            },
            {
                "title": "AI 功能与必要说明",
                "content": (
                    "只有在你开启相应功能时，系统才会读取为完成该次服务所必要的记录并生成回复"
                    "或分析。AI 内容仅用于陪伴和自我观察，不替代医生、心理咨询师或其他专业意见。"
                ),
            },
            {
                "title": "保存、删除与撤回同意",
                "content": (
                    "我们仅在实现服务目的所需期限内保存信息。你可以通过产品内相关功能删除记录，"
                    "也可以撤回隐私同意；撤回后我们将停止继续处理依赖同意的个人信息，"
                    "但不影响撤回前已经合法进行的处理。"
                ),
            },
            {
                "title": "你的权利与联系我们",
                "content": (
                    f"你可以查询、更正或删除个人信息，也可以撤回同意或注销账号。"
                    f"如需帮助，请通过{PRIVACY_CONTACT}联系我们。运营者：{PRIVACY_OPERATOR_NAME}。"
                ),
            },
        ],
        "notice": (
            "互联网服务无法承诺绝对零风险，但我们会采用与数据敏感程度相匹配的措施，"
            "认真保护你的隐私，并在发生安全事件时依法采取处置和通知措施。"
        ),
    }


def get_privacy_policy_digest() -> str:
    canonical = json.dumps(
        get_privacy_policy(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_policy_version(version: str) -> bool:
    return bool(version) and version == PRIVACY_POLICY_VERSION


def parse_effective_date() -> date:
    return date.fromisoformat(PRIVACY_POLICY_EFFECTIVE_DATE)
