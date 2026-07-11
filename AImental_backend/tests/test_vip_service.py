import os
import tempfile
import unittest

from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

from db import vip_db
from model.vip import (
    VIP_MODELS,
    VipMembership,
    VipOrder,
    VipQuotaBucket,
    VipQuotaLedger,
    VipQuotaReservation,
)
from vip_catalog import (
    FEATURE_COMMUNITY,
    FEATURE_TREE_HOLE,
)
from vip_service import VipQuotaExceeded, VipService, add_months
from vip_access import validate_ai_input
from router import vip as vip_router_module


TEST_NOW = 1783780800  # 2026-07-11 20:00:00 Asia/Shanghai


class VipServiceTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not vip_db.is_closed():
            vip_db.close()
        temp_file = tempfile.NamedTemporaryFile(
            prefix="vip-test-",
            suffix=".db",
            delete=False,
        )
        temp_file.close()
        cls.temp_db_path = temp_file.name
        vip_db.init(
            cls.temp_db_path,
            pragmas={
                "foreign_keys": 1,
                "journal_mode": "wal",
            },
        )
        vip_db.connect()
        vip_db.create_tables(VIP_MODELS)
        cls.service = VipService(vip_db)

    @classmethod
    def tearDownClass(cls):
        vip_db.drop_tables(VIP_MODELS)
        vip_db.close()
        for suffix in ("", "-wal", "-shm"):
            path = cls.temp_db_path + suffix
            if os.path.exists(path):
                os.remove(path)

    def setUp(self):
        for model in (
            VipQuotaLedger,
            VipQuotaReservation,
            VipQuotaBucket,
            VipOrder,
            VipMembership,
        ):
            model.delete().execute()

    def test_free_monthly_quotas_are_created(self):
        summary = self.service.get_summary("free-user", timestamp=TEST_NOW)

        self.assertEqual(summary["user_type"], "free")
        self.assertEqual(
            summary["entitlements"][FEATURE_TREE_HOLE]["remaining"],
            30,
        )
        self.assertEqual(
            summary["entitlements"][FEATURE_COMMUNITY]["remaining"],
            30,
        )

    def test_reservation_release_and_confirm(self):
        reservation = self.service.reserve(
            user_id="quota-user",
            feature=FEATURE_TREE_HOLE,
            request_id="tree-request-1",
            timestamp=TEST_NOW,
        )
        summary = self.service.get_summary("quota-user", timestamp=TEST_NOW)
        self.assertEqual(
            summary["entitlements"][FEATURE_TREE_HOLE]["remaining"],
            29,
        )

    def test_quota_exhaustion_and_input_limit(self):
        for index in range(30):
            reservation = self.service.reserve(
                user_id="exhausted-user",
                feature=FEATURE_TREE_HOLE,
                request_id=f"exhaust-{index}",
                timestamp=TEST_NOW,
            )
            self.service.confirm(
                reservation.reservation_id,
                timestamp=TEST_NOW,
            )
        with self.assertRaises(VipQuotaExceeded):
            self.service.reserve(
                user_id="exhausted-user",
                feature=FEATURE_TREE_HOLE,
                request_id="exhaust-over-limit",
                timestamp=TEST_NOW,
            )

        with self.assertRaises(HTTPException) as context:
            validate_ai_input(
                "字" * 501,
                max_chars=500,
                max_bytes=2000,
                max_tokens=1024,
            )
        self.assertEqual(context.exception.status_code, 413)

        self.service.release(reservation.reservation_id, timestamp=TEST_NOW)
        summary = self.service.get_summary("quota-user", timestamp=TEST_NOW)
        self.assertEqual(
            summary["entitlements"][FEATURE_TREE_HOLE]["remaining"],
            30,
        )

        confirmed = self.service.reserve(
            user_id="quota-user",
            feature=FEATURE_TREE_HOLE,
            request_id="tree-request-2",
            timestamp=TEST_NOW,
        )
        self.service.confirm(confirmed.reservation_id, timestamp=TEST_NOW)
        self.service.release(confirmed.reservation_id, timestamp=TEST_NOW)
        summary = self.service.get_summary("quota-user", timestamp=TEST_NOW)
        self.assertEqual(
            summary["entitlements"][FEATURE_TREE_HOLE]["remaining"],
            29,
        )

    def test_free_user_can_purchase_addon(self):
        order = self.service.create_order(
            "addon-user",
            "addon_community_300",
            timestamp=TEST_NOW,
        )
        fulfilled = self.service.mark_order_paid(
            order_id=order.id,
            user_id="addon-user",
            transaction_id="mock-addon-transaction",
            timestamp=TEST_NOW,
        )

        self.assertEqual(fulfilled.status, "fulfilled")
        summary = self.service.get_summary("addon-user", timestamp=TEST_NOW)
        self.assertEqual(
            summary["entitlements"][FEATURE_COMMUNITY]["remaining"],
            330,
        )
        addon_sources = [
            source
            for source in summary["entitlements"][FEATURE_COMMUNITY]["sources"]
            if source["source_type"] == "addon"
        ]
        self.assertEqual(len(addon_sources), 1)
        self.assertEqual(
            addon_sources[0]["expires_at"],
            TEST_NOW + 90 * 24 * 60 * 60,
        )

    def test_membership_purchase_and_same_plan_renewal(self):
        order = self.service.create_order(
            "member-user",
            "vip_light",
            timestamp=TEST_NOW,
        )
        self.service.mark_order_paid(
            order_id=order.id,
            user_id="member-user",
            transaction_id="mock-member-transaction-1",
            timestamp=TEST_NOW,
        )
        summary = self.service.get_summary("member-user", timestamp=TEST_NOW)
        self.assertEqual(summary["user_type"], "member")
        self.assertEqual(
            summary["entitlements"][FEATURE_TREE_HOLE]["remaining"],
            330,
        )
        original_expiry = summary["membership"]["expires_at"]

        renewal_order = self.service.create_order(
            "member-user",
            "vip_light",
            timestamp=TEST_NOW + 60,
        )
        self.service.mark_order_paid(
            order_id=renewal_order.id,
            user_id="member-user",
            transaction_id="mock-member-transaction-2",
            timestamp=TEST_NOW + 60,
        )
        renewed = self.service.get_summary(
            "member-user",
            timestamp=TEST_NOW + 60,
        )
        self.assertEqual(
            renewed["membership"]["expires_at"],
            add_months(original_expiry),
        )
        self.assertEqual(
            renewed["entitlements"][FEATURE_TREE_HOLE]["remaining"],
            330,
        )

        next_cycle = self.service.get_summary(
            "member-user",
            timestamp=original_expiry + 1,
        )
        self.assertEqual(next_cycle["user_type"], "member")
        self.assertEqual(
            next_cycle["entitlements"][FEATURE_TREE_HOLE]["remaining"],
            330,
        )
        self.assertEqual(
            next_cycle["membership"]["current_period_start"],
            original_expiry,
        )

    def test_vip_api_catalog_order_and_mock_payment(self):
        previous_mock_setting = vip_router_module.ENABLE_VIP_MOCK_PAYMENT
        vip_router_module.ENABLE_VIP_MOCK_PAYMENT = True
        try:
            catalog = vip_router_module.get_vip_catalog()
            self.assertEqual(len(catalog["membership_products"]), 3)

            before = vip_router_module.get_my_vip_state(
                current_user_id="api-user"
            )
            self.assertEqual(
                before["entitlements"][FEATURE_COMMUNITY]["remaining"],
                30,
            )

            created = vip_router_module.create_vip_order(
                vip_router_module.CreateOrderRequest(
                    product_code="addon_community_300"
                ),
                current_user_id="api-user",
            )
            self.assertEqual(created.payment["mode"], "mock")
            order_id = created.order.id

            paid = vip_router_module.mock_pay_vip_order(
                order_id,
                current_user_id="api-user",
            )
            self.assertEqual(paid.status, "fulfilled")

            after = vip_router_module.get_my_vip_state(
                current_user_id="api-user"
            )
            self.assertEqual(
                after["entitlements"][FEATURE_COMMUNITY]["remaining"],
                330,
            )
        finally:
            vip_router_module.ENABLE_VIP_MOCK_PAYMENT = previous_mock_setting


if __name__ == "__main__":
    unittest.main()
