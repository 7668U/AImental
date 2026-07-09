import json
import os
from typing import Any, Dict, List

from pydantic import BaseModel, Field, ValidationError

from llm_config import HEPAI_MODEL, IS_MOCK_API, client


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


AFFINITY_LLM_TIMEOUT_SECONDS = _env_float("AFFINITY_LLM_TIMEOUT_SECONDS", 30.0)


def _no_retry_client():
    if client and hasattr(client, "with_options"):
        return client.with_options(max_retries=0)
    return client


class CommunityAffinityAssessment(BaseModel):
    base_delta: float = Field(
        ...,
        ge=-8.0,
        le=3.0,
        description="本批聊天带来的基础好感度变化，不含 MBTI 倍率。",
    )
    interaction_quality: str = Field(
        ...,
        description="warm/deep/routine/spam/conflict/boundary_violation/repair 等关系质量标签。",
    )
    reason: str = Field(..., description="一句话说明为什么这样变化。")
    analysis: str = Field(..., description="简短分析本批对话的关系动态。")
    affinity_note: str = Field(..., description="角色对用户当前亲近感、信任感和相处氛围的文字描述。")
    proactive_hint: str = Field(
        "",
        description="如果以后主动发消息，适合延续的自然话题；没有就留空。",
    )


def _format_messages(messages: List[Dict[str, Any]], character_name: str) -> str:
    if not messages:
        return "无可用聊天记录。"
    lines = []
    for index, message in enumerate(messages, start=1):
        role = character_name if message.get("role") == "ai" else "用户"
        content = str(message.get("content", "")).strip()
        if content:
            lines.append(f"{index}. {role}: {content}")
    return "\n".join(lines) if lines else "无可用聊天记录。"


def assess_community_affinity(
    *,
    character_profile: Dict[str, Any],
    current_score: float,
    recent_messages: List[Dict[str, Any]],
    favorability_history: List[Dict[str, Any]],
    memory_context: Dict[str, Any],
) -> CommunityAffinityAssessment:
    character_name = character_profile.get("identity_core", {}).get("name", "角色")
    schema = CommunityAffinityAssessment.model_json_schema()
    prompt = f"""
# 任务
你正在评估虚拟角色“{character_name}”和用户之间最近一批聊天对关系温度的影响。

你只需要评估“这 20 条左右消息本身带来的变化”，不要重算总分。后端会根据角色 MBTI 再做升温/降温倍率。

# 角色人设
```json
{json.dumps(character_profile, ensure_ascii=False, indent=2)}
```

# 当前关系数据
当前好感度分数: {current_score}
历史好感度记录:
```json
{json.dumps(favorability_history[-12:], ensure_ascii=False, indent=2)}
```

# 长期记忆上下文
```json
{json.dumps(memory_context or {}, ensure_ascii=False, indent=2)}
```

# 本批聊天记录
---
{_format_messages(recent_messages, character_name)}
---

# 评估规则
1. 只根据本批聊天给 `base_delta`，不要输出新的总分。
2. 高质量互动可以明显增加：用户真诚分享、认真回应、记得角色说过的话、表达关心，可给 +1 到 +3。
3. 普通日常聊天小幅增加：通常 +0.2 到 +0.8。
4. 仅表情、重复短句、无意义刷屏，给 0 或 -0.5。
5. 冷淡但无冒犯，通常 0。
6. 争吵、羞辱、操控、强迫角色、越界内容，可给 -2 到 -8。
7. 如果用户在修复关系、道歉或重新认真沟通，可以给小幅正向或减少负向。
8. `affinity_note` 写成角色主观能感受到的关系氛围，不要写数值。
9. 输出必须是严格 JSON，字段遵循下面 schema。

```json
{json.dumps(schema, ensure_ascii=False, indent=2)}
```
"""

    fallback = CommunityAffinityAssessment(
        base_delta=0.0,
        interaction_quality="routine",
        reason="本批聊天没有足够清晰的关系变化信号。",
        analysis="保持当前关系温度。",
        affinity_note="关系温度暂时保持稳定，角色会按照已有熟悉程度自然回应。",
        proactive_hint="",
    )

    try:
        if IS_MOCK_API:
            return fallback
        response = _no_retry_client().chat.completions.create(
            model=HEPAI_MODEL,
            messages=[{"role": "system", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.25,
            max_tokens=1200,
            timeout=AFFINITY_LLM_TIMEOUT_SECONDS,
        )
        return CommunityAffinityAssessment.model_validate_json(response.choices[0].message.content)
    except (ValidationError, Exception) as exc:
        print(f"[affinity] 好感度评估失败，使用保守兜底: {exc}")
        return fallback
