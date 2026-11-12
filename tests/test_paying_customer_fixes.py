"""A paid invoice outlives late payments, customers skip the channel check, balance warnings come in two steps."""
import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import access, db
from app.balance_notifications import balance_details


class UnpaidOrdersKeptTest(unittest.IsolatedAsyncioTestCase):
    async def test_purge_waits_a_week_and_never_touches_granted(self):
        pool = SimpleNamespace(execute=AsyncMock(return_value="DELETE 0"))
        with patch.object(db, "_pool_req", return_value=pool):
            await db.purge_stale_unpaid_orders()
        sql, limit, days = pool.execute.call_args.args
        self.assertIn("status <> 'granted'", sql)
        self.assertIn("make_interval(days => $2)", sql)
        self.assertNotIn("30 minutes", sql)
        self.assertEqual(days, 7)


class ChannelGateTest(unittest.IsolatedAsyncioTestCase):
    async def check(self, *, enabled=True, paid=False, devices=0, member=False):
        settings = SimpleNamespace(required_channel_enabled=enabled)
        with patch.object(access, "get_settings", return_value=settings), \
             patch.object(db, "get_user", AsyncMock(return_value={"has_paid_topup": paid})), \
             patch.object(db, "device_count", AsyncMock(return_value=devices)), \
             patch.object(access, "is_channel_member", AsyncMock(return_value=member)) as member_check:
            return await access.channel_gate_passed(SimpleNamespace(), 1), member_check

    async def test_customers_pass_after_leaving_the_channel(self):
        self.assertTrue((await self.check(paid=True))[0])
        self.assertTrue((await self.check(devices=1))[0])

    async def test_newcomers_still_need_the_channel(self):
        ok, member_check = await self.check()
        self.assertFalse(ok)
        member_check.assert_awaited_once()
        self.assertTrue((await self.check(member=True))[0])

    async def test_switched_off_channel_asks_nothing(self):
        ok, member_check = await self.check(enabled=False)
        self.assertTrue(ok)
        member_check.assert_not_awaited()


class BalanceWarningStagesTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.c = sqlite3.connect(":memory:")
        self.addCleanup(self.c.close)
        self.c.executescript("""CREATE TABLE users (telegram_id INTEGER, trial_end_nudge_at TEXT, balance_warn3_at TEXT,
            bot_started_at TEXT, first_online_at TEXT, bot_blocked_at TEXT, blocked_at TEXT, billing_paused_at TEXT,
            balance_rub INTEGER, has_paid_topup BOOLEAN);
            INSERT INTO users VALUES (1, NULL, NULL, 'start', 'online', NULL, NULL, NULL, 18, TRUE);
            CREATE TABLE devices (telegram_id INTEGER, kind TEXT);
            INSERT INTO devices VALUES (1, 'phone');
            CREATE TABLE message_log (telegram_id INTEGER, kind TEXT, status TEXT, created_at TEXT);""")

    def pool(self):
        def query(sql, args):
            sql = sql.replace("NOW()-INTERVAL '24 hours'", "'2026-09-24'").replace("NOW()", "'2026-09-25'")
            return self.c.execute(sql, {str(i): a for i, a in enumerate(args, 1)})
        async def fetchrow(sql, *args): return query(sql, args).fetchone()
        async def execute(sql, *args): return query(sql, args)
        return SimpleNamespace(fetchrow=fetchrow, execute=execute)

    async def test_three_days_then_one_day_for_people_who_paid(self):
        with patch.object(db, "_pool_req", return_value=self.pool()):
            self.assertFalse(await db.claim_balance_ending_notice(1, 6))  # 3 days left: not the last-day warning
            self.assertTrue(await db.claim_balance_ending_notice(1, 6, stage=3))
            self.assertFalse(await db.claim_balance_ending_notice(1, 6, stage=3))  # once
            self.c.execute("INSERT INTO message_log VALUES (1, 'nudge_trial_end', 'sent', '2026-09-24 12:00')")
            self.c.execute("UPDATE users SET balance_rub=6")
            self.assertFalse(await db.claim_balance_ending_notice(1, 6))  # the 3-day warning went out within 24 hours
            self.c.execute("UPDATE message_log SET created_at='2026-09-22'")
            self.assertTrue(await db.claim_balance_ending_notice(1, 6))

    async def test_gift_only_users_get_no_early_warning(self):
        self.c.execute("UPDATE users SET has_paid_topup=FALSE")
        with patch.object(db, "_pool_req", return_value=self.pool()):
            self.assertFalse(await db.claim_balance_ending_notice(1, 6, stage=3))

    async def test_release_frees_only_its_own_stage(self):
        with patch.object(db, "_pool_req", return_value=self.pool()):
            self.assertTrue(await db.claim_balance_ending_notice(1, 6, stage=3))
            await db.release_balance_ending_notice(1, stage=3)
            self.assertTrue(await db.claim_balance_ending_notice(1, 6, stage=3))

    def test_details_say_how_long_the_balance_lasts(self):
        self.assertIn("хватит примерно на 3 дня", balance_details(18, 1, 6))
        self.assertIn("хватит примерно на 1 день", balance_details(12, 2, 6))
        self.assertIn("меньше чем на сутки", balance_details(5, 1, 6))


class BalanceWarningsReachMutedUsersTest(unittest.IsolatedAsyncioTestCase):
    async def test_exit_answer_mutes_reminders_but_not_balance_warnings(self):
        pool = SimpleNamespace(fetchval=AsyncMock(side_effect=lambda sql, *a: True if "EXISTS" in sql and "device_exit_feedback" in sql else True))
        with patch.object(db, "_pool_req", return_value=pool), patch.object(db, "notification_allowed", AsyncMock(return_value=True)):
            await db.nudge_delivery_allowed(1, "nudge_trial_end")
            await db.nudge_delivery_allowed(1, "low_balance")
            self.assertFalse(any("device_exit_feedback" in c.args[0] for c in pool.fetchval.call_args_list))
            await db.nudge_delivery_allowed(1, "nudge_idle")
            self.assertTrue(any("device_exit_feedback" in c.args[0] for c in pool.fetchval.call_args_list))


if __name__ == "__main__":
    unittest.main()
