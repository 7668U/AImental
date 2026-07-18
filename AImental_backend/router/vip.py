import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field

from feature_flags import (
    ENABLE_VIP_TEST_TOOLS,
    ENABLE_VIP_LOCAL_VIRTUAL_PAYMENT,
    ENABLE_VIP_MOCK_PAYMENT,
)
from model.user import user_table
from model.vip import VipOrder
from vip_catalog import public_catalog
from vip_service import (
    VipDuplicateRequest,
    VipError,
    VipOrderError,
    VipProductError,
    VipQuotaExceeded,
    vip_service,
)
from vip_payment_sync import (
    VipPaymentSyncError,
    callback_failure_response,
    callback_success_response,
    find_order_for_callback,
    parse_callback_body,
    reconcile_order,
    verify_message_signature,
)
from vip_virtual_payment import (
    _product_id,
    _unit_price,
    _virtual_payment_env,
    build_virtual_payment,
    real_virtual_payment_ready,
    virtual_out_trade_no,
)

from .auth import get_current_user_id


router = APIRouter(
    prefix="/vip",
    tags=["VIP - 会员与额度"],
)
logger = logging.getLogger(__name__)
PENDING_RECONCILE_WINDOW_SECONDS = 7 * 24 * 60 * 60


class CreateOrderRequest(BaseModel):
    product_code: str = Field(..., min_length=1, max_length=64)
    quantity: int = Field(1, ge=1, le=99)


class OrderResponse(BaseModel):
    id: str
    product_code: str
    product_type: str
    amount_fen: int
    status: str
    product_snapshot: Dict[str, Any]
    payment_provider: str
    provider_transaction_id: Optional[str] = None
    created_at: int
    paid_at: Optional[int] = None
    fulfilled_at: Optional[int] = None


class CreateOrderResponse(BaseModel):
    order: OrderResponse
    payment: Dict[str, Any]


class ReconcileOrderResponse(BaseModel):
    order: OrderResponse
    paid: bool
    provider_status: int


class RecordsResponse(BaseModel):
    quota_events: List[Dict[str, Any]]
    orders: List[OrderResponse]


def order_payload(order: VipOrder) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        product_code=order.product_code,
        product_type=order.product_type,
        amount_fen=order.amount_fen,
        status=order.status,
        product_snapshot=json.loads(order.product_snapshot_json),
        payment_provider=order.payment_provider,
        provider_transaction_id=order.provider_transaction_id,
        created_at=order.created_at,
        paid_at=order.paid_at,
        fulfilled_at=order.fulfilled_at,
    )


def reconcile_recent_pending_orders(user_id: str) -> None:
    user = user_table.get_user_by_id(user_id)
    if not user or not real_virtual_payment_ready(user):
        return
    cutoff = int(time.time()) - PENDING_RECONCILE_WINDOW_SECONDS
    pending_orders = (
        VipOrder.select()
        .where(
            (VipOrder.user_id == user_id)
            & (VipOrder.status.in_(["pending", "paid", "fulfillment_pending"]))
            & (VipOrder.created_at >= cutoff)
        )
        .order_by(VipOrder.created_at.desc())
        .limit(5)
    )
    for order in pending_orders:
        try:
            reconcile_order(order, user, vip_service)
        except (VipError, VipPaymentSyncError):
            logger.warning(
                "Could not reconcile pending VIP order %s while loading state.",
                order.id,
                exc_info=True,
            )


def vip_http_error(exc: VipError) -> HTTPException:
    if isinstance(exc, VipQuotaExceeded):
        http_status = status.HTTP_402_PAYMENT_REQUIRED
    elif isinstance(exc, VipDuplicateRequest):
        http_status = status.HTTP_409_CONFLICT
    elif isinstance(exc, VipProductError):
        http_status = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, VipOrderError):
        http_status = status.HTTP_409_CONFLICT
    else:
        http_status = status.HTTP_400_BAD_REQUEST
    return HTTPException(
        status_code=http_status,
        detail={
            "code": exc.code,
            "message": str(exc),
        },
    )


@router.get("/catalog", response_model=Dict[str, Any])
def get_vip_catalog():
    catalog = public_catalog()
    catalog["mock_payment_available"] = ENABLE_VIP_MOCK_PAYMENT
    catalog["local_virtual_payment_available"] = ENABLE_VIP_LOCAL_VIRTUAL_PAYMENT
    catalog["test_tools_available"] = ENABLE_VIP_TEST_TOOLS
    return catalog


