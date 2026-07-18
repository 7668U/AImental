import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

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
    ADDON_PRODUCTS,
    FEATURE_ASSESSMENT_ANALYSIS,
    FEATURE_COMMUNITY,
    FEATURE_MOOD_ANALYSIS,
    FEATURE_TREE_HOLE,
    PLAN_PRODUCTS,
)
from vip_service import VipQuotaExceeded, VipService, add_months
from vip_access import validate_ai_input
from vip_virtual_payment import (
    _virtual_payment_app_key,
    build_virtual_payment,
)
from vip_payment_sync import (
    _ACCESS_TOKEN_CACHE,
    parse_callback_body,
    reconcile_order,
    verify_message_signature,
)
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

    def test_virtual_payment_selects_app_key_by_environment(self):
        with patch.dict(
            os.environ,
            {
                "WECHAT_VIRTUAL_PAY_APP_KEY": "production-key",
                "WECHAT_VIRTUAL_PAY_SANDBOX_APP_KEY": "sandbox-key",
            },
            clear=False,
        ):
            self.assertEqual(
                _virtual_payment_app_key(0),
                "production-key",
            )
            self.assertEqual(
                _virtual_payment_app_key(1),
                "sandbox-key",
            )

    def test_real_virtual_payment_never_exposes_local_confirm_endpoint(self):
        order = self.service.create_order(
            "real-payment-user",
            "vip_light",
            timestamp=TEST_NOW,
        )
        with patch.dict(
            os.environ,
            {
                "WECHAT_VIRTUAL_PAY_OFFER_ID": "offer-id",
                "WECHAT_VIRTUAL_PAY_APP_KEY": "production-key",
                "WECHAT_VIRTUAL_PAY_ENV": "0",
            },
            clear=False,
        ):
            payment = build_virtual_payment(
                order=order,
                user=SimpleNamespace(wechat_session_key="session-key"),
            )

        self.assertEqual(payment["mode"], "wechat_virtual")
        self.assertIsNone(payment["local_confirm_endpoint"])

    def test_virtual_payment_reconcile_fulfills_paid_membership_order(self):
        order = self.service.create_order(
            "reconcile-member-user",
            "vip_light",
            timestamp=TEST_NOW,
        )
        access_token_response = SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "access_token": "wechat-access-token",
                "expires_in": 7200,
            },
        )
        order_response = SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "errcode": 0,
                "errmsg": "ok",
                "order": {
                    "status": 2,
                    "order_fee": order.amount_fen,
                    "paid_time": TEST_NOW + 30,
                    "wxpay_order_id": "wxpay-reconcile-transaction",
                },
            },
        )
        _ACCESS_TOKEN_CACHE.update({"value": "", "expires_at": 0})
        with patch.dict(
            os.environ,
            {
                "WECHAT_APP_ID": "test-app-id",
                "WECHAT_APP_SECRET": "test-app-secret",
                "WECHAT_VIRTUAL_PAY_APP_KEY": "production-key",
                "WECHAT_VIRTUAL_PAY_ENV": "0",
            },
            clear=False,
        ), patch(
            "vip_payment_sync.requests.get",
            return_value=access_token_response,
        ), patch(
            "vip_payment_sync.requests.post",
            return_value=order_response,
        ):
            fulfilled, paid, provider_status = reconcile_order(
                order,
                SimpleNamespace(openid="user-openid"),
                self.service,
            )

        self.assertTrue(paid)
        self.assertEqual(provider_status, 2)
        self.assertEqual(fulfilled.status, "fulfilled")
        summary = self.service.get_summary(
            "reconcile-member-user",
            timestamp=TEST_NOW + 30,
        )
        self.assertEqual(summary["user_type"], "member")
        self.assertEqual(summary["membership"]["plan_code"], "light")

    def test_virtual_payment_callback_parser_and_signature(self):
        token = "callback-token"
        timestamp = "1784380800"
        nonce = "nonce-value"
        import hashlib

        signature = hashlib.sha1(
            "".join(sorted((token, timestamp, nonce))).encode("utf-8")
        ).hexdigest()
        self.assertTrue(
            verify_message_signature(
                signature=signature,
                timestamp=timestamp,
                nonce=nonce,
                token=token,
            )
        )

        payload, fmt = parse_callback_body(
            b'{"Event":"xpay_goods_deliver_notify","OutTradeNo":"order123"}'
        )
        self.assertEqual(fmt, "json")
        self.assertEqual(payload["Event"], "xpay_goods_deliver_notify")

    def test_loading_vip_state_recovers_recent_paid_pending_order(self):
        order = self.service.create_order(
            "recover-member-user",
            "vip_light",
            timestamp=TEST_NOW,
        )
        fake_user = SimpleNamespace(
            id="recover-member-user",
            openid="recover-openid",
            wechat_session_key="recover-session-key",
        )

        def fake_reconcile(pending_order, user, service):
            fulfilled = service.mark_order_paid(
                order_id=pending_order.id,
                user_id=pending_order.user_id,
                transaction_id="wxpay-recovered-transaction",
                timestamp=TEST_NOW + 10,
            )
            return fulfilled, True, 2

        with patch.object(
            vip_router_module.user_table,
            "get_user_by_id",
            return_value=fake_user,
        ), patch.object(
            vip_router_module,
            "real_virtual_payment_ready",
            return_value=True,
        ), patch.object(
            vip_router_module,
            "reconcile_order",
            side_effect=fake_reconcile,
        ), patch.object(
            vip_router_module.time,
            "time",
            return_value=TEST_NOW + 20,
        ):
            state = vip_router_module.get_my_vip_state(
                current_user_id="recover-member-user"
            )

        self.assertEqual(order.get().status, "fulfilled")
        self.assertEqual(state["user_type"], "member")
        self.assertEqual(state["membership"]["plan_code"], "light")

    def test_free_monthly_quotas_are_created(self):
        summary = self.service.get_summary("free-user", timestamp=TEST_NOW)

        self.assertEqual(summary["user_type"], "free")
        self.assertEqual(
            summary["entitlements"][FEATURE_TREE_HOLE]["remaining"],
            100,
        )
        self.assertEqual(
            summary["entitlements"][FEATURE_COMMUNITY]["remaining"],
            100,
        )
        self.assertEqual(
            summary["entitlements"][FEATURE_MOOD_ANALYSIS]["remaining"],
            4,
        )
        self.assertEqual(
            summary["entitlements"][FEATURE_ASSESSMENT_ANALYSIS]["remaining"],
            4,
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
            99,
        )

    def test_quota_exhaustion_and_input_limit(self):
        for index in range(100):
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
            100,
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
            99,
        )

    def test_free_user_can_purchase_addon(self):
        order = self.service.create_order(
            "addon-user",
            "addon_community_500",
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
            600,
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
            1100,
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
            1100,
        )

        next_cycle = self.service.get_summary(
            "member-user",
            timestamp=original_expiry + 1,
        )
        self.assertEqual(next_cycle["user_type"], "member")
        self.assertEqual(
            next_cycle["entitlements"][FEATURE_TREE_HOLE]["remaining"],
            1100,
        )
        self.assertEqual(
            next_cycle["membership"]["current_period_start"],
            original_expiry,
        )

    def test_cancel_membership_for_testing_resets_member_state(self):
        order = self.service.create_order(
            "cancel-member-user",
            "vip_light",
            timestamp=TEST_NOW,
        )
        self.service.mark_order_paid(
            order_id=order.id,
            user_id="cancel-member-user",
            transaction_id="mock-cancel-member-transaction",
            timestamp=TEST_NOW,
        )

        before = self.service.get_summary("cancel-member-user", timestamp=TEST_NOW)
        self.assertEqual(before["user_type"], "member")

        after = self.service.cancel_membership_for_testing(
            "cancel-member-user",
            timestamp=TEST_NOW + 60,
        )

        self.assertEqual(after["user_type"], "free")
        self.assertIsNone(after["membership"])
        self.assertEqual(
            after["entitlements"][FEATURE_TREE_HOLE]["remaining"],
            100,
        )
        membership_sources = [
            source
            for source in after["entitlements"][FEATURE_TREE_HOLE]["sources"]
            if source["source_type"] == "membership"
        ]
        self.assertEqual(membership_sources, [])

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
                100,
            )

            created = vip_router_module.create_vip_order(
                vip_router_module.CreateOrderRequest(
                    product_code="addon_community_500"
                ),
                current_user_id="api-user",
            )
            self.assertEqual(created.payment["mode"], "local_virtual_mock")
            self.assertEqual(created.payment["payload"]["mode"], "short_series_goods")
            order_id = created.order.id

            paid = vip_router_module.local_confirm_virtual_payment(
                order_id,
                current_user_id="api-user",
            )
            self.assertEqual(paid.status, "fulfilled")

            after = vip_router_module.get_my_vip_state(
                current_user_id="api-user"
            )
            self.assertEqual(
                after["entitlements"][FEATURE_COMMUNITY]["remaining"],
                600,
            )
        finally:
            vip_router_module.ENABLE_VIP_MOCK_PAYMENT = previous_mock_setting

    def test_vip_api_membership_local_virtual_payment(self):
        created = vip_router_module.create_vip_order(
            vip_router_module.CreateOrderRequest(product_code="vip_light"),
            current_user_id="api-member-user",
        )
        self.assertEqual(created.payment["mode"], "local_virtual_mock")
        self.assertEqual(created.payment["payload"]["mode"], "short_series_goods")

        paid = vip_router_module.local_confirm_virtual_payment(
            created.order.id,
            current_user_id="api-member-user",
        )
        self.assertEqual(paid.status, "fulfilled")

        summary = vip_router_module.get_my_vip_state(
            current_user_id="api-member-user"
        )
        self.assertEqual(summary["user_type"], "member")
        self.assertEqual(summary["membership"]["plan_code"], "light")

        previous_test_tools_setting = vip_router_module.ENABLE_VIP_TEST_TOOLS
        vip_router_module.ENABLE_VIP_TEST_TOOLS = True
        try:
            reset = vip_router_module.test_cancel_my_vip_membership(
                current_user_id="api-member-user",
            )
        finally:
            vip_router_module.ENABLE_VIP_TEST_TOOLS = previous_test_tools_setting
        self.assertEqual(reset["user_type"], "free")
        self.assertIsNone(reset["membership"])

    def test_catalog_uses_new_quota_ladder_and_addon_prices(self):
        expected_plan_quotas = {
            "vip_light": {
                FEATURE_TREE_HOLE: 1000,
                FEATURE_COMMUNITY: 1000,
                FEATURE_MOOD_ANALYSIS: 100,
                FEATURE_ASSESSMENT_ANALYSIS: 100,
            },
            "vip_knowing": {
                FEATURE_TREE_HOLE: 2000,
                FEATURE_COMMUNITY: 2000,
                FEATURE_MOOD_ANALYSIS: 200,
                FEATURE_ASSESSMENT_ANALYSIS: 200,
            },
            "vip_companion": {
                FEATURE_TREE_HOLE: 3000,
                FEATURE_COMMUNITY: 3000,
                FEATURE_MOOD_ANALYSIS: 300,
                FEATURE_ASSESSMENT_ANALYSIS: 300,
            },
        }
        for product_code, quotas in expected_plan_quotas.items():
            self.assertEqual(PLAN_PRODUCTS[product_code]["quotas"], quotas)

        self.assertEqual(
            {
                code: (product["amount"], product["price_fen"])
                for code, product in ADDON_PRODUCTS.items()
            },
            {
                "addon_tree_500": (500, 199),
                "addon_community_500": (500, 299),
                "addon_mood_50": (50, 99),
                "addon_assessment_50": (50, 99),
            },
        )

    def test_existing_buckets_receive_only_the_quota_increase(self):
        self.service.ensure_free_buckets("quota-upgrade-user", timestamp=TEST_NOW)
        free_bucket = VipQuotaBucket.get(
            (VipQuotaBucket.user_id == "quota-upgrade-user")
            & (VipQuotaBucket.feature == FEATURE_TREE_HOLE)
            & (VipQuotaBucket.source_type == "free")
        )
        free_bucket.total_amount = 30
        free_bucket.remaining_amount = 12
        free_bucket.save()

        upgraded = self.service.get_summary(
            "quota-upgrade-user",
            timestamp=TEST_NOW,
        )
        self.assertEqual(
            upgraded["entitlements"][FEATURE_TREE_HOLE]["total"],
            100,
        )
        self.assertEqual(
            upgraded["entitlements"][FEATURE_TREE_HOLE]["remaining"],
            82,
        )

        order = self.service.create_order(
            "member-quota-upgrade-user",
            "vip_light",
            timestamp=TEST_NOW,
        )
        self.service.mark_order_paid(
            order_id=order.id,
            user_id="member-quota-upgrade-user",
            transaction_id="mock-member-quota-upgrade",
            timestamp=TEST_NOW,
        )
        member_bucket = VipQuotaBucket.get(
            (VipQuotaBucket.user_id == "member-quota-upgrade-user")
            & (VipQuotaBucket.feature == FEATURE_TREE_HOLE)
            & (VipQuotaBucket.source_type == "membership")
        )
        member_bucket.total_amount = 300
        member_bucket.remaining_amount = 125
        member_bucket.save()

        member_upgraded = self.service.get_summary(
            "member-quota-upgrade-user",
            timestamp=TEST_NOW,
        )
        membership_source = next(
            source
            for source in member_upgraded["entitlements"][FEATURE_TREE_HOLE]["sources"]
            if source["source_type"] == "membership"
        )
        self.assertEqual(membership_source["total"], 1000)
        self.assertEqual(membership_source["remaining"], 825)


if __name__ == "__main__":
    unittest.main()
