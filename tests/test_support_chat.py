import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.handlers import tickets


def message(text="Привет"):
    return SimpleNamespace(
        from_user=SimpleNamespace(id=7, is_bot=False, username="u", first_name="U"),
        text=text, caption=None, photo=None, video=None, document=None, animation=None,
        bot=object(), answer=AsyncMock())


class SupportChatTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        tickets._support_until.clear()
        tickets._hinted.clear()
        p = patch.object(tickets, "receive_user_message", AsyncMock())
        self.receive = p.start()
        self.addCleanup(p.stop)

    async def test_random_message_does_not_open_a_ticket(self):
        with patch.object(tickets.db, "has_open_ticket", AsyncMock(return_value=False)):
            msg = message()
            await tickets.ticket_from_chat(msg)
            self.receive.assert_not_awaited()
            self.assertIn("Написать в поддержку", msg.answer.await_args.kwargs["reply_markup"].inline_keyboard[0][0].text)
            again = message("ещё")
            await tickets.ticket_from_chat(again)
            again.answer.assert_not_awaited()  # the hint is not repeated right away

    async def test_after_the_support_button_the_message_goes_to_support(self):
        tickets.open_support(7)
        with patch.object(tickets.db, "has_open_ticket", AsyncMock(return_value=False)):
            await tickets.ticket_from_chat(message("Не работает VPN"))
        self.assertEqual(self.receive.await_args.kwargs["body"], "Не работает VPN")

    async def test_an_open_ticket_keeps_the_conversation(self):
        with patch.object(tickets.db, "has_open_ticket", AsyncMock(return_value=True)):
            await tickets.ticket_from_chat(message("Спасибо, помогло"))
        self.receive.assert_awaited_once()

    async def test_cancel_closes_support_mode(self):
        tickets.open_support(7)
        tickets.close_support(7)
        self.assertFalse(tickets.support_open(7))


if __name__ == "__main__":
    unittest.main()
