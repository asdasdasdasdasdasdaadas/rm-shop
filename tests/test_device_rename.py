"""The customer names a device in the cabinet: the name is cleaned, the icon checked, only their own device changes."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import db, web


class FakeRequest:
    def __init__(self, device_id, body):
        self.match_info = {"device_id": str(device_id)}
        self._body = body

    async def json(self):
        return self._body


class CleanTitleTest(unittest.TestCase):
    def test_spaces_newlines_and_invisible_characters_go(self):
        self.assertEqual(web.clean_device_title("  Телефон\n  мамы​ "), "Телефон мамы")

    def test_long_name_is_cut(self):
        self.assertEqual(len(web.clean_device_title("я" * 100)), web.DEVICE_TITLE_MAX)

    def test_nothing_is_empty(self):
        self.assertEqual(web.clean_device_title(None), "")
        self.assertEqual(web.clean_device_title("​ \t"), "")


class RenameApiTest(unittest.IsolatedAsyncioTestCase):
    async def call(self, body, row={"id": 5, "title": "Телефон мамы", "icon": "👵"}, device_id=5):
        rename = AsyncMock(return_value=row)
        with patch.object(web, "_require_tg", AsyncMock(return_value=(42, None))), patch.object(db, "rename_device", rename):
            res = await web.api_rename_device(FakeRequest(device_id, body))
        return res.status, json.loads(res.text), rename

    async def test_saves_the_cleaned_name_and_icon(self):
        status, data, rename = await self.call({"title": " Телефон  мамы ", "icon": "👵"})
        self.assertEqual(status, 200)
        self.assertEqual(data, {"ok": True, "title": "Телефон мамы", "icon": "👵"})
        rename.assert_awaited_once_with(42, 5, "Телефон мамы", "👵")

    async def test_without_icon_keeps_the_old_one(self):
        _, _, rename = await self.call({"title": "Рабочий"})
        rename.assert_awaited_once_with(42, 5, "Рабочий", None)

    async def test_empty_name_is_refused(self):
        status, data, rename = await self.call({"title": "   "})
        self.assertEqual((status, data["ok"]), (400, False))
        rename.assert_not_awaited()

    async def test_unknown_icon_is_refused(self):
        status, _, rename = await self.call({"title": "Рабочий", "icon": "💣"})
        self.assertEqual(status, 400)
        rename.assert_not_awaited()

    async def test_someone_elses_device_is_not_found(self):
        status, _, _ = await self.call({"title": "Рабочий"}, row=None)
        self.assertEqual(status, 404)

    async def test_not_an_object_body_is_refused(self):
        status, _, rename = await self.call(["Рабочий"])
        self.assertEqual(status, 400)
        rename.assert_not_awaited()


class RenameQueryTest(unittest.IsolatedAsyncioTestCase):
    async def test_update_is_limited_to_the_owner(self):
        pool = SimpleNamespace(fetchrow=AsyncMock(return_value=None))
        with patch.object(db, "_pool_req", return_value=pool):
            self.assertIsNone(await db.rename_device(42, 5, "Рабочий"))
        sql, *args = pool.fetchrow.await_args.args
        self.assertIn("WHERE id = $1 AND telegram_id = $2", sql)
        self.assertIn("COALESCE($4, icon)", sql)
        self.assertEqual(args, [5, 42, "Рабочий", None])


if __name__ == "__main__":
    unittest.main()
