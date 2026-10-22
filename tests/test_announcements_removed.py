"""Regression coverage for retired announcements without external services."""
import ast
import asyncio
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]


class AnnouncementsRemovedTest(unittest.TestCase):
    def test_retired_api_and_ui_are_absent(self):
        for filename in ('app/admin.py', 'app/web.py'):
            source = (ROOT / filename).read_text()
            self.assertNotIn('/api/announcements', source)
            self.assertNotIn('app.announcements', source)
        self.assertNotIn('latest_update_announcement', (ROOT / 'app/web.py').read_text())
        for filename in ('webapp/app.js', 'webapp/index.html'):
            source = (ROOT / filename).read_text()
            self.assertNotIn('updateNotice', source)
            self.assertNotIn('view-article', source)

    def test_regular_broadcast_delivery_still_sends_text(self):
        tree = ast.parse((ROOT / 'app/admin.py').read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == '_deliver_broadcast')
        # Exercise the actual delivery function without importing service dependencies.
        module = ast.Module(body=[fn], type_ignores=[])
        namespace = {'Bot': object}
        exec(compile(module, 'app/admin.py', 'exec'), namespace)
        funnel = ModuleType('app.funnel_ui')
        funnel.funnel_body = lambda body: body
        funnel.funnel_keyboard = lambda markup: markup
        bot = AsyncMock()
        with patch.dict(sys.modules, {'app.funnel_ui': funnel}):
            asyncio.run(namespace['_deliver_broadcast'](bot, 123, 'Сообщение', None))
        bot.send_message.assert_awaited_once_with(123, 'Сообщение', reply_markup=None)
        bot.send_photo.assert_not_called()
