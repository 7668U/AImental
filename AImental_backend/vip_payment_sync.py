import hashlib
import hmac
import json
import os
import threading
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional, Tuple

import requests

from model.vip import VipOrder
from vip_virtual_payment import (
    _virtual_payment_app_key,
    _virtual_payment_env,
    calc_pay_sig,
    virtual_out_trade_no,
)


WECHAT_XPAY_BASE_URL = "https://api.weixin.qq.com"
_ACCESS_TOKEN_LOCK = threading.Lock()
_ACCESS_TOKEN_CACHE: Dict[str, Any] = {
    "value": "",
    "expires_at": 0,
}


class VipPaymentSyncError(Exception):
    def __init__(self, message: str, code: str = "vip_payment_sync_failed"):
        super().__init__(message)
        self.code = code


def _wechat_app_id() -> str:
    return os.getenv("WECHAT_APP_ID", "").strip()


def _wechat_app_secret() -> str:
    return os.getenv("WECHAT_APP_SECRET", "").strip()


def _message_token() -> str:
    return (
        os.getenv("WECHAT_VIRTUAL_PAY_CALLBACK_TOKEN", "").strip()
        or os.getenv("WECHAT_MESSAGE_TOKEN", "").strip()
    )


def _json_body(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _request_access_token() -> str:
    app_id = _wechat_app_id()
    app_secret = _wechat_app_secret()
    if not app_id or not app_secret:
        raise VipPaymentSyncError(
            "WeChat app credentials are not configured.",
            code="wechat_credentials_missing",
        )

    try:
        response = requests.get(
            f"{WECHAT_XPAY_BASE_URL}/cgi-bin/token",
            params={
                "grant_type": "client_credential",
                "appid": app_id,
                "secret": app_secret,
            },
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise VipPaymentSyncError(
            f"Could not get WeChat access token: {exc}",
            code="wechat_access_token_failed",
        ) from exc

    access_token = str(payload.get("access_token") or "")
    if not access_token:
        raise VipPaymentSyncError(
            str(payload.get("errmsg") or "WeChat did not return an access token."),
            code="wechat_access_token_failed",
        )
    return access_token


def get_wechat_access_token() -> str:
    now = int(time.time())
    with _ACCESS_TOKEN_LOCK:
        if _ACCESS_TOKEN_CACHE["value"] and _ACCESS_TOKEN_CACHE["expires_at"] > now + 60:
            return _ACCESS_TOKEN_CACHE["value"]
        access_token = _request_access_token()
        _ACCESS_TOKEN_CACHE.update(
            {
                "value": access_token,
                "expires_at": now + 5400,
            }
        )
        return access_token


def query_virtual_order(order: VipOrder, user: Any) -> Dict[str, Any]:
    app_key = _virtual_payment_app_key()
    if not app_key:
        raise VipPaymentSyncError(
            "The WeChat virtual payment AppKey is not configured.",
            code="wechat_payment_app_key_missing",
        )

    request_body = _json_body(
        {
            "openid": user.openid,
            "env": _virtual_payment_env(),
            "order_id": virtual_out_trade_no(order),
        }
    )
    pay_sig = calc_pay_sig("/xpay/query_order", request_body, app_key)
    try:
        response = requests.post(
            f"{WECHAT_XPAY_BASE_URL}/xpay/query_order",
            params={
                "access_token": get_wechat_access_token(),
                "pay_sig": pay_sig,
            },
            data=request_body.encode("utf-8"),
            headers={"Content-Type": "application/json"},
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise VipPaymentSyncError(
            f"Could not query the WeChat virtual payment order: {exc}",
            code="wechat_order_query_failed",
        ) from exc

    if int(payload.get("errcode") or 0) != 0:
        raise VipPaymentSyncError(
            str(payload.get("errmsg") or "WeChat order query failed."),
            code="wechat_order_query_failed",
        )
    return payload.get("order") or {}


def reconcile_order(order: VipOrder, user: Any, vip_service: Any) -> Tuple[VipOrder, bool, int]:
    provider_order = query_virtual_order(order, user)
    provider_status = int(provider_order.get("status") or 0)
    if provider_status not in {2, 3, 4}:
        return order, False, provider_status

    provider_amount = int(provider_order.get("order_fee") or 0)
    if provider_amount and provider_amount != order.amount_fen:
        raise VipPaymentSyncError(
            "The paid order amount does not match the local order.",
            code="wechat_order_amount_mismatch",
        )

    transaction_id = (
        provider_order.get("wxpay_order_id")
        or provider_order.get("wx_order_id")
        or provider_order.get("channel_order_id")
        or f"wechat-{virtual_out_trade_no(order)}"
    )
    paid_at = int(provider_order.get("paid_time") or 0) or None
    fulfilled = vip_service.mark_order_paid(
        order_id=order.id,
        user_id=order.user_id,
        transaction_id=str(transaction_id),
        timestamp=paid_at,
    )
    return fulfilled, True, provider_status


def verify_message_signature(
    *,
    signature: str,
    timestamp: str,
    nonce: str,
    token: Optional[str] = None,
) -> bool:
    callback_token = token or _message_token()
    if not callback_token or not signature or not timestamp or not nonce:
        return False
    expected = hashlib.sha1(
        "".join(sorted((callback_token, timestamp, nonce))).encode("utf-8")
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def parse_callback_body(raw_body: bytes) -> Tuple[Dict[str, Any], str]:
    body = raw_body.decode("utf-8").strip()
    if not body:
        raise VipPaymentSyncError(
            "The WeChat callback body is empty.",
            code="wechat_callback_invalid",
        )
    if body.startswith("<"):
        try:
            root = ET.fromstring(body)
        except ET.ParseError as exc:
            raise VipPaymentSyncError(
                "The WeChat callback XML is invalid.",
                code="wechat_callback_invalid",
            ) from exc
        return _xml_to_dict(root), "xml"
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise VipPaymentSyncError(
            "The WeChat callback JSON is invalid.",
            code="wechat_callback_invalid",
        ) from exc
    if not isinstance(payload, dict):
        raise VipPaymentSyncError(
            "The WeChat callback must be an object.",
            code="wechat_callback_invalid",
        )
    return payload, "json"


def _xml_to_dict(element: ET.Element) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for child in element:
        if len(child):
            result[child.tag] = _xml_to_dict(child)
        else:
            result[child.tag] = child.text or ""
    return result


def find_order_for_callback(
    *,
    attach: str = "",
    out_trade_no: str = "",
) -> Optional[VipOrder]:
    if attach:
        order = VipOrder.get_or_none(VipOrder.id == attach)
        if order:
            return order
    if not out_trade_no:
        return None
    candidates = (
        VipOrder.select()
        .where(
            VipOrder.status.in_(
                ["pending", "closed", "paid", "fulfillment_pending"]
            )
        )
        .order_by(VipOrder.created_at.desc())
        .limit(500)
    )
    for order in candidates:
        if virtual_out_trade_no(order) == out_trade_no:
            return order
    return None


def callback_success_response(fmt: str) -> Tuple[str, str]:
    if fmt == "xml":
        return (
            "<xml><ErrCode>0</ErrCode><ErrMsg><![CDATA[success]]></ErrMsg></xml>",
            "application/xml",
        )
    return json.dumps({"ErrCode": 0, "ErrMsg": "success"}), "application/json"


def callback_failure_response(message: str, fmt: str) -> Tuple[str, str]:
    safe_message = message.replace("<", "").replace(">", "")
    if fmt == "xml":
        return (
            f"<xml><ErrCode>-1</ErrCode><ErrMsg><![CDATA[{safe_message}]]></ErrMsg></xml>",
            "application/xml",
        )
    return (
        json.dumps({"ErrCode": -1, "ErrMsg": safe_message}),
        "application/json",
    )
