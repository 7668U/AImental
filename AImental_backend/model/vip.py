import uuid
from typing import List, Type

from peewee import (
    AutoField,
    CharField,
    IntegerField,
    Model,
    TextField,
)

from db import vip_db


def _uuid() -> str:
    return str(uuid.uuid4())


class VipMembership(Model):
    id = CharField(primary_key=True, max_length=36, default=_uuid)
    user_id = CharField(max_length=36, unique=True, index=True)
    plan_code = CharField(max_length=32)
    status = CharField(max_length=16, default="active", index=True)
    started_at = IntegerField()
    current_period_start = IntegerField()
    current_period_end = IntegerField()
    expires_at = IntegerField(index=True)
    created_at = IntegerField()
    updated_at = IntegerField()

    class Meta:
        database = vip_db
        table_name = "vip_memberships"


class VipQuotaBucket(Model):
    id = CharField(primary_key=True, max_length=36, default=_uuid)
    user_id = CharField(max_length=36, index=True)
    feature = CharField(max_length=32, index=True)
    source_type = CharField(max_length=16, index=True)
    source_ref = CharField(max_length=160, unique=True)
    total_amount = IntegerField()
    remaining_amount = IntegerField()
    valid_from = IntegerField(index=True)
    expires_at = IntegerField(index=True)
    status = CharField(max_length=16, default="active", index=True)
    created_at = IntegerField()
    updated_at = IntegerField()

    class Meta:
        database = vip_db
        table_name = "vip_quota_buckets"
        indexes = (
            (("user_id", "feature", "status", "expires_at"), False),
        )


class VipQuotaReservation(Model):
    id = CharField(primary_key=True, max_length=36, default=_uuid)
    request_id = CharField(max_length=96, unique=True, index=True)
    user_id = CharField(max_length=36, index=True)
    feature = CharField(max_length=32, index=True)
    amount = IntegerField(default=1)
    allocations_json = TextField()
    status = CharField(max_length=16, default="reserved", index=True)
    created_at = IntegerField()
    updated_at = IntegerField()

    class Meta:
        database = vip_db
        table_name = "vip_quota_reservations"


class VipQuotaLedger(Model):
    id = AutoField()
    user_id = CharField(max_length=36, index=True)
    feature = CharField(max_length=32, index=True)
    bucket_id = CharField(max_length=36, null=True, index=True)
    request_id = CharField(max_length=96, null=True, index=True)
    event_type = CharField(max_length=24, index=True)
    amount = IntegerField(default=0)
    balance_after = IntegerField(null=True)
    metadata_json = TextField(default="{}")
    created_at = IntegerField(index=True)

    class Meta:
        database = vip_db
        table_name = "vip_quota_ledger"
        indexes = (
            (("user_id", "created_at"), False),
        )


class VipOrder(Model):
    id = CharField(primary_key=True, max_length=36, default=_uuid)
    user_id = CharField(max_length=36, index=True)
    product_code = CharField(max_length=64, index=True)
    product_type = CharField(max_length=16, index=True)
    amount_fen = IntegerField()
    status = CharField(max_length=24, default="pending", index=True)
    product_snapshot_json = TextField()
    payment_provider = CharField(max_length=24, default="wechat")
    provider_transaction_id = CharField(max_length=96, null=True, unique=True)
    created_at = IntegerField(index=True)
    paid_at = IntegerField(null=True)
    fulfilled_at = IntegerField(null=True)
    updated_at = IntegerField()

    class Meta:
        database = vip_db
        table_name = "vip_orders"
        indexes = (
            (("user_id", "created_at"), False),
        )


VIP_MODELS: List[Type[Model]] = [
    VipMembership,
    VipQuotaBucket,
    VipQuotaReservation,
    VipQuotaLedger,
    VipOrder,
]
