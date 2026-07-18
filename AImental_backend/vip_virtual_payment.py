import hashlib
import hmac
import json
import os
from typing import Any, Dict, Optional

from feature_flags import ENABLE_VIP_LOCAL_VIRTUAL_PAYMENT
from model.vip import VipOrder


REQUEST_VIRTUAL_PAYMENT_URI = "requestVirtualPayment"
VIRTUAL_PAYMENT_MODE = "short_series_goods"
LOCAL_APP_KEY = "local-virtual-payment-app-key"
LOCAL_OFFER_ID = "local-offer-id"


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _virtual_payment_env() -> int:
    return _env_int("WECHAT_VIRTUAL_PAY_ENV", 1)


def _virtual_payment_app_key(env: Optional[int] = None) -> str:
    selected_env = _virtual_payment_env() if env is None else env
    key_name = (
        "WECHAT_VIRTUAL_PAY_APP_KEY"
        if selected_env == 0
        else "WECHAT_VIRTUAL_PAY_SANDBOX_APP_KEY"
    )
    return os.getenv(key_name, "").strip()


def _json_dumps(payload: Dict[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _load_product_ids() -> Dict[str, str]:
    raw = os.getenv("WECHAT_VIRTUAL_PAY_PRODUCT_IDS", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {
        str(key): str(value)
        for key, value in parsed.items()
        if key and value
    }


def calc_pay_sig(uri: str, sign_data: str, app_key: str) -> str:
    message = f"{uri}&{sign_data}"
    return hmac.new(
        key=app_key.encode("utf-8"),
        msg=message.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


def calc_signature(sign_data: str, session_key: str) -> str:
    return hmac.new(
        key=session_key.encode("utf-8"),
        msg=sign_data.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


def virtual_out_trade_no(order: VipOrder) -> str:
    return order.id.replace("-", "")[:32]


def _product_snapshot(order: VipOrder) -> Dict[str, Any]:
    return json.loads(order.product_snapshot_json or "{}")


def _unit_price(order: VipOrder, snapshot: Dict[str, Any]) -> int:
    quantity = max(int(snapshot.get("quantity") or 1), 1)
    return int(snapshot.get("price_fen") or (order.amount_fen // quantity))


def _product_id(order: VipOrder) -> str:
    return _load_product_ids().get(order.product_code, order.product_code)


def _build_payload(
    *,
    order: VipOrder,
    offer_id: str,
    app_key: str,
    session_key: str,
    env: int,
) -> Dict[str, Any]:
    snapshot = _product_snapshot(order)
    quantity = max(int(snapshot.get("quantity") or 1), 1)
    sign_payload = {
        "offerId": offer_id,
        "buyQuantity": quantity,
        "env": env,
        "currencyType": "CNY",
        "productId": _product_id(order),
        "goodsPrice": _unit_price(order, snapshot),
        "outTradeNo": virtual_out_trade_no(order),
        "attach": order.id,
    }
    sign_data = _json_dumps(sign_payload)
    return {
        "signData": sign_data,
        "paySig": calc_pay_sig(
            REQUEST_VIRTUAL_PAYMENT_URI,
            sign_data,
            app_key,
        ),
        "signature": calc_signature(sign_data, session_key),
        "mode": VIRTUAL_PAYMENT_MODE,
    }


def real_virtual_payment_ready(user: Any) -> bool:
    return bool(
        os.getenv("WECHAT_VIRTUAL_PAY_OFFER_ID", "").strip()
        and _virtual_payment_app_key()
        and getattr(user, "wechat_session_key", None)
    )


def local_virtual_payment_ready() -> bool:
    return ENABLE_VIP_LOCAL_VIRTUAL_PAYMENT


def build_virtual_payment(
    *,
    order: VipOrder,
    user: Optional[Any],
    api_prefix: str = "/api/v1",
) -> Dict[str, Any]:
    session_key = getattr(user, "wechat_session_key", None)
    is_real = real_virtual_payment_ready(user)
    is_local = not is_real and local_virtual_payment_ready()

    if not is_real and not is_local:
        return {
            "provider": "wechat",
            "mode": "wechat_virtual_not_configured",
            "payload": None,
            "local_confirm_endpoint": None,
        }

    offer_id = os.getenv("WECHAT_VIRTUAL_PAY_OFFER_ID", "").strip()
    payment_env = _virtual_payment_env()
    app_key = _virtual_payment_app_key(payment_env)
    if is_local:
        offer_id = offer_id or LOCAL_OFFER_ID
        app_key = app_key or LOCAL_APP_KEY
        session_key = session_key or f"local-session-key-{order.user_id}"

    payload = _build_payload(
        order=order,
        offer_id=offer_id,
        app_key=app_key,
        session_key=session_key,
        env=payment_env,
    )
    local_confirm_endpoint = (
        f"{api_prefix}/vip/orders/{order.id}/virtual-pay/local-confirm"
        if local_virtual_payment_ready()
        else None
    )
    return {
        "provider": "wechat",
        "mode": "wechat_virtual" if is_real else "local_virtual_mock",
        "payload": payload,
        "local_confirm_endpoint": local_confirm_endpoint,
        "out_trade_no": virtual_out_trade_no(order),
    }
