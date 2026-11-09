import base64
import json
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import ton

WALLET = "UQBuU8RCIxH121MjJofAC2xyvn-7pr2LmdqIiO5d_xVkkGgT"
RAW = "0:6e53c4422311f5db53232687c00b6c72be7fbba6bd8b99da8888ee5dff156490"


def settings(**kw):
    base = dict(ton_enabled=True, ton_wallet=WALLET, ton_rate_margin_pct=1.0, toncenter_api_key="",
                balance_topup_min=50, balance_topup_max=100000, admin_id_set={1})
    base.update(kw)
    return SimpleNamespace(**base)


class AddressTest(unittest.TestCase):
    def test_friendly_and_raw_forms_are_the_same_wallet(self):
        self.assertEqual(ton.parse_address(WALLET), ton.parse_address(RAW))
        self.assertTrue(ton.same_address(WALLET, RAW.upper()))
        self.assertEqual(ton.normalize_wallet(RAW), WALLET)

    def test_bounceable_form_is_stored_as_non_bounceable(self):
        workchain, account = ton.parse_address(WALLET)
        bounceable = ton._friendly(workchain, account, bounceable=True)
        self.assertTrue(bounceable.startswith("EQ"))
        self.assertEqual(ton.normalize_wallet(bounceable), WALLET)

    def test_broken_addresses_are_refused(self):
        for bad in ["", "hello", WALLET[:-1] + "A", "0:1234", WALLET.replace("U", "k", 1)]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                ton.parse_address(bad)


class PayloadTest(unittest.TestCase):
    def test_crc32c_check_value(self):
        self.assertEqual(ton._crc32c(b"123456789"), 0xE3069283)

    def test_comment_is_a_single_cell_boc_with_text_op(self):
        boc = base64.b64decode(ton.comment_payload("VPN-ABC234"))
        self.assertEqual(boc[:4], bytes.fromhex("b5ee9c72"))
        self.assertEqual(boc[4], 0x41)  # crc32c present, 1-byte cell refs
        cell = boc[11:-4]
        self.assertEqual(cell[:2], bytes([0, 2 * 14]))
        self.assertEqual(cell[2:], b"\0\0\0\0VPN-ABC234")
        self.assertEqual(int.from_bytes(boc[-4:], "little"), ton._crc32c(boc[:-4]))


class QuoteTest(unittest.TestCase):
    def test_quote_adds_margin_and_rounds_up_to_milli_ton(self):
        nano = ton.quote_nano(500, Decimal("250"), 1.0)  # 2 TON + 1% = 2.02
        self.assertEqual(nano, 2_020_000_000)
        self.assertEqual(ton.quote_nano(100, Decimal("300"), 0), 334_000_000)

    def test_credit_follows_what_arrived_at_the_locked_price(self):
        order = {"rub": 500, "nano": 2_000_000_000}
        self.assertEqual(ton.credited_rub(order, 2_000_000_000), 500)
        self.assertEqual(ton.credited_rub(order, 1_000_000_000), 250)
        self.assertEqual(ton.credited_rub(order, 2_100_000_000), 525)

    def test_widget_amounts_respect_the_minimum(self):
        with patch.object(ton, "get_settings", return_value=settings(balance_topup_min=400)):
            self.assertEqual(ton.widget_amounts(), [500, 1000])
        with patch.object(ton, "get_settings", return_value=settings(balance_topup_min=5000)):
            self.assertEqual(ton.widget_amounts(), [5000])


class AccessTest(unittest.TestCase):
    def test_admins_can_test_with_the_switch_off(self):
        with patch.object(ton, "get_settings", return_value=settings(ton_enabled=False)):
            self.assertFalse(ton.enabled())
            self.assertTrue(ton.allowed(1))
            self.assertFalse(ton.allowed(2))
        with patch.object(ton, "get_settings", return_value=settings(ton_wallet="")):
            self.assertFalse(ton.allowed(1))


