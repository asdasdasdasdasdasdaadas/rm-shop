"""«Пополнить 50 ₽ / 200 ₽» buttons: amounts from the settings, the cabinet opens on the top-up with the amount."""
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app import funnel_board


class QuickTopup(unittest.IsolatedAsyncioTestCase):
    def settings(self, **kw):
        return SimpleNamespace(**{"balance_topup_min": 50, "balance_topup_step": 50, "balance_topup_max": 100000,
                                  "vpn_day_price_rub": 6, **kw})

    def test_amounts(self):
        for kw, want in (({}, [50, 200]), ({"vpn_day_price_rub": 1}, [50]), ({"balance_topup_min": 100}, [100, 200]),
                         ({"vpn_day_price_rub": 7}, [50, 250])):
            with patch("app.config.get_settings", return_value=self.settings(**kw)):
                self.assertEqual(funnel_board.quick_amounts(), want, kw)

    def test_buttons_open_the_topup_with_the_amount(self):
        with patch("app.config.get_settings", return_value=self.settings()), \
                patch("app.keyboards.mini_app_url", return_value="https://cab.test/app"):
            try:
                kb = funnel_board.markup(["topup_quick", "menu"], 1)
            except (ImportError, TypeError):  # local Python 3.9 cannot build the widget types
                self.skipTest("aiogram types")
        first = kb.inline_keyboard[0]
        self.assertEqual([b.text for b in first], ["Пополнить 50 ₽", "Пополнить 200 ₽"])
        self.assertTrue(first[1].web_app.url.endswith("screen=topup&amount=200"))

    async def test_money_messages_use_them(self):
        with patch.object(funnel_board, "_flag", AsyncMock(return_value=True)):
            graph = await funnel_board.default_graph()
        steps = {s["id"]: s for b in graph["branches"] for s in b["steps"]}
        for sid in ("balance-1", "gift-ending-1", "recovery-recover-topup-1", "recovery-recover-topup-2"):
            self.assertIn("topup_quick", steps[sid]["buttons"], sid)


if __name__ == "__main__":
    unittest.main()
