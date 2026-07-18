import calendar
import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pytz

from db import vip_db
from model.vip import (
    VipMembership,
    VipOrder,
    VipQuotaBucket,
    VipQuotaLedger,
    VipQuotaReservation,
)
from vip_catalog import (
    ADDON_PRODUCTS,
    FEATURES,
    FREE_MONTHLY_QUOTAS,
    PLAN_PRODUCTS,
    get_plan_by_code,
    get_product,
)


BEIJING_TZ = pytz.timezone("Asia/Shanghai")


class VipError(Exception):
    code = "vip_error"

    def __init__(self, message: str, *, code: Optional[str] = None):
        super().__init__(message)
        if code:
            self.code = code


class VipQuotaExceeded(VipError):
    code = "quota_exhausted"


class VipDuplicateRequest(VipError):
    code = "duplicate_request"


class VipProductError(VipError):
    code = "invalid_product"


class VipOrderError(VipError):
    code = "order_error"


@dataclass
class ReservationResult:
    reservation_id: str
    request_id: str
    feature: str
    amount: int


def now_ts() -> int:
    return int(time.time())


def _beijing_datetime(timestamp: int) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=BEIJING_TZ)


def _to_timestamp(value: datetime) -> int:
    return int(value.timestamp())


def _free_period(timestamp: int) -> Dict[str, Any]:
    current = _beijing_datetime(timestamp)
    start = BEIJING_TZ.localize(datetime(current.year, current.month, 1))
    if current.month == 12:
        end = BEIJING_TZ.localize(datetime(current.year + 1, 1, 1))
    else:
        end = BEIJING_TZ.localize(datetime(current.year, current.month + 1, 1))
    return {
        "key": f"{current.year:04d}-{current.month:02d}",
        "start": _to_timestamp(start),
        "end": _to_timestamp(end),
    }


def add_months(timestamp: int, months: int = 1) -> int:
    current = _beijing_datetime(timestamp)
    total_month = current.month - 1 + months
    year = current.year + total_month // 12
    month = total_month % 12 + 1
    day = min(current.day, calendar.monthrange(year, month)[1])
    target = current.replace(year=year, month=month, day=day)
    return _to_timestamp(target)


