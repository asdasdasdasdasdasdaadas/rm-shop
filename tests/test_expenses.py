"""«Затраты»: next dates by period, the summary, validation and reminders to the channel without repeats."""
import asyncio
import os
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app import db, expenses


def item(id=1, title="Хостинг", amount=1000, currency="RUB", period="month", next_date=date(2026, 11, 25), **kw):
    return {"id": id, "title": title, "amount": amount, "currency": currency, "period": period,
            "next_date": next_date, "anchor_day": kw.pop("anchor_day", next_date.day), "url": "", "description": "",
            "done_at": None, **kw}


class PeriodTest(unittest.TestCase):
    def test_month_keeps_its_day_after_a_short_month(self):
        feb = expenses.add_period(date(2027, 1, 31), "month", 31)
        self.assertEqual(feb, date(2027, 2, 28))
        self.assertEqual(expenses.add_period(feb, "month", 31), date(2027, 3, 31))

    def test_quarter_year_and_once(self):
        self.assertEqual(expenses.add_period(date(2026, 11, 30), "quarter"), date(2027, 2, 28))
        self.assertEqual(expenses.add_period(date(2028, 2, 29), "year", 29), date(2029, 2, 28))
        self.assertIsNone(expenses.add_period(date(2026, 11, 1), "once"))

    def test_dates_from_either_driver(self):
        self.assertEqual(expenses.as_day("2026-11-22T00:00:00.000Z"), date(2026, 11, 22))
        self.assertEqual(expenses.as_day(datetime(2026, 11, 22, 5, tzinfo=timezone.utc)), date(2026, 11, 22))


class SummaryTest(unittest.TestCase):
    def test_month_30_days_overdue_and_averages(self):
        today = date(2026, 11, 22)
        items = [
            item(1, next_date=date(2026, 11, 25)),                                       # this month and next 30 days
            item(2, "Домен", 1200, period="year", next_date=date(2027, 3, 1)),            # neither
            item(3, "Сервер", 20, "USD", next_date=date(2026, 11, 20)),                   # overdue
            item(4, "Лицензия", 500, period="once", next_date=date(2026, 12, 10)),        # next 30 days only
            item(5, "Старое", 999, period="once", next_date=date(2026, 1, 1), done_at=datetime(2026, 1, 1)),
        ]
        s = expenses.summarize(items, [{"amount": 300, "currency": "RUB", "paid_on": date(2026, 11, 3)}], today)
        self.assertEqual(s["month_due"], {"RUB": 1000, "USD": 20})
        self.assertEqual(s["month_paid"], {"RUB": 300})
        self.assertEqual(s["next_30"], {"RUB": 1500, "USD": 40})   # overdue + the next one on 20.12
        self.assertEqual((s["overdue_count"], s["overdue"]), (1, {"USD": 20}))
        self.assertEqual(s["per_month"], {"RUB": 1100, "USD": 20})
        self.assertEqual(s["per_year"], {"RUB": 13200, "USD": 240})
        self.assertEqual([u["id"] for u in s["upcoming"]], [3, 1, 4, 2])
        self.assertEqual(s["upcoming"][0]["days_left"], -2)


class CleanTest(unittest.TestCase):
    def test_good_form(self):
        data = expenses.clean({"title": " VDS ", "amount": "1 499,5", "currency": "usd", "period": "year",
                               "next_date": "2026-12-01", "url": "my.host.ru/billing", "description": "карта *1234"})
        self.assertEqual((data["title"], str(data["amount"]), data["currency"], data["url"]),
                         ("VDS", "1499.50", "USD", "https://my.host.ru/billing"))

    def test_bad_form(self):
        good = {"title": "x", "amount": "1", "next_date": "2026-12-01"}
        for bad in ({**good, "title": ""}, {**good, "amount": "0"}, {**good, "amount": "abc"}, {**good, "period": "day"},
                    {**good, "next_date": ""}, {**good, "next_date": "31.12"}, {**good, "url": "javascript:alert(1)"},
                    {**good, "currency": "BTC"}, None):
            with self.assertRaises(ValueError, msg=bad):
                expenses.clean(bad)

    def test_days(self):
        self.assertEqual(expenses.parse_days("0, 3;7 3"), [7, 3, 0])
        for bad in ("", "завтра", "-1", "99"):
            with self.assertRaises(ValueError):
                expenses.parse_days(bad)


class StageTest(unittest.TestCase):
    def test_stages(self):
        due, days = date(2026, 11, 25), [3, 0]
        self.assertIsNone(expenses.stage_for(due, date(2026, 11, 21), days))
        self.assertEqual(expenses.stage_for(due, date(2026, 11, 22), days), 3)
        self.assertEqual(expenses.stage_for(due, date(2026, 11, 24), days), 3)   # missed day: still the 3-day one
        self.assertEqual(expenses.stage_for(due, date(2026, 11, 25), days), 0)
        self.assertEqual(expenses.stage_for(due, date(2026, 11, 26), days), -1)
        self.assertIsNone(expenses.stage_for(due, date(2026, 12, 10), days))

    def test_message(self):
        rows = [item(1, "Хост <b>", 1500.5, url="https://h.ru/?a=1&b=2", next_date=date(2026, 11, 25)),
                item(2, "Сервер", 20, "USD", next_date=date(2026, 11, 22))]
        text = expenses.format_reminder(rows, date(2026, 11, 22))
        self.assertIn("Скоро оплата сервисов", text)
        self.assertIn('<a href="https://h.ru/?a=1&amp;b=2">Хост &lt;b&gt;</a>', text)
        self.assertIn("1 500,50 ₽", text)
        self.assertIn("сегодня", text)
        self.assertIn("через 3 дня", text)
        self.assertIn("Итого: 20 $ + 1 500,50 ₽", text)
        late = expenses.format_reminder([item(next_date=date(2026, 11, 20))], date(2026, 11, 22))
        self.assertIn("просрочено на 2 дня", late)