class ChainTest(unittest.TestCase):
    def tx(self, **msg):
        base = {"source": RAW, "value": "2020000000", "bounced": False,
                "message_content": {"decoded": {"type": "text_comment", "comment": "VPN-ABC234"}}}
        base.update(msg)
        return {"hash": "h1", "now": 1700000000, "in_msg": base, "description": {"aborted": False}}

    def test_incoming_transfer_with_comment(self):
        self.assertEqual(ton.parse_incoming(self.tx()), {
            "tx_hash": "h1", "sender": RAW, "nano": 2020000000, "comment": "VPN-ABC234", "utime": 1700000000})

    def test_outgoing_bounced_and_failed_are_skipped(self):
        self.assertIsNone(ton.parse_incoming(self.tx(source=None)))
        self.assertIsNone(ton.parse_incoming(self.tx(bounced=True)))
        self.assertIsNone(ton.parse_incoming(self.tx(value="0")))
        failed = self.tx()
        failed["description"]["aborted"] = True
        self.assertIsNone(ton.parse_incoming(failed))

    def test_transfer_without_comment(self):
        self.assertIsNone(ton.parse_incoming(self.tx(message_content={}))["comment"])


class CreditTest(unittest.IsolatedAsyncioTestCase):
    order = {"order_id": "VPN-ABC234", "telegram_id": 7, "rub": 500, "nano": 2_000_000_000,
             "status": "sent", "chat_id": 7, "message_id": 9}
    incoming = {"tx_hash": "h1", "sender": RAW, "nano": 2_000_000_000, "comment": "VPN-ABC234", "utime": 1}

    def pool(self, claimed="VPN-ABC234"):
        return SimpleNamespace(fetchval=AsyncMock(return_value=claimed), execute=AsyncMock())

    async def test_matching_transfer_is_credited_once(self):
        receipt = {"telegram_id": 7, "payment_key": "ton:VPN-ABC234", "first_payment": False}
        with patch.object(ton.db, "_pool_req", return_value=self.pool()), \
                patch.object(ton.db, "credit_payment_once", AsyncMock(return_value=receipt)) as credit, \
                patch("app.billing.after_credit", AsyncMock()) as after, \
                patch.object(ton, "notify_widget_paid", AsyncMock()) as notify:
            self.assertTrue(await ton.credit(self.order, self.incoming))
        credit.assert_awaited_once_with(7, "ton", "ton:VPN-ABC234", 500)
        self.assertEqual(after.await_args.kwargs["amount"], 500)
        notify.assert_awaited_once_with(self.order, 500)

    async def test_transfer_claimed_by_another_scan_is_not_credited(self):
        with patch.object(ton.db, "_pool_req", return_value=self.pool(claimed=None)), \
                patch.object(ton.db, "credit_payment_once", AsyncMock()) as credit:
            self.assertFalse(await ton.credit(self.order, self.incoming))
        credit.assert_not_awaited()

    async def test_dust_is_not_credited(self):
        with patch.object(ton.db, "credit_payment_once", AsyncMock()) as credit:
            self.assertFalse(await ton.credit(self.order, dict(self.incoming, nano=1000)))
        credit.assert_not_awaited()

    async def test_unknown_comment_is_recorded_as_unmatched(self):
        pool = self.pool(claimed=1)  # first TON order at epoch 1
        with patch.object(ton.db, "_pool_req", return_value=pool), \
                patch.object(ton, "credit", AsyncMock()) as credit:
            self.assertFalse(await ton._handle_incoming(dict(self.incoming, comment="за впн", utime=5)))
        self.assertIsNone(pool.execute.await_args.args[5])
        credit.assert_not_awaited()

    async def test_dust_and_transfers_before_the_first_order_are_ignored(self):
        for incoming, first in [(dict(self.incoming, comment=None, nano=322605, utime=5), 1),
                                (dict(self.incoming, comment=None, utime=5), 10),
                                (dict(self.incoming, comment=None, utime=5), None)]:
            pool = self.pool(claimed=first)
            with self.subTest(incoming=incoming, first=first), patch.object(ton.db, "_pool_req", return_value=pool):
                self.assertFalse(await ton._handle_incoming(incoming))
            pool.execute.assert_not_awaited()

    def test_comment_from_raw_body(self):
        self.assertEqual(ton.comment_from_boc(ton.comment_payload("VPN-ABC234")), "VPN-ABC234")
        self.assertIsNone(ton.comment_from_boc("not a boc"))
        tx = {"hash": "h", "now": 1, "description": {}, "in_msg": {
            "source": RAW, "value": "5", "message_content": {"body": ton.comment_payload("VPN-ABC234")}}}
        self.assertEqual(ton.parse_incoming(tx)["comment"], "VPN-ABC234")


class WidgetQueryTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        p = patch.object(ton, "get_settings", return_value=settings())
        p.start()
        self.addCleanup(p.stop)
        self.bot = AsyncMock()

    async def test_order_answer_is_a_ton_connect_transaction(self):
        order = {"order_id": "VPN-ABC234", "nano": 2_020_000_000,
                 "valid_until": datetime(2030, 1, 1, tzinfo=timezone.utc)}
        with patch.object(ton, "create_order", AsyncMock(return_value=order)) as create:
            answer = await ton.handle_query(self.bot, {"chat": {"id": 7}, "message_id": 9}, 7, "t:500")
        create.assert_awaited_once_with(7, 500, chat_id=7, message_id=9)
        message = answer["tx"]["messages"][0]
        self.assertEqual((message["address"], message["amount"]), (WALLET, "2020000000"))
        self.assertEqual(answer["tx"]["valid_until"], 1893456000)
        self.assertLessEqual(len(json.dumps(answer)), 1024)

    async def test_rate_outage_is_reported(self):
        with patch.object(ton, "rub_per_ton", AsyncMock(side_effect=OSError)):
            answer = await ton.handle_query(self.bot, {}, 7, "t:500")
        self.assertEqual(answer, {"e": "Курс TON недоступен, попробуйте позже"})

    async def test_someone_elses_order_is_not_found(self):
        with patch.object(ton, "get_order", AsyncMock(return_value={"order_id": "VPN-ABC234", "telegram_id": 8})):
            self.assertEqual(await ton.handle_query(self.bot, {}, 7, "q:VPN-ABC234"), {"e": "Счёт не найден"})

    async def test_sent_transfer_starts_watching(self):
        order = {"order_id": "VPN-ABC234", "telegram_id": 7, "rub": 500}
        query = {"chat": {"id": 7}, "message_id": 9,
                 "type": {"type": "sent_transaction", "wallet": {"address": RAW}, "msg_hash": "m"}}
        with patch.object(ton, "get_order", AsyncMock(return_value=order)), \
                patch.object(ton, "mark_sent", AsyncMock(return_value=order)) as sent, \
                patch.object(ton, "watch") as watch:
            answer = await ton.handle_query(self.bot, query, 7, "p:VPN-ABC234")
        self.assertEqual(answer, {"w": "VPN-ABC234"})
        sent.assert_awaited_once_with("VPN-ABC234", 7, sender=RAW, msg_hash="m")
        watch.assert_called_once_with("VPN-ABC234")
        self.assertEqual(json.loads(self.bot.await_args.args[0].chat_data)["w"], "VPN-ABC234")

    async def test_status_of_a_paid_order(self):
        order = {"order_id": "VPN-ABC234", "telegram_id": 7, "status": "paid", "credited_rub": 500}
        with patch.object(ton, "get_order", AsyncMock(return_value=order)), \
                patch.object(ton.db, "get_user", AsyncMock(return_value={"balance_rub": 620})):
            answer = await ton.handle_query(self.bot, {}, 7, "q:VPN-ABC234")
        self.assertEqual(answer, {"ok": {"o": "VPN-ABC234", "c": 500, "b": 620}})

    async def test_widget_routes_ton_requests(self):
        from app import widgets
        with patch.object(ton, "handle_query", AsyncMock(return_value={"w": "x"})) as handle:
            result = await widgets.handle_query(self.bot, {"from": {"id": 7}, "data": "q:VPN-ABC234"})
        self.assertEqual(result, {"w": "x"})
        handle.assert_awaited_once()


class PayWidgetTest(unittest.TestCase):
    def test_fits_telegram_limits(self):
        import zlib
        from app.widgets import ton_pay_html
        page = ton_pay_html().encode()
        self.assertLessEqual(len(zlib.compress(page, 9)), 4096)
        self.assertIn(b"sendTransaction", page)


class SettingsTest(unittest.TestCase):
    def test_wallet_is_required_to_enable_and_normalized(self):
        from app import shop_config
        with patch("app.shop_config.get_settings", return_value=settings(ton_enabled=False, ton_wallet="")):
            with self.assertRaisesRegex(ValueError, "адрес кошелька"):
                shop_config._validate_ton({"ton_enabled": True, "ton_wallet": ""})
            out = shop_config._validate_ton({"ton_wallet": RAW, "ton_rate_margin_pct": 2})
        self.assertEqual(out["ton_wallet"], WALLET)
        self.assertFalse(out["ton_enabled"])


if __name__ == "__main__":
    unittest.main()
