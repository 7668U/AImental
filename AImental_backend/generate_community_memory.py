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


MEMORY_LLM_TIMEOUT_SECONDS = _env_float("MEMORY_LLM_TIMEOUT_SECONDS", 45.0)


def _no_retry_client():
    if client and hasattr(client, "with_options"):
        return client.with_options(max_retries=0)
    return client


class UserProfileMemoryCard(BaseModel):
    relationship_stage: str = Field(..., description="初遇、熟悉、亲近、深度信任等关系阶段")
    affinity_note: str = Field(..., description="角色对用户当前亲近感和好感氛围的文字描述，不使用数值")
    impression_summary: str = Field(..., description="角色对用户的主观印象，80到180字")
    user_traits_observed: List[str] = Field(default_factory=list)
    user_preferences: List[str] = Field(default_factory=list)
    emotional_patterns: List[str] = Field(default_factory=list)
    important_memories: List[str] = Field(default_factory=list)
    unresolved_threads: List[str] = Field(default_factory=list)
    conversation_tone: str = Field(..., description="当前两人聊天的自然氛围")
    updated_reason: str = Field(..., description="本次为什么更新画像")


class HistorySummaryCard(BaseModel):
    title: str = Field(..., description="这段记忆的短标题")
    summary: str = Field(..., description="这100条左右聊天的压缩摘要，120到260字")
    key_events: List[str] = Field(default_factory=list)
    user_facts: List[str] = Field(default_factory=list)
    emotional_turning_points: List[str] = Field(default_factory=list)
    relationship_development: str = ""
    open_threads: List[str] = Field(default_factory=list)


def build_default_profile_card() -> Dict[str, Any]:
    return UserProfileMemoryCard(
        relationship_stage="初遇",
        affinity_note="还在建立信任和熟悉感，适合保持温和、礼貌、不过度亲密的距离。",
        impression_summary="两个人刚开始认识，角色对用户的了解还很少，需要通过接下来的聊天慢慢形成印象。",
        user_traits_observed=[],
        user_preferences=[],
        emotional_patterns=[],
        important_memories=[],
        unresolved_threads=[],
        conversation_tone="还比较陌生，适合温和、谨慎、不过度亲密地回应。",
        updated_reason="初始化默认画像卡",
    ).model_dump()


def _format_messages(messages: List[Dict[str, Any]], character_name: str) -> str:
    lines = []
    for index, message in enumerate(messages, start=1):
        role = character_name if message.get("role") == "ai" else "用户"
        content = str(message.get("content", "")).strip()
        if content:
            lines.append(f"{index}. {role}: {content}")
    return "\n".join(lines) if lines else "无可用聊天记录。"