@router.get("/me", response_model=Dict[str, Any])
def get_my_vip_state(
    current_user_id: str = Depends(get_current_user_id),
):
    reconcile_recent_pending_orders(current_user_id)
    summary = vip_service.get_summary(current_user_id)
    summary["test_tools_available"] = ENABLE_VIP_TEST_TOOLS
    return summary


@router.post("/me/test-cancel-membership", response_model=Dict[str, Any])
def test_cancel_my_vip_membership(
    current_user_id: str = Depends(get_current_user_id),
):
    if not ENABLE_VIP_TEST_TOOLS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "vip_test_tools_disabled",
                "message": "VIP test tools are disabled.",
            },
        )
    return vip_service.cancel_membership_for_testing(current_user_id)


@router.post(
    "/orders",
    response_model=CreateOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_vip_order(
    request_data: CreateOrderRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    try:
        order = vip_service.create_order(
            current_user_id,
            request_data.product_code,
            quantity=request_data.quantity,
        )
    except VipError as exc:
        raise vip_http_error(exc) from exc
    serialized = order_payload(order)
    user = user_table.get_user_by_id(current_user_id)
    payment = build_virtual_payment(order=order, user=user)
    if ENABLE_VIP_MOCK_PAYMENT:
        payment["legacy_mock_pay_endpoint"] = f"/api/v1/vip/orders/{order.id}/mock-pay"
    return CreateOrderResponse(order=serialized, payment=payment)


@router.post(
    "/orders/{order_id}/reconcile",
    response_model=ReconcileOrderResponse,
)
def reconcile_vip_order(
    order_id: str,
    current_user_id: str = Depends(get_current_user_id),
):
    try:
        order = vip_service.get_order(current_user_id, order_id)
        if order.status == "fulfilled":
            return ReconcileOrderResponse(
                order=order_payload(order),
                paid=True,
                provider_status=4,
            )
        user = user_table.get_user_by_id(current_user_id)
        if not user:
            raise VipOrderError("User does not exist.")
        reconciled_order, paid, provider_status = reconcile_order(
            order,
            user,
            vip_service,
        )
    except VipError as exc:
        raise vip_http_error(exc) from exc
    except VipPaymentSyncError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": exc.code,
                "message": str(exc),
            },
        ) from exc
    return ReconcileOrderResponse(
        order=order_payload(reconciled_order),
        paid=paid,
        provider_status=provider_status,
    )


@router.get("/wechat/callback", response_class=PlainTextResponse)
def verify_wechat_callback(request: Request):
    params = request.query_params
    if not verify_message_signature(
        signature=params.get("signature", ""),
        timestamp=params.get("timestamp", ""),
        nonce=params.get("nonce", ""),
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid WeChat callback signature.",
        )
    return params.get("echostr", "")