class SendTest(unittest.IsolatedAsyncioTestCase):
    async def test_off_or_early_sends_nothing(self):
        bot = SimpleNamespace(send_message=AsyncMock())
        with patch.object(expenses.db, "flag_on", AsyncMock(return_value=False)):
            self.assertEqual(await expenses.send_due(bot, datetime(2026, 11, 22, 9, tzinfo=timezone.utc)), 0)
        with patch.object(expenses.db, "flag_on", AsyncMock(return_value=True)):
            self.assertEqual(await expenses.send_due(bot, datetime(2026, 11, 22, 5, tzinfo=timezone.utc)), 0)
        bot.send_message.assert_not_awaited()


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class ExpensesDb(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from tests.test_funnel_integration import PgPool
        self.proc = await asyncio.create_subprocess_exec(
            os.environ.get("NODE_BIN", "node"), str(Path(__file__).parent / "support/pglite_bridge.mjs"),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
        self.pool = PgPool(self.proc)
        await self.pool.query(db.SCHEMA_PATH.read_text(), script=True)
        p = patch.object(db, "_pool_req", return_value=self.pool)
        p.start()
        self.addCleanup(p.stop)

    async def asyncTearDown(self):
        self.proc.stdin.close()
        await self.proc.wait()

    async def add(self, **kw):
        body = {"title": "Хостинг", "amount": "1500", "period": "month", "next_date": "2026-11-25", **kw}
        return await expenses.create(expenses.clean(body))

    async def test_crud_paid_and_summary(self):
        host = await self.add(url="https://host.example/billing", description="VDS в Амстердаме")
        once = await self.add(title="SSL", amount="900", period="once", next_date="2026-11-30")
        view = await expenses.overview(date(2026, 11, 22))
        self.assertEqual([x["title"] for x in view["items"]], ["Хостинг", "SSL"])
        self.assertEqual(view["items"][0]["url"], "https://host.example/billing")
        self.assertEqual(view["summary"]["month_due"], {"RUB": 2400})

        self.assertTrue(await expenses.update(host, expenses.clean(
            {"title": "Хостинг VDS", "amount": "1700", "period": "month", "next_date": "2026-11-30"})))
        moved = await expenses.mark_paid(host, date(2026, 11, 22))
        self.assertEqual(moved, {"next_date": "2026-12-30", "closed": False})
        self.assertEqual((await expenses.mark_paid(once, date(2026, 11, 22)))["closed"], True)
        with self.assertRaises(ValueError):
            await expenses.mark_paid(once)

        view = await expenses.overview(date(2026, 11, 22))
        s = view["summary"]
        self.assertEqual((s["month_due"], s["month_paid"]), ({}, {"RUB": 2600}))
        self.assertEqual(s["next_30"], {})   # next one is on 30.12
        self.assertEqual([x["done"] for x in view["items"]], [False, True])
        self.assertEqual([h["title"] for h in view["history"]], ["SSL", "Хостинг VDS"])
        self.assertTrue(await expenses.delete(once))
        self.assertFalse(await expenses.delete(once))
        self.assertEqual(len((await expenses.overview(date(2026, 11, 22)))["history"]), 2)   # history stays

    async def test_reminders_go_once_per_stage(self):
        await self.add(next_date="2026-11-25")
        await self.add(title="Домен", period="year", next_date="2027-05-01")
        await expenses.save_notify({"enabled": True, "days": "3, 0"})
        self.assertEqual((await expenses.notify_settings())["days"], [3, 0])
        bot = SimpleNamespace(send_message=AsyncMock())
        at = lambda d, h=12: datetime(2026, 11, d, h - 3, tzinfo=timezone.utc)   # Moscow hour h
        with patch("app.stuck_alert._targets", AsyncMock(return_value=[-100])):
            self.assertEqual(await expenses.send_due(bot, at(22)), 1)
            self.assertEqual(await expenses.send_due(bot, at(22)), 0)       # no repeat
            self.assertEqual(await expenses.send_due(bot, at(24)), 0)       # still the 3-day stage
            self.assertEqual(await expenses.send_due(bot, at(25, 9)), 0)    # before 10:00
            self.assertEqual(await expenses.send_due(bot, at(25)), 1)
            self.assertEqual(await expenses.send_due(bot, at(26)), 1)       # overdue, once
            self.assertEqual(await expenses.send_due(bot, at(27)), 0)
            await expenses.save_notify({"enabled": False})
            self.assertEqual(await expenses.send_due(bot, at(28)), 0)
        self.assertEqual(bot.send_message.await_count, 3)
        self.assertIn("через 3 дня", bot.send_message.await_args_list[0].args[1])
        self.assertIn("просрочено", bot.send_message.await_args_list[2].args[1])


if __name__ == "__main__":
    unittest.main()