def generate_user_profile_memory_card(
    *,
    character_profile: Dict[str, Any],
    existing_profile_card: Dict[str, Any],
    recent_messages: List[Dict[str, Any]],
    history_summaries: List[Dict[str, Any]],
    total_message_count: int,
) -> Dict[str, Any]:
    character_name = character_profile.get("identity_core", {}).get("name", "角色")
    schema = UserProfileMemoryCard.model_json_schema()
    prompt = f"""
# 任务
你正在为虚拟角色“{character_name}”更新一张“TA眼中的用户画像卡”。

这张卡不是冷冰冰的用户档案，而是角色对用户的主观印象、关系阶段和共同回忆。它会在后续聊天中帮助角色更像一个真正认识用户的人。

# 角色人设
```json
{json.dumps(character_profile, ensure_ascii=False, indent=2)}
```

# 现有画像卡
```json
{json.dumps(existing_profile_card or build_default_profile_card(), ensure_ascii=False, indent=2)}
```

# 已有历史摘要卡
```json
{json.dumps(history_summaries, ensure_ascii=False, indent=2)}
```

# 最近聊天记录
总消息数: {total_message_count}
---
{_format_messages(recent_messages, character_name)}
---

# 更新规则
1. 只记录用户明确表达过、或能从多次对话中稳定观察到的信息；不要编造。
2. 画像是“这个角色眼中的用户”，可以带一点角色主观感受，但必须克制。
3. `relationship_stage` 根据聊天深度判断：初遇 / 熟悉 / 亲近 / 深度信任。
4. `affinity_note` 只写角色主观上的亲近感、信任感和好感氛围，不要写数值分数。
5. `important_memories` 记录两个人共同聊过、以后值得被想起的事。
6. `unresolved_threads` 记录下次可以自然关心的未完成话题。
7. 输出必须是严格 JSON，字段遵循下面 schema。

```json
{json.dumps(schema, ensure_ascii=False, indent=2)}
```
"""

    try:
        if IS_MOCK_API:
            return build_default_profile_card()
        response = _no_retry_client().chat.completions.create(
            model=HEPAI_MODEL,
            messages=[{"role": "system", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_tokens=1600,
            timeout=MEMORY_LLM_TIMEOUT_SECONDS,
        )
        card = UserProfileMemoryCard.model_validate_json(response.choices[0].message.content)
        return card.model_dump()
    except (ValidationError, Exception) as exc:
        print(f"[memory] 用户画像卡生成失败，保留旧画像: {exc}")
        return existing_profile_card or build_default_profile_card()


def generate_history_summary_card(
    *,
    character_profile: Dict[str, Any],
    messages: List[Dict[str, Any]],
    start_index: int,
    end_index: int,
) -> Dict[str, Any]:
    character_name = character_profile.get("identity_core", {}).get("name", "角色")
    schema = HistorySummaryCard.model_json_schema()
    prompt = f"""
# 任务
你要把“{character_name}”和用户的一段聊天压缩成一张历史摘要卡。

# 角色人设
```json
{json.dumps(character_profile, ensure_ascii=False, indent=2)}
```

# 聊天范围
消息序号: {start_index + 1} 到 {end_index}

# 聊天记录
---
{_format_messages(messages, character_name)}
---

# 摘要规则
1. 保留重要事实、情绪变化、共同回忆、未完成话题。
2. 不要逐条复述，不要写流水账。
3. 如果出现用户偏好、禁忌、重要人物、长期困扰，要写进对应字段。
4. 输出必须是严格 JSON，字段遵循下面 schema。

```json
{json.dumps(schema, ensure_ascii=False, indent=2)}
```
"""

    fallback = HistorySummaryCard(
        title=f"聊天摘要 {start_index + 1}-{end_index}",
        summary="这段聊天已经被压缩记录，但模型暂时没有生成更细的摘要。",
        key_events=[],
        user_facts=[],
        emotional_turning_points=[],
        relationship_development="关系继续推进。",
        open_threads=[],
    ).model_dump()

    try:
        if IS_MOCK_API:
            return fallback
        response = _no_retry_client().chat.completions.create(
            model=HEPAI_MODEL,
            messages=[{"role": "system", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.35,
            max_tokens=1800,
            timeout=MEMORY_LLM_TIMEOUT_SECONDS,
        )
        card = HistorySummaryCard.model_validate_json(response.choices[0].message.content)
        return card.model_dump()
    except (ValidationError, Exception) as exc:
        print(f"[memory] 历史摘要卡生成失败，使用保守兜底: {exc}")
        return fallback


def merge_history_summary_cards(
    *,
    character_profile: Dict[str, Any],
    first_summary: Dict[str, Any],
    second_summary: Dict[str, Any],
) -> Dict[str, Any]:
    schema = HistorySummaryCard.model_json_schema()
    character_name = character_profile.get("identity_core", {}).get("name", "角色")
    prompt = f"""
# 任务
你要把“{character_name}”和用户最早的两张历史摘要卡合并成一张更高层的记忆。

# 第一张摘要
```json
{json.dumps(first_summary, ensure_ascii=False, indent=2)}
```

# 第二张摘要
```json
{json.dumps(second_summary, ensure_ascii=False, indent=2)}
```

# 合并规则
1. 更早的细节可以压缩，但重要事实、关系变化、用户偏好和未完成话题必须保留。
2. 合并后仍然是一张摘要卡，不要超过260字主摘要。
3. 输出严格 JSON，遵循下面 schema。

```json
{json.dumps(schema, ensure_ascii=False, indent=2)}
```
"""

    fallback = HistorySummaryCard(
        title=f"{first_summary.get('title', '早期记忆')} / {second_summary.get('title', '早期记忆')}",
        summary="；".join(
            part for part in [first_summary.get("summary", ""), second_summary.get("summary", "")]
            if part
        )[:260],
        key_events=(first_summary.get("key_events", []) + second_summary.get("key_events", []))[:8],
        user_facts=(first_summary.get("user_facts", []) + second_summary.get("user_facts", []))[:8],
        emotional_turning_points=(
            first_summary.get("emotional_turning_points", [])
            + second_summary.get("emotional_turning_points", [])
        )[:8],
        relationship_development="；".join(
            part for part in [
                first_summary.get("relationship_development", ""),
                second_summary.get("relationship_development", ""),
            ]
            if part
        )[:180],
        open_threads=(first_summary.get("open_threads", []) + second_summary.get("open_threads", []))[:8],
    ).model_dump()

    try:
        if IS_MOCK_API:
            return fallback
        response = _no_retry_client().chat.completions.create(
            model=HEPAI_MODEL,
            messages=[{"role": "system", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1600,
            timeout=MEMORY_LLM_TIMEOUT_SECONDS,
        )
        card = HistorySummaryCard.model_validate_json(response.choices[0].message.content)
        return card.model_dump()
    except (ValidationError, Exception) as exc:
        print(f"[memory] 摘要卡合并失败，使用保守兜底: {exc}")
        return fallback