@router.post("/wechat/callback")
async def receive_wechat_callback(request: Request):
    params = request.query_params
    if not verify_message_signature(
        signature=params.get("signature", ""),
        timestamp=params.get("timestamp", ""),
        nonce=params.get("nonce", ""),
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid WeChat callback signature.",
        )

    fmt = "json"
    try:
        payload, fmt = parse_callback_body(await request.body())
        if payload.get("Event") != "xpay_goods_deliver_notify":
            raise VipPaymentSyncError(
                "Unsupported WeChat callback event.",
                code="wechat_callback_event_unsupported",
            )

        goods_info = payload.get("GoodsInfo") or {}
        payment_info = payload.get("WeChatPayInfo") or {}
        order = find_order_for_callback(
            attach=str(goods_info.get("Attach") or ""),
            out_trade_no=str(payload.get("OutTradeNo") or ""),
        )
        if not order:
            raise VipPaymentSyncError(
                "The callback order does not exist.",
                code="wechat_callback_order_missing",
            )

        expected_out_trade_no = virtual_out_trade_no(order)
        if str(payload.get("OutTradeNo") or "") != expected_out_trade_no:
            raise VipPaymentSyncError(
                "The callback order number does not match.",
                code="wechat_callback_order_mismatch",
            )
        if int(payload.get("Env") or 0) != _virtual_payment_env():
            raise VipPaymentSyncError(
                "The callback payment environment does not match.",
                code="wechat_callback_environment_mismatch",
            )

        user = user_table.get_user_by_id(order.user_id)
        callback_openid = str(payload.get("OpenId") or "")
        if callback_openid and (not user or callback_openid != user.openid):
            raise VipPaymentSyncError(
                "The callback user does not match the order.",
                code="wechat_callback_user_mismatch",
            )

        snapshot = json.loads(order.product_snapshot_json or "{}")
        expected_quantity = max(int(snapshot.get("quantity") or 1), 1)
        callback_quantity = int(goods_info.get("Quantity") or 0)
        if callback_quantity and callback_quantity != expected_quantity:
            raise VipPaymentSyncError(
                "The callback quantity does not match the order.",
                code="wechat_callback_quantity_mismatch",
            )
        callback_product_id = str(goods_info.get("ProductId") or "")
        if callback_product_id and callback_product_id != _product_id(order):
            raise VipPaymentSyncError(
                "The callback product does not match the order.",
                code="wechat_callback_product_mismatch",
            )
        expected_unit_price = _unit_price(order, snapshot)
        callback_orig_price = int(goods_info.get("OrigPrice") or 0)
        if callback_orig_price and callback_orig_price not in {
            expected_unit_price,
            order.amount_fen,
        }:
            raise VipPaymentSyncError(
                "The callback amount does not match the order.",
                code="wechat_callback_amount_mismatch",
            )

        transaction_id = (
            payment_info.get("TransactionId")
            or payment_info.get("MchOrderNo")
            or f"wechat-{expected_out_trade_no}"
        )
        paid_at = int(payment_info.get("PaidTime") or 0) or None
        vip_service.mark_order_paid(
            order_id=order.id,
            user_id=order.user_id,
            transaction_id=str(transaction_id),
            timestamp=paid_at,
        )
        body, content_type = callback_success_response(fmt)
        return Response(content=body, media_type=content_type)
    except (VipError, VipPaymentSyncError, ValueError, TypeError) as exc:
        logger.exception("WeChat virtual payment callback failed")
        body, content_type = callback_failure_response(str(exc), fmt)
        return Response(
            content=body,
            media_type=content_type,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/orders", response_model=List[OrderResponse])
def list_my_vip_orders(
    limit: int = 50,
    current_user_id: str = Depends(get_current_user_id),
):
    limit = min(max(limit, 1), 100)
    return [
        order_payload(order)
        for order in vip_service.list_orders(current_user_id, limit=limit)
    ]


@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_vip_order(
    order_id: str,
    current_user_id: str = Depends(get_current_user_id),
):
    try:
        order = vip_service.get_order(current_user_id, order_id)
    except VipError as exc:
        raise vip_http_error(exc) from exc
    return order_payload(order)


@router.post("/orders/{order_id}/mock-pay", response_model=OrderResponse)
def mock_pay_vip_order(
    order_id: str,
    current_user_id: str = Depends(get_current_user_id),
):
    if not ENABLE_VIP_MOCK_PAYMENT:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "mock_payment_disabled",
                "message": "模拟支付未开启。",
            },
        )
    try:
        order = vip_service.mark_order_paid(
            order_id=order_id,
            user_id=current_user_id,
            transaction_id=f"mock-{uuid.uuid4()}",
        )
    except VipError as exc:
        raise vip_http_error(exc) from exc
    return order_payload(order)


@router.post(
    "/orders/{order_id}/virtual-pay/local-confirm",
    response_model=OrderResponse,
)
def local_confirm_virtual_payment(
    order_id: str,
    current_user_id: str = Depends(get_current_user_id),
):
    if not ENABLE_VIP_LOCAL_VIRTUAL_PAYMENT:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "local_virtual_payment_disabled",
                "message": "Local virtual payment confirmation is disabled.",
            },
        )
    try:
        order = vip_service.mark_order_paid(
            order_id=order_id,
            user_id=current_user_id,
            transaction_id=f"local-virtual-{uuid.uuid4()}",
        )
    except VipError as exc:
        raise vip_http_error(exc) from exc
    return order_payload(order)


@router.get("/records", response_model=RecordsResponse)
def get_vip_records(
    limit: int = 100,
    current_user_id: str = Depends(get_current_user_id),
):
    limit = min(max(limit, 1), 200)
    ledger = vip_service.list_ledger(current_user_id, limit=limit)
    orders = vip_service.list_orders(current_user_id, limit=min(limit, 100))
    return RecordsResponse(
        quota_events=[
            {
                "id": item.id,
                "feature": item.feature,
                "bucket_id": item.bucket_id,
                "request_id": item.request_id,
                "event_type": item.event_type,
                "amount": item.amount,
                "balance_after": item.balance_after,
                "metadata": json.loads(item.metadata_json or "{}"),
                "created_at": item.created_at,
            }
            for item in ledger
        ],
        orders=[order_payload(order) for order in orders],
    )
