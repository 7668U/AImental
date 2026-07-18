import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
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
from vip_virtual_payment import build_virtual_payment

from .auth import get_current_user_id


router = APIRouter(
    prefix="/vip",
    tags=["VIP - 会员与额度"],
)


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