class VipService:
    def __init__(self, database=vip_db):
        self.db = database

    def _ledger(
        self,
        *,
        user_id: str,
        feature: str,
        event_type: str,
        amount: int,
        bucket: Optional[VipQuotaBucket] = None,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[int] = None,
    ) -> VipQuotaLedger:
        return VipQuotaLedger.create(
            user_id=user_id,
            feature=feature,
            bucket_id=bucket.id if bucket else None,
            request_id=request_id,
            event_type=event_type,
            amount=amount,
            balance_after=bucket.remaining_amount if bucket else None,
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
            created_at=timestamp or now_ts(),
        )

    def _grant_bucket(
        self,
        *,
        user_id: str,
        feature: str,
        source_type: str,
        source_ref: str,
        amount: int,
        valid_from: int,
        expires_at: int,
        timestamp: Optional[int] = None,
    ) -> VipQuotaBucket:
        timestamp = timestamp or now_ts()
        bucket, created = VipQuotaBucket.get_or_create(
            source_ref=source_ref,
            defaults={
                "user_id": user_id,
                "feature": feature,
                "source_type": source_type,
                "total_amount": amount,
                "remaining_amount": amount,
                "valid_from": valid_from,
                "expires_at": expires_at,
                "status": "active",
                "created_at": timestamp,
                "updated_at": timestamp,
            },
        )
        if created:
            self._ledger(
                user_id=user_id,
                feature=feature,
                event_type="grant",
                amount=amount,
                bucket=bucket,
                metadata={"source_type": source_type, "source_ref": source_ref},
                timestamp=timestamp,
            )
        elif amount > bucket.total_amount:
            increase = amount - bucket.total_amount
            bucket.total_amount = amount
            bucket.remaining_amount += increase
            bucket.status = "active"
            bucket.updated_at = timestamp
            bucket.save(
                only=[
                    VipQuotaBucket.total_amount,
                    VipQuotaBucket.remaining_amount,
                    VipQuotaBucket.status,
                    VipQuotaBucket.updated_at,
                ]
            )
            self._ledger(
                user_id=user_id,
                feature=feature,
                event_type="grant",
                amount=increase,
                bucket=bucket,
                metadata={
                    "source_type": source_type,
                    "source_ref": source_ref,
                    "reason": "quota_increase",
                },
                timestamp=timestamp,
            )
        return bucket

    def ensure_free_buckets(self, user_id: str, timestamp: Optional[int] = None) -> None:
        timestamp = timestamp or now_ts()
        period = _free_period(timestamp)
        with self.db.atomic():
            for feature, amount in FREE_MONTHLY_QUOTAS.items():
                self._grant_bucket(
                    user_id=user_id,
                    feature=feature,
                    source_type="free",
                    source_ref=f"free:{user_id}:{period['key']}:{feature}",
                    amount=amount,
                    valid_from=period["start"],
                    expires_at=period["end"],
                    timestamp=timestamp,
                )

    def _expire_buckets(self, user_id: str, timestamp: int) -> None:
        expired = list(
            VipQuotaBucket.select().where(
                (VipQuotaBucket.user_id == user_id)
                & (VipQuotaBucket.status == "active")
                & (VipQuotaBucket.expires_at <= timestamp)
            )
        )
        for bucket in expired:
            bucket.status = "expired"
            bucket.updated_at = timestamp
            bucket.save(only=[VipQuotaBucket.status, VipQuotaBucket.updated_at])
            self._ledger(
                user_id=user_id,
                feature=bucket.feature,
                event_type="expire",
                amount=-bucket.remaining_amount,
                bucket=bucket,
                metadata={"source_type": bucket.source_type},
                timestamp=timestamp,
            )

    def _grant_membership_period(
        self,
        membership: VipMembership,
        period_start: int,
        period_end: int,
        timestamp: int,
    ) -> None:
        plan = get_plan_by_code(membership.plan_code)
        if not plan:
            raise VipProductError("会员套餐配置不存在。")
        for feature, amount in plan["quotas"].items():
            self._grant_bucket(
                user_id=membership.user_id,
                feature=feature,
                source_type="membership",
                source_ref=(
                    f"membership:{membership.id}:{period_start}:{feature}"
                ),
                amount=amount,
                valid_from=period_start,
                expires_at=period_end,
                timestamp=timestamp,
            )

    def ensure_membership_cycle(
        self,
        user_id: str,
        timestamp: Optional[int] = None,
    ) -> Optional[VipMembership]:
        timestamp = timestamp or now_ts()
        membership = VipMembership.get_or_none(VipMembership.user_id == user_id)
        if not membership:
            return None
        if membership.expires_at <= timestamp:
            if membership.status != "expired":
                membership.status = "expired"
                membership.updated_at = timestamp
                membership.save(
                    only=[VipMembership.status, VipMembership.updated_at]
                )
            return None
        if membership.status != "active":
            membership.status = "active"
        changed = False
        while (
            membership.current_period_end <= timestamp
            and membership.current_period_end < membership.expires_at
        ):
            next_start = membership.current_period_end
            next_end = min(add_months(next_start), membership.expires_at)
            membership.current_period_start = next_start
            membership.current_period_end = next_end
            self._grant_membership_period(
                membership,
                next_start,
                next_end,
                timestamp,
            )
            changed = True
        if changed:
            membership.updated_at = timestamp
        self._grant_membership_period(
            membership,
            membership.current_period_start,
            membership.current_period_end,
            timestamp,
        )
        membership.save()
        return membership

    def ensure_entitlements(
        self,
        user_id: str,
        timestamp: Optional[int] = None,
    ) -> Optional[VipMembership]:
        timestamp = timestamp or now_ts()
        with self.db.atomic():
            self._expire_buckets(user_id, timestamp)
            self.ensure_free_buckets(user_id, timestamp)
            return self.ensure_membership_cycle(user_id, timestamp)

    def reserve(
        self,
        *,
        user_id: str,
        feature: str,
        request_id: str,
        amount: int = 1,
        timestamp: Optional[int] = None,
    ) -> ReservationResult:
        if feature not in FEATURES:
            raise VipProductError("未知的权益功能。")
        if amount <= 0:
            raise VipError("额度数量必须大于 0。")
        timestamp = timestamp or now_ts()
        self.ensure_entitlements(user_id, timestamp)
        with self.db.atomic():
            existing = VipQuotaReservation.get_or_none(
                VipQuotaReservation.request_id == request_id
            )
            if existing:
                raise VipDuplicateRequest(
                    "该请求已经处理或正在处理中。"
                )
            buckets = list(
                VipQuotaBucket.select()
                .where(
                    (VipQuotaBucket.user_id == user_id)
                    & (VipQuotaBucket.feature == feature)
                    & (VipQuotaBucket.status == "active")
                    & (VipQuotaBucket.valid_from <= timestamp)
                    & (VipQuotaBucket.expires_at > timestamp)
                    & (VipQuotaBucket.remaining_amount > 0)
                )
                .order_by(
                    VipQuotaBucket.expires_at.asc(),
                    VipQuotaBucket.created_at.asc(),
                )
            )
            if sum(bucket.remaining_amount for bucket in buckets) < amount:
                raise VipQuotaExceeded("当前功能额度已用完。")
            remaining = amount
            allocations: List[Dict[str, Any]] = []
            for bucket in buckets:
                if remaining <= 0:
                    break
                allocated = min(bucket.remaining_amount, remaining)
                bucket.remaining_amount -= allocated
                bucket.updated_at = timestamp
                if bucket.remaining_amount == 0:
                    bucket.status = "exhausted"
                bucket.save()
                allocations.append(
                    {
                        "bucket_id": bucket.id,
                        "amount": allocated,
                    }
                )
                self._ledger(
                    user_id=user_id,
                    feature=feature,
                    event_type="reserve",
                    amount=-allocated,
                    bucket=bucket,
                    request_id=request_id,
                    timestamp=timestamp,
                )
                remaining -= allocated
            reservation = VipQuotaReservation.create(
                request_id=request_id,
                user_id=user_id,
                feature=feature,
                amount=amount,
                allocations_json=json.dumps(allocations),
                status="reserved",
                created_at=timestamp,
                updated_at=timestamp,
            )
            return ReservationResult(
                reservation_id=reservation.id,
                request_id=request_id,
                feature=feature,
                amount=amount,
            )

    def confirm(
        self,
        reservation_id: str,
        timestamp: Optional[int] = None,
    ) -> None:
        timestamp = timestamp or now_ts()
        with self.db.atomic():
            reservation = VipQuotaReservation.get_by_id(reservation_id)
            if reservation.status == "confirmed":
                return
            if reservation.status != "reserved":
                raise VipError("该额度预占无法确认。")
            reservation.status = "confirmed"
            reservation.updated_at = timestamp
            reservation.save(
                only=[
                    VipQuotaReservation.status,
                    VipQuotaReservation.updated_at,
                ]
            )
            self._ledger(
                user_id=reservation.user_id,
                feature=reservation.feature,
                event_type="confirm",
                amount=0,
                request_id=reservation.request_id,
                metadata={"reservation_id": reservation.id},
                timestamp=timestamp,
            )

    def release(
        self,
        reservation_id: str,
        timestamp: Optional[int] = None,
    ) -> None:
        timestamp = timestamp or now_ts()
        with self.db.atomic():
            reservation = VipQuotaReservation.get_by_id(reservation_id)
            if reservation.status == "released":
                return
            if reservation.status != "reserved":
                return
            allocations = json.loads(reservation.allocations_json)
            for allocation in allocations:
                bucket = VipQuotaBucket.get_by_id(allocation["bucket_id"])
                amount = int(allocation["amount"])
                bucket.remaining_amount += amount
                bucket.status = "active"
                bucket.updated_at = timestamp
                bucket.save()
                self._ledger(
                    user_id=reservation.user_id,
                    feature=reservation.feature,
                    event_type="release",
                    amount=amount,
                    bucket=bucket,
                    request_id=reservation.request_id,
                    timestamp=timestamp,
                )
            reservation.status = "released"
            reservation.updated_at = timestamp
            reservation.save(
                only=[
                    VipQuotaReservation.status,
                    VipQuotaReservation.updated_at,
                ]
            )

    def _membership_payload(
        self,
        membership: Optional[VipMembership],
    ) -> Optional[Dict[str, Any]]:
        if not membership:
            return None
        plan = get_plan_by_code(membership.plan_code)
        return {
            "id": membership.id,
            "plan_code": membership.plan_code,
            "plan_name": plan["name"] if plan else membership.plan_code,
            "status": membership.status,
            "started_at": membership.started_at,
            "current_period_start": membership.current_period_start,
            "current_period_end": membership.current_period_end,
            "expires_at": membership.expires_at,
        }

    def get_summary(
        self,
        user_id: str,
        timestamp: Optional[int] = None,
    ) -> Dict[str, Any]:
        timestamp = timestamp or now_ts()
        membership = self.ensure_entitlements(user_id, timestamp)
        buckets = list(
            VipQuotaBucket.select()
            .where(
                (VipQuotaBucket.user_id == user_id)
                & (VipQuotaBucket.status.in_(["active", "exhausted"]))
                & (VipQuotaBucket.valid_from <= timestamp)
                & (VipQuotaBucket.expires_at > timestamp)
            )
            .order_by(
                VipQuotaBucket.feature.asc(),
                VipQuotaBucket.expires_at.asc(),
            )
        )
        entitlements: Dict[str, Dict[str, Any]] = {}
        for feature, metadata in FEATURES.items():
            sources = [
                {
                    "bucket_id": bucket.id,
                    "source_type": bucket.source_type,
                    "source_ref": bucket.source_ref,
                    "total": bucket.total_amount,
                    "remaining": bucket.remaining_amount,
                    "valid_from": bucket.valid_from,
                    "expires_at": bucket.expires_at,
                }
                for bucket in buckets
                if bucket.feature == feature
            ]
            entitlements[feature] = {
                "feature": feature,
                "name": metadata["name"],
                "unit": metadata["unit"],
                "total": sum(item["total"] for item in sources),
                "remaining": sum(item["remaining"] for item in sources),
                "sources": sources,
            }
        return {
            "user_type": "member" if membership else "free",
            "membership": self._membership_payload(membership),
            "entitlements": entitlements,
            "server_time": timestamp,
        }

    def cancel_membership_for_testing(
        self,
        user_id: str,
        timestamp: Optional[int] = None,
    ) -> Dict[str, Any]:
        timestamp = timestamp or now_ts()
        with self.db.atomic():
            membership = VipMembership.get_or_none(VipMembership.user_id == user_id)
            if membership:
                membership.status = "expired"
                membership.expires_at = timestamp
                membership.current_period_end = min(
                    membership.current_period_end,
                    timestamp,
                )
                membership.updated_at = timestamp
                membership.save(
                    only=[
                        VipMembership.status,
                        VipMembership.expires_at,
                        VipMembership.current_period_end,
                        VipMembership.updated_at,
                    ]
                )

            member_buckets = list(
                VipQuotaBucket.select().where(
                    (VipQuotaBucket.user_id == user_id)
                    & (VipQuotaBucket.source_type == "membership")
                    & (VipQuotaBucket.status.in_(["active", "exhausted"]))
                )
            )
            for bucket in member_buckets:
                remaining = bucket.remaining_amount
                bucket.remaining_amount = 0
                bucket.status = "expired"
                bucket.expires_at = min(bucket.expires_at, timestamp)
                bucket.updated_at = timestamp
                bucket.save(
                    only=[
                        VipQuotaBucket.remaining_amount,
                        VipQuotaBucket.status,
                        VipQuotaBucket.expires_at,
                        VipQuotaBucket.updated_at,
                    ]
                )
                if remaining:
                    self._ledger(
                        user_id=user_id,
                        feature=bucket.feature,
                        event_type="cancel",
                        amount=-remaining,
                        bucket=bucket,
                        metadata={"source_type": "membership", "reason": "test_cancel"},
                        timestamp=timestamp,
                    )

            self.ensure_free_buckets(user_id, timestamp)

        return self.get_summary(user_id, timestamp)

    def create_order(
        self,
        user_id: str,
        product_code: str,
        quantity: int = 1,
        timestamp: Optional[int] = None,
    ) -> VipOrder:
        timestamp = timestamp or now_ts()
        product = get_product(product_code)
        if not product:
            raise VipProductError("商品不存在。")
        quantity = int(quantity or 1)
        if quantity < 1 or quantity > 99:
            raise VipProductError("购买数量必须在 1-99 之间。")
        membership = self.ensure_membership_cycle(user_id, timestamp)
        if product["product_type"] == "membership" and quantity != 1:
            raise VipProductError("会员套餐暂不支持一次购买多份。")
        if product["product_type"] == "membership" and membership:
            if membership.plan_code != product["plan_code"]:
                raise VipProductError(
                    "会员升级与降级规则尚未开放，请先购买当前等级续费或等待当前会员到期。",
                    code="membership_change_not_supported",
                )
        if product["product_type"] == "addon":
            cutoff = timestamp - 30 * 24 * 60 * 60
            recent_count = (
                VipOrder.select()
                .where(
                    (VipOrder.user_id == user_id)
                    & (VipOrder.product_code == product_code)
                    & (VipOrder.status == "fulfilled")
                    & (VipOrder.fulfilled_at >= cutoff)
                )
                .count()
            )
            if recent_count >= 5:
                raise VipProductError(
                    "该功能近 30 天购买次数已达上限。",
                    code="addon_purchase_limit",
                )
        snapshot = {
            **product,
            "price_fen": product["price_fen"],
            "quantity": quantity,
        }
        if product["product_type"] == "addon":
            snapshot["unit_amount"] = int(product["amount"])
            snapshot["amount"] = int(product["amount"]) * quantity
        return VipOrder.create(
            user_id=user_id,
            product_code=product_code,
            product_type=product["product_type"],
            amount_fen=product["price_fen"] * quantity,
            status="pending",
            product_snapshot_json=json.dumps(snapshot, ensure_ascii=False),
            created_at=timestamp,
            updated_at=timestamp,
        )

    def _activate_membership(
        self,
        *,
        user_id: str,
        product: Dict[str, Any],
        timestamp: int,
    ) -> VipMembership:
        membership = VipMembership.get_or_none(VipMembership.user_id == user_id)
        if membership and membership.expires_at > timestamp:
            if membership.plan_code != product["plan_code"]:
                raise VipOrderError(
                    "当前会员等级与订单等级不一致，无法自动发放。"
                )
            membership.expires_at = add_months(membership.expires_at)
            membership.updated_at = timestamp
            membership.status = "active"
            membership.save()
            return membership
        period_end = add_months(timestamp)
        if membership:
            membership.plan_code = product["plan_code"]
            membership.status = "active"
            membership.started_at = timestamp
            membership.current_period_start = timestamp
            membership.current_period_end = period_end
            membership.expires_at = period_end
            membership.updated_at = timestamp
            membership.save()
        else:
            membership = VipMembership.create(
                user_id=user_id,
                plan_code=product["plan_code"],
                status="active",
                started_at=timestamp,
                current_period_start=timestamp,
                current_period_end=period_end,
                expires_at=period_end,
                created_at=timestamp,
                updated_at=timestamp,
            )
        self._grant_membership_period(
            membership,
            timestamp,
            period_end,
            timestamp,
        )
        return membership

    def _fulfill_order(self, order: VipOrder, timestamp: int) -> None:
        product = json.loads(order.product_snapshot_json)
        if order.product_type == "membership":
            self._activate_membership(
                user_id=order.user_id,
                product=product,
                timestamp=timestamp,
            )
        elif order.product_type == "addon":
            feature = product["feature"]
            amount = int(product["amount"])
            expires_at = timestamp + int(product["valid_days"]) * 24 * 60 * 60
            self._grant_bucket(
                user_id=order.user_id,
                feature=feature,
                source_type="addon",
                source_ref=f"addon:{order.id}:{feature}",
                amount=amount,
                valid_from=timestamp,
                expires_at=expires_at,
                timestamp=timestamp,
            )
        else:
            raise VipOrderError("不支持的订单商品类型。")

    def mark_order_paid(
        self,
        *,
        order_id: str,
        user_id: str,
        transaction_id: str,
        timestamp: Optional[int] = None,
    ) -> VipOrder:
        timestamp = timestamp or now_ts()
        with self.db.atomic():
            order = VipOrder.get_or_none(
                (VipOrder.id == order_id) & (VipOrder.user_id == user_id)
            )
            if not order:
                raise VipOrderError("订单不存在。")
            if order.status == "fulfilled":
                return order
            if order.status not in {
                "pending",
                "closed",
                "paid",
                "fulfillment_pending",
            }:
                raise VipOrderError("当前订单状态无法支付。")
            if order.status in {"pending", "closed"}:
                order.status = "paid"
                order.paid_at = timestamp
                order.provider_transaction_id = transaction_id
                order.updated_at = timestamp
                order.save()
            try:
                self._fulfill_order(order, timestamp)
            except Exception:
                order.status = "fulfillment_pending"
                order.updated_at = timestamp
                order.save()
                raise
            order.status = "fulfilled"
            order.fulfilled_at = timestamp
            order.updated_at = timestamp
            order.save()
            return order

    def close_pending_order(
        self,
        *,
        order_id: str,
        user_id: str,
        timestamp: Optional[int] = None,
    ) -> VipOrder:
        timestamp = timestamp or now_ts()
        with self.db.atomic():
            order = VipOrder.get_or_none(
                (VipOrder.id == order_id) & (VipOrder.user_id == user_id)
            )
            if not order:
                raise VipOrderError("订单不存在。")
            if order.status != "pending":
                return order
            order.status = "closed"
            order.updated_at = timestamp
            order.save(only=[VipOrder.status, VipOrder.updated_at])
            return order

    def expire_pending_orders(
        self,
        user_id: str,
        *,
        older_than_seconds: int = 30 * 60,
        timestamp: Optional[int] = None,
    ) -> int:
        timestamp = timestamp or now_ts()
        cutoff = timestamp - max(int(older_than_seconds), 60)
        return (
            VipOrder.update(
                status="closed",
                updated_at=timestamp,
            )
            .where(
                (VipOrder.user_id == user_id)
                & (VipOrder.status == "pending")
                & (VipOrder.created_at <= cutoff)
            )
            .execute()
        )

    def get_order(self, user_id: str, order_id: str) -> VipOrder:
        order = VipOrder.get_or_none(
            (VipOrder.id == order_id) & (VipOrder.user_id == user_id)
        )
        if not order:
            raise VipOrderError("订单不存在。")
        return order

    def list_orders(self, user_id: str, limit: int = 50) -> List[VipOrder]:
        return list(
            VipOrder.select()
            .where(VipOrder.user_id == user_id)
            .order_by(VipOrder.created_at.desc())
            .limit(limit)
        )

    def list_purchase_orders(
        self,
        user_id: str,
        limit: int = 50,
    ) -> List[VipOrder]:
        return list(
            VipOrder.select()
            .where(
                (VipOrder.user_id == user_id)
                & (
                    VipOrder.status.in_(
                        ["paid", "fulfillment_pending", "fulfilled", "refunded"]
                    )
                )
            )
            .order_by(VipOrder.created_at.desc())
            .limit(limit)
        )

    def list_ledger(
        self,
        user_id: str,
        limit: int = 100,
    ) -> List[VipQuotaLedger]:
        return list(
            VipQuotaLedger.select()
            .where(VipQuotaLedger.user_id == user_id)
            .order_by(VipQuotaLedger.created_at.desc(), VipQuotaLedger.id.desc())
            .limit(limit)
        )


vip_service = VipService(vip_db)
