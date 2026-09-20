import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import db


class AdminTrafficTest(unittest.IsolatedAsyncioTestCase):
    def test_totals_filter_and_sort_across_devices(self):
        conn = sqlite3.connect(':memory:')
        self.addCleanup(conn.close)
        conn.create_function('GREATEST', -1, max)
        conn.executescript('''CREATE TABLE users (telegram_id INTEGER, used_traffic_bytes INTEGER, lifetime_traffic_bytes INTEGER);
            CREATE TABLE devices (telegram_id INTEGER, used_traffic_bytes INTEGER, lifetime_traffic_bytes INTEGER);''')
        gb = 1024 ** 3
        conn.executemany('INSERT INTO users VALUES (?,?,?)', [(1,0,0),(2,gb*9,gb*10),(3,0,0),(4,0,0)])
        conn.executemany('INSERT INTO devices VALUES (?,?,?)', [(1,gb,gb*3),(1,gb*5,gb*4),(2,gb*2,gb*4),(4,gb,gb)])
        where,args = db._admin_users_filter('', {'traffic_min':'1.5','traffic_max':'10'})
        args = {str(i): value for i, value in enumerate(args, 1)}
        sql = f'SELECT u.telegram_id, {db._ADMIN_TRAFFIC_SQL} AS traffic_total_bytes FROM users u {where} ORDER BY {db._admin_users_order({"sort":"traffic_desc"})} LIMIT 1 OFFSET 1'
        self.assertEqual(conn.execute(sql, args).fetchall(), [(1,gb*8)])
        # User-level counters are a fallback, never added to the same device counters twice.
        self.assertEqual(conn.execute(sql.replace('LIMIT 1 OFFSET 1',''),args).fetchall(), [(2,gb*10),(1,gb*8)])

    def test_online_inactivity_uses_latest_device_and_sort_is_allowlisted(self):
        where,args = db._admin_users_filter('', {'online':'inactive_7d'})
        self.assertIn('MAX(d0.last_online_at)',where)
        self.assertIn('< NOW()',where)
        self.assertEqual(args,[7])
        self.assertEqual(db._admin_users_order({'sort':'online_asc'}), 'last_online_at ASC NULLS LAST, u.telegram_id DESC')
        self.assertEqual(db._admin_users_order({'sort':'DROP TABLE users'}), db._admin_users_order())
        where,args = db._admin_users_filter('', {'traffic_min':'1,5'})
        self.assertEqual(args,[int(1.5*1024**3)])
        self.assertNotIn('1,5',where)

    async def test_list_sorts_before_pagination_and_returns_display_total(self):
        pool = SimpleNamespace(fetchval=AsyncMock(return_value=1), fetch=AsyncMock(return_value=[
            {'telegram_id':1,'used_traffic_bytes':0,'traffic_total_bytes':123,'paid_plan_codes':[]}]))
        with patch.object(db,'_pool_req',return_value=pool), patch.object(db,'get_settings'):
            items,total = await db.admin_list_users('',30,60,{'sort':'traffic_desc'})
        sql,*args = pool.fetch.call_args.args
        self.assertIn('ORDER BY traffic_total_bytes DESC, u.telegram_id DESC',sql)
        self.assertLess(sql.index('ORDER BY traffic_total_bytes'),sql.index('LIMIT $'))
        self.assertEqual(args,[30,60])
        self.assertEqual(items[0]['used_traffic_bytes'],123)
        self.assertEqual(total,1)
