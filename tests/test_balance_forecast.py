"""«Баланс на исходе» on time: when the VPN switches off, and when the warning goes out."""
import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

from app import balance_forecast as bf
from app.balance_notifications import balance_details

MSK = timezone(timedelta(hours=3))


def msk(day, hour, minute=0):
    return datetime(2026, 11, day, hour, minute, tzinfo=MSK).astimezone(timezone.utc)


class OffAtTest(unittest.TestCase):
    def test_one_device_pays_until_money_ends(self):
        now = msk(18, 12)
        # Charged at 07:00 today, 25 ₽ at 10 ₽/day: tomorrow and the day after are paid, off at 07:00 on the 21st.
        self.assertEqual(bf.off_at(25, [msk(18, 7)], 10, now), msk(21, 7))
        self.assertEqual(bf.off_at(5, [msk(18, 7)], 10, now), msk(19, 7))

    def test_devices_charged_at_different_hours(self):
        now = msk(18, 12)
        # 15 ₽ at 10 ₽: the 20:00 device takes 10 ₽ tonight, the 07:00 one finds 5 ₽ tomorrow morning.
        self.assertEqual(bf.off_at(15, [msk(18, 20) - timedelta(days=1), msk(18, 7)], 10, now), msk(19, 7))

    def test_overdue_charge_counts_from_now_and_no_devices_is_unknown(self):
        now = msk(18, 12)
        self.assertEqual(bf.off_at(0, [msk(16, 7)], 10, now), now)
        self.assertIsNone(bf.off_at(50, [], 10, now))


class WhenToWarnTest(unittest.TestCase):
    def test_a_day_ahead_in_the_daytime(self):
        self.assertTrue(bf.warn_now(msk(19, 15), msk(18, 15)))
        self.assertFalse(bf.warn_now(msk(19, 16), msk(18, 15)))

    def test_night_switch_off_is_announced_the_day_before(self):
        off = msk(20, 6)
        self.assertFalse(bf.warn_now(off, msk(19, 6)))  # a day ahead falls at night: not at 6 am
        self.assertTrue(bf.warn_now(off, msk(19, 10)))  # 20 hours ahead, in the daytime

    def test_night_waits_for_the_morning_unless_it_is_too_late(self):
        self.assertFalse(bf.warn_now(msk(19, 18), msk(19, 3)))  # off in the evening: wait for 10:00
        self.assertTrue(bf.warn_now(msk(19, 8), msk(19, 3)))    # off before the morning: say it now

    def test_label(self):
        now = msk(18, 12)
        self.assertEqual(bf.when_label(msk(18, 18, 47), now), "сегодня около 18:40")
        self.assertEqual(bf.when_label(msk(19, 7, 5), now), "завтра около 7:00")
        self.assertEqual(bf.when_label(msk(20, 9, 30), now), "20 ноября около 9:30")
        self.assertIn("VPN выключится <b>завтра около 7:00</b>", balance_details(5, 1, 10, off_label="завтра около 7:00"))


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class CandidatesTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from unittest.mock import patch
        from app import db
        from tests.test_funnel_integration import PgPool
        self.db = db
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

    async def test_candidates_carry_device_charges_and_closest_come_first(self):
        await self.pool.execute("""INSERT INTO users (telegram_id, balance_rub, has_paid_topup, bot_started_at, first_online_at)
            VALUES (1, 15, TRUE, NOW(), NOW()), (2, 5, TRUE, NOW(), NOW())""")
        await self.pool.execute("""INSERT INTO devices (telegram_id, title, kind, last_billed_at, panel_status) VALUES
            (1, 'a', 'phone', NOW() - INTERVAL '3 hours', 'ACTIVE'), (2, 'b', 'phone', NOW() - INTERVAL '1 hour', 'ACTIVE'),
            (2, 'off', 'phone', NOW() - INTERVAL '5 days', 'DISABLED')""")
        rows = await self.db.list_due_trial_end_nudges(10)
        self.assertEqual([r["telegram_id"] for r in rows], [2, 1])
        self.assertEqual([len(r["billed"]) for r in rows], [1, 1])  # the switched-off device is not in the forecast
        self.assertEqual([r["stage"] for r in rows], [1, 1])
        self.assertTrue(await self.db.claim_balance_ending_notice(1, 10))  # 15 ₽ ≤ two days of 10 ₽


if __name__ == "__main__":
    unittest.main()
