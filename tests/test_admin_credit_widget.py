import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import admin, db, widgets_more as more


class AdminCreditTest(unittest.IsolatedAsyncioTestCase):
    def patches(self):
        return [patch('app.keyboards.cabinet_keyboard', return_value=None),
                patch.object(more.db, 'get_user', AsyncMock(return_value={'balance_rub': 550})),
                patch.object(more.db, 'list_devices', AsyncMock(return_value=[])),
                patch.object(more, 'receipt_state', AsyncMock(return_value={'a': 500, 'b': 550, 'm': 'admin'}))]

    async def run_notify(self, bot, amount):
        ps = self.patches()
        for p in ps:
            p.start()
        try:
            await admin._notify_credit(bot, 7, amount)
        finally:
            for p in ps:
                p.stop()

    async def test_credit_sends_the_receipt_card(self):
        bot = AsyncMock()
        await self.run_notify(bot, 500)
        method = bot.await_args.args[0]
        self.assertEqual(method.__api_method__, 'sendWidget')
        self.assertEqual(json.loads(method.chat_data)['m'], 'admin')
        self.assertIn('500 ₽', method.caption)
        bot.send_message.assert_not_awaited()

    async def test_deduction_and_missing_bot_stay_quiet(self):
        bot = AsyncMock()
        await self.run_notify(bot, -100)
        await self.run_notify(None, 100)
        bot.assert_not_awaited()

    async def test_old_telegram_gets_text(self):
        bot = AsyncMock(side_effect=RuntimeError('no widgets'))
        bot.send_message = AsyncMock()
        await self.run_notify(bot, 300)
        self.assertIn('начислено 300 ₽', bot.send_message.await_args.args[1])

    async def test_receipt_page_names_admin_credits(self):
        self.assertIn("admin:'от поддержки'", more.RECEIPT_HTML)
        self.assertIn("'начисление'", more.RECEIPT_HTML)


class HistoryTest(unittest.IsolatedAsyncioTestCase):
    async def test_topups_are_in_the_history_without_tariff_codes(self):
        rows = [{'id': 1, 'kind': 'topup', 'amount': 50, 'note': 'b50'}, {'id': 2, 'kind': 'promo', 'amount': 30, 'note': 'Промокод X'}]
        pool = SimpleNamespace(fetch=AsyncMock(return_value=rows))
        settings = SimpleNamespace(plan_by_code=lambda code: {'topup_rub': 50} if code == 'b50' else None)
        with patch.object(db, '_pool_req', return_value=pool), patch.object(db, 'get_settings', return_value=settings):
            items = await db.user_billing_history(1)
        kinds = pool.fetch.await_args.args[3]
        self.assertTrue({'topup', 'promo', 'router'} <= set(kinds))
        self.assertIsNone(items[0]['note'])
        self.assertEqual(items[1]['note'], 'Промокод X')


if __name__ == '__main__':
    unittest.main()
