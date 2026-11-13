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
        self.assertEqual(data, {"ok": True, "title": "Телефон мамы", "icon": "👵", "client": ""})
        rename.assert_awaited_once_with(42, 5, "Телефон мамы", "👵", None)

    async def test_without_icon_keeps_the_old_one(self):
        _, _, rename = await self.call({"title": "Рабочий"})
        rename.assert_awaited_once_with(42, 5, "Рабочий", None, None)

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


class DeviceAppTest(unittest.IsolatedAsyncioTestCase):
    """The VPN app the customer uses on a device: «Открыть» must go there, not to the recommended one."""

    async def call(self, body):
        rename = AsyncMock(return_value={"id": 5, "title": "Мой iPhone", "icon": "", "client": "happ"})
        with patch.object(web, "_require_tg", AsyncMock(return_value=(42, None))), patch.object(db, "rename_device", rename):
            res = await web.api_rename_device(FakeRequest(5, body))
        return res.status, json.loads(res.text), rename

    async def test_app_alone_changes_only_the_app(self):
        status, data, rename = await self.call({"client": "Happ"})
        self.assertEqual(status, 200)
        self.assertEqual(data["client"], "happ")
        rename.assert_awaited_once_with(42, 5, None, None, "happ")

    async def test_own_app_without_a_link_is_allowed(self):
        _, _, rename = await self.call({"client": "other"})
        rename.assert_awaited_once_with(42, 5, None, None, "other")

    async def test_junk_app_id_is_refused(self):
        status, _, rename = await self.call({"client": "<script>"})
        self.assertEqual(status, 400)
        rename.assert_not_awaited()

    async def test_nothing_to_save_is_refused(self):
        status, _, rename = await self.call({})
        self.assertEqual(status, 400)
        rename.assert_not_awaited()

    def test_client_id_cleaning(self):
        self.assertEqual(web.clean_client_id(" V2RayNG "), "v2rayng")
        self.assertEqual(web.clean_client_id("a" * 40), "")
        self.assertEqual(web.clean_client_id(None), "")


class RenameQueryTest(unittest.IsolatedAsyncioTestCase):
    async def test_update_is_limited_to_the_owner(self):
        pool = SimpleNamespace(fetchrow=AsyncMock(return_value=None))
        with patch.object(db, "_pool_req", return_value=pool):
            self.assertIsNone(await db.rename_device(42, 5, "Рабочий"))
        sql, *args = pool.fetchrow.await_args.args
        self.assertIn("WHERE id = $1 AND telegram_id = $2", sql)
        self.assertIn("COALESCE($4, icon)", sql)
        self.assertIn("COALESCE($5, client)", sql)
        self.assertEqual(args, [5, 42, "Рабочий", None, None])


class NewDeviceAppTest(unittest.IsolatedAsyncioTestCase):
    async def test_app_picked_in_the_wizard_is_saved_with_the_device(self):
        rw = SimpleNamespace(create_user=AsyncMock(return_value={"id": 9, "subscriptionUrl": "https://sub.test/9"}))
        request = SimpleNamespace(app={"rw": rw}, json=AsyncMock(return_value={"platform": "ios", "title": "Мой iPhone", "client": "happ"}))
        settings = SimpleNamespace(max_devices=6, vpn_day_price_rub=6, remnawave_hwid_limit=1)
        add = AsyncMock(return_value={"id": 3})
        with patch.object(web, "_if_down", AsyncMock(return_value=None)), \
                patch.object(web, "_require_tg", AsyncMock(return_value=(7, None))), \
                patch.object(web, "get_settings", return_value=settings), \
                patch.object(db, "billable_device_count", AsyncMock(return_value=0)), \
                patch.object(db, "get_user", AsyncMock(return_value={"trial_waiting_connection": True})), \
                patch.object(db, "list_devices", AsyncMock(return_value=[])), \
                patch.object(db, "spend_balance_rub", AsyncMock()), \
                patch.object(db, "add_balance_rub", AsyncMock()), \
                patch.object(db, "add_device", add), \
                patch.object(db, "save_device_subscription", AsyncMock()), \
                patch.object(db, "mark_first_device_thanks_pending", AsyncMock()):
            response = await web._api_add_device_locked(request)
        self.assertEqual(response.status, 200)
        self.assertEqual(add.await_args.args[3:], ("ios", "happ"))


if __name__ == "__main__":
    unittest.main()
