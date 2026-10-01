import unittest
from datetime import datetime, date, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from app import db

class PaySoonStatisticsTest(unittest.IsolatedAsyncioTestCase):
    async def test_counts_online_users_near_zero_or_on_trust(self):
        pool = SimpleNamespace(fetchrow=AsyncMock(return_value={'total': 4, 'low_balance': 3, 'trust': 2}))
        with patch.object(db, '_pool_req', return_value=pool):
            result = await db.admin_pay_soon_counts(6)
        self.assertEqual(result, {'days': 3, 'day_price_rub': 6, 'total': 4, 'low_balance': 3, 'trust': 2})
        sql, horizon = pool.fetchrow.call_args.args
        self.assertEqual(horizon, 18)
        self.assertIn('first_online_at IS NOT NULL', sql)
        self.assertIn('trust_loans', sql)
        self.assertIn("COALESCE(d.kind, '') <> 'router'", sql)
        self.assertIn('billing_paused_at IS NULL', sql)


class AdminStatisticsTest(unittest.IsolatedAsyncioTestCase):
    async def test_moscow_days_zero_fill_and_separate_currencies(self):
        pool = SimpleNamespace(fetch=AsyncMock(return_value=[
            {'day': date(2026, 9, 27), 'kind': 'payments', 'code': 'topup_100', 'value': 2},
            {'day': date(2026, 9, 27), 'kind': 'payments', 'code': 'topup_250', 'value': 1},
            {'day': date(2026, 9, 27), 'kind': 'stars', 'code': '', 'value': 70},
            {'day': date(2026, 9, 21), 'kind': 'registered', 'code': '', 'value': 3},
        ]), fetchrow=AsyncMock(return_value={'traffic_bytes': 100, 'devices_total': 2}))
        settings = SimpleNamespace(topup_rub_for_code=lambda c: {'topup_100': 100, 'topup_250': 250}[c])
        with patch.object(db, '_pool_req', return_value=pool), patch.object(db, 'get_settings', return_value=settings), patch.object(db, '_utc_now', return_value=datetime(2026, 9, 26, 22, tzinfo=timezone.utc)):
            result = await db.admin_statistics(7)
        self.assertEqual(len(result['series']), 7)
        self.assertEqual(result['series'][0]['day'], '2026-09-21')
        self.assertEqual(result['series'][-1]['day'], '2026-09-27')
        self.assertEqual(result['series'][1]['payments'], 0)
        self.assertEqual(result['totals']['rub'], 450)
        self.assertEqual(result['totals']['payments'], 3)
        self.assertEqual(result['totals']['stars'], 70)
        self.assertEqual(result['totals']['registered'], 3)
        sql, start, end = pool.fetch.call_args.args
        self.assertEqual(start.astimezone(timezone.utc).isoformat(), '2026-09-20T21:00:00+00:00')
        self.assertIn("status = 'granted'", sql)
        self.assertIn('COALESCE(paid_at, created_at)', sql)
        self.assertIn('at >= $1 AND at < $2', sql)

    async def test_unsupported_period_rejected_before_database(self):
        with patch.object(db, '_pool_req') as pool:
            for days in (0, -7, 9999):
                with self.assertRaises(ValueError):
                    await db.admin_statistics(days)
            pool.assert_not_called()

    async def test_endpoint_authentication_and_period_validation(self):
        from app import admin
        from aiohttp import web
        request = SimpleNamespace(query={'days': 'invalid'})
        with patch.object(admin, '_need_auth', return_value=None), patch.object(db, 'admin_statistics', new_callable=AsyncMock) as fetch:
            response = await admin.api_statistics(request)
            self.assertEqual(response.status, 400)
            fetch.assert_not_called()
        denied = web.json_response({'ok': False}, status=401)
        with patch.object(admin, '_need_auth', return_value=denied), patch.object(db, 'admin_statistics', new_callable=AsyncMock) as fetch:
            response = await admin.api_statistics(request)
            self.assertEqual(response.status, 401)
            fetch.assert_not_called()
