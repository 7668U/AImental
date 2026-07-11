import hashlib
import math
import uuid
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from vip_service import (
    ReservationResult,
    VipDuplicateRequest,
    VipError,
    VipQuotaExceeded,
    vip_service,
)


def estimate_text_tokens(text: str) -> int:
    if not text:
        return 0
    utf8_bytes = len(text.encode("utf-8"))
    return max(len(text), math.ceil(utf8_bytes / 4))


def validate_ai_input(
    text: str,
    *,
    max_chars: int,
    max_bytes: int,
    max_tokens: int,
) -> str:
    normalized = (text or "").strip()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "input_empty",
                "message": "请输入内容后再发送。",
            },
        )
    chars = len(normalized)
    utf8_bytes = len(normalized.encode("utf-8"))
    estimated_tokens = estimate_text_tokens(normalized)
    if (
        chars > max_chars
        or utf8_bytes > max_bytes
        or estimated_tokens > max_tokens
    ):
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail={
                "code": "input_too_large",
                "message": "本次输入内容过长，请精简后重试。",
                "limits": {
                    "max_chars": max_chars,
                    "max_bytes": max_bytes,
                    "max_tokens": max_tokens,
                },
            },
        )
    return normalized


def build_request_id(
    *,
    user_id: str,
    feature: str,
    supplied_request_id: Optional[str] = None,
) -> str:
    client_value = (supplied_request_id or "").strip()
    if not client_value:
        client_value = str(uuid.uuid4())
    digest = hashlib.sha256(
        f"{user_id}:{feature}:{client_value}".encode("utf-8")
    ).hexdigest()
    return f"{feature}:{digest[:56]}"


def reserve_feature_or_http(
    *,
    user_id: str,
    feature: str,
    supplied_request_id: Optional[str] = None,
) -> ReservationResult:
    request_id = build_request_id(
        user_id=user_id,
        feature=feature,
        supplied_request_id=supplied_request_id,
    )
    try:
        return vip_service.reserve(
            user_id=user_id,
            feature=feature,
            request_id=request_id,
        )
    except VipQuotaExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": exc.code,
                "message": str(exc),
                "feature": feature,
                "vip_state": vip_service.get_summary(user_id),
            },
        ) from exc
    except VipDuplicateRequest as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": exc.code,
                "message": str(exc),
                "feature": feature,
            },
        ) from exc
    except VipError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": exc.code,
                "message": str(exc),
                "feature": feature,
            },
        ) from exc


def release_reservation(reservation: Optional[ReservationResult]) -> None:
    if not reservation:
        return
    vip_service.release(reservation.reservation_id)


def confirm_reservation(reservation: ReservationResult) -> None:
    vip_service.confirm(reservation.reservation_id)


def trim_chat_messages(
    messages: List[Dict[str, Any]],
    *,
    max_tokens: int,
) -> List[Dict[str, Any]]:
    system_messages = [
        message for message in messages if message.get("role") == "system"
    ]
    conversation = [
        message for message in messages if message.get("role") != "system"
    ]
    system_cost = sum(
        estimate_text_tokens(str(message.get("content", ""))) + 8
        for message in system_messages
    )
    if system_cost >= max_tokens:
        raise ValueError("System context exceeds the model input budget.")
    budget = max_tokens - system_cost
    selected: List[Dict[str, Any]] = []
    used = 0
    for message in reversed(conversation):
        cost = estimate_text_tokens(str(message.get("content", ""))) + 8
        if selected and used + cost > budget:
            break
        if cost > budget:
            raise ValueError("Current message exceeds the model input budget.")
        selected.append(message)
        used += cost
    selected.reverse()
    return [*system_messages, *selected]
