"""Blocking from the admin panel is total: devices deleted (panel and here), panel keys off, out of the channel,
the bot writes nothing and answers nothing; unblocking lets them back into the channel."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.methods import BanChatMember, GetChat, SendMessage
from aiogram.types import Chat, Message, User

from app import admin, block
from app.remnawave import RemnawaveError

SETTINGS = SimpleNamespace(admin_id_set={1}, required_channel_id="-1001")


class ApplyBlockTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = SimpleNamespace(
            get_user=AsyncMock(return_value={"telegram_id": 7}),
            set_user_blocked=AsyncMock(),
            list_devices=AsyncMock(return_value=[{"id": 11, "remnawave_id": 101, "title": "iPhone"},
                                                 {"id": 12, "remnawave_id": 102, "title": "Mac"},
                                                 {"id": 13, "remnawave_id": None, "title": "TV"}]),
            delete_device=AsyncMock(return_value={"id": 1}),
            log_billing_event=AsyncMock(),
            list_panel_ids_for_user=AsyncMock(return_value=[100, 102]),
            clear_device_billing=AsyncMock(), clear_device_ips=AsyncMock(),
            refund_sharing_penalty=AsyncMock(return_value=(0, 0)),
        )
        for p in (patch.object(admin, "db", self.db), patch.object(admin, "get_settings", return_value=SETTINGS)):
            p.start()
            self.addCleanup(p.stop)
        self.rw = SimpleNamespace(delete_panel_user=AsyncMock(), disable_panel_user=AsyncMock())
        self.bot = SimpleNamespace(ban_chat_member=AsyncMock(), unban_chat_member=AsyncMock(), send_message=AsyncMock())

    async def test_block_deletes_devices_disables_keys_and_bans_from_channel(self):
        self.rw.delete_panel_user.side_effect = [None, RemnawaveError("down")]
        self.assertEqual(await admin._apply_block(self.rw, 7, True, "спам", self.bot), "ok")
        self.db.set_user_blocked.assert_awaited_once_with(7, True, "спам")
        self.assertEqual([c.args[0] for c in self.rw.delete_panel_user.await_args_list], [101, 102])
        # the device the panel refused to delete stays here and is switched off with the main key
        self.assertEqual([c.args[1] for c in self.db.delete_device.await_args_list], [11, 13])
        self.assertEqual([c.args[0] for c in self.rw.disable_panel_user.await_args_list], [100, 102])
        self.bot.ban_chat_member.assert_awaited_once_with("-1001", 7)
        self.bot.send_message.assert_not_awaited()

    async def test_unblock_lifts_the_channel_ban(self):
        await admin._apply_block(self.rw, 7, False, bot=self.bot)
        self.bot.unban_chat_member.assert_awaited_once_with("-1001", 7, only_if_banned=True)
        self.db.delete_device.assert_not_awaited()

    async def test_admin_is_never_blocked(self):
        self.assertEqual(await admin._apply_block(self.rw, 1, True, bot=self.bot), "skipped")
        self.db.set_user_blocked.assert_not_awaited()


class SilenceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.blocked = {7}
        for p in (patch.object(block.db, "user_is_blocked", new=AsyncMock(side_effect=lambda t: t in self.blocked)),
                  patch.object(block, "get_settings", return_value=SETTINGS)):
            p.start()
            self.addCleanup(p.stop)
        self.sent = AsyncMock(return_value="sent")
        self.mw = block.BlockedRequestMiddleware()

    async def test_nothing_goes_out_to_a_blocked_person(self):
        with self.assertRaises(block.BlockedByAdmin):
            await self.mw(self.sent, None, SendMessage(chat_id=7, text="рассылка"))
        self.sent.assert_not_awaited()
        self.assertEqual(await self.mw(self.sent, None, SendMessage(chat_id=8, text="ok")), "sent")
        self.assertEqual(await self.mw(self.sent, None, GetChat(chat_id=7)), "sent")
        self.assertEqual(await self.mw(self.sent, None, BanChatMember(chat_id=-1001, user_id=7)), "sent")

    async def test_sharing_notice_may_still_go_out(self):
        async def send(chat_id, text, **_):
            return await self.mw(self.sent, None, SendMessage(chat_id=chat_id, text=text))
        block._last_sent_at.clear()
        with patch.object(block, "blocked_notice", return_value="Доступ ограничен"), \
                patch.object(block, "blocked_keyboard", return_value=None):
            await block.notify_blocked(SimpleNamespace(send_message=send), 7)
        self.sent.assert_awaited_once()

    async def test_incoming_messages_are_dropped_silently(self):
        handler = AsyncMock()
        msg = Message(message_id=1, date=0, chat=Chat(id=7, type="private"),
                      from_user=User(id=7, is_bot=False, first_name="x"), text="помогите")
        self.assertIsNone(await block.BlockedMiddleware()(handler, msg, {"bot": object()}))
        handler.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
