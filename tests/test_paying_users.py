import sqlite3
import unittest
from app.db import _PAYING_USERS_SQL

class PayingUsersTest(unittest.TestCase):
    def test_first_payment_only_across_providers_and_moscow_day(self):
        connection = sqlite3.connect(':memory:')
        self.addCleanup(connection.close)
        connection.executescript('''
        CREATE TABLE payments(telegram_id INTEGER, created_at TEXT);
        CREATE TABLE rollypay_orders(telegram_id INTEGER, created_at TEXT, paid_at TEXT, status TEXT);
        INSERT INTO payments VALUES (1,'2026-10-20 10:00:00'), (2,'2026-10-24 21:00:00');
        INSERT INTO rollypay_orders VALUES
        (1,'2026-10-25 10:00:00','2026-10-25 10:00:00','granted'),
        (2,'2026-10-25 10:00:00','2026-10-25 10:00:00','granted'),
        (3,'2026-10-24 19:00:00','2026-10-24 23:00:00','granted'),
        (4,'2026-10-25 10:00:00',NULL,'pending'),
        (5,'2026-10-24 20:59:59',NULL,'granted');
        ''')
        sql = _PAYING_USERS_SQL.replace("($1::timestamptz AT TIME ZONE 'Europe/Moscow')::date\n                                  AT TIME ZONE 'Europe/Moscow'", ':midnight').replace('$1::timestamptz', ':now').replace('::int','')
        self.assertEqual(connection.execute(sql, {'midnight':'2026-10-24 21:00:00','now':'2026-10-25 13:00:00'}).fetchone(), (4,2))
        connection.execute('DELETE FROM payments')
        connection.execute('DELETE FROM rollypay_orders')
        self.assertEqual(connection.execute(sql, {'midnight':'2026-10-24 21:00:00','now':'2026-10-25 13:00:00'}).fetchone(), (0,0))
