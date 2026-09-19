"""Schema initialization must preserve SQL comments and quoted semicolons."""
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app import db


class SchemaInitTest(unittest.IsolatedAsyncioTestCase):
    async def test_script_with_semicolons_in_comments_and_strings(self):
        script = """
            CREATE TABLE users (id INTEGER PRIMARY KEY, note TEXT, bot_started_at TEXT);
            -- Only the /start handler claims this marker; Web App registration does not.
            INSERT INTO users (id, note) VALUES (1, 'gift; pending');
            UPDATE users SET bot_started_at = 'started' WHERE id = 1;
        """
        connection = sqlite3.connect(':memory:')
        self.addCleanup(connection.close)
        sql = SimpleNamespace(execute=AsyncMock(side_effect=connection.executescript))
        pool = MagicMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=sql)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        settings = SimpleNamespace(database_url='unused', billing_concurrency=1)
        with patch.object(db, '_pool', None), \
             patch.object(db, 'get_settings', return_value=settings), \
             patch.object(db.asyncpg, 'create_pool', AsyncMock(return_value=pool)), \
             patch.object(db, 'SCHEMA_PATH') as path, \
             patch.object(db, '_ensure_nudge_defaults', AsyncMock()) as defaults:
            path.read_text.return_value = script
            await db.init_db()
            self.assertEqual(connection.execute('SELECT note, bot_started_at FROM users').fetchone(),
                             ('gift; pending', 'started'))
            defaults.assert_awaited_once()
