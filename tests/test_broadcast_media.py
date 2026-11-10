import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import admin, broadcast_media as bm, db

GIF = b"GIF89a" + b"\x00" * 20
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 20
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20


class MediaDirTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        p = patch.object(bm, "MEDIA_DIR", Path(tmp.name))
        p.start()
        self.addCleanup(p.stop)


class StoreTest(MediaDirTest):
    def test_kind_follows_the_file(self):
        self.assertEqual(bm.store(PNG, "a.png")["kind"], "photo")
        self.assertEqual(bm.store(GIF, "a.gif")["kind"], "animation")
        self.assertEqual(bm.store(MP4, "a.mp4")["kind"], "video")
        self.assertEqual(bm.store(MP4, "a.mp4", as_gif=True)["kind"], "animation")

    def test_rejects_other_files_and_paths(self):
        with self.assertRaises(ValueError):
            bm.store(b"%PDF-1.4", "a.pdf")
        self.assertIsNone(bm.path_of("../../.env"))
        self.assertEqual(bm.check({"id": "0" * 32 + ".gif", "kind": "animation"})[1],
                         "Файл рассылки не найден, загрузите его снова")

    def test_picture_cannot_pretend_to_be_a_video(self):
        media = bm.store(PNG, "a.png")
        self.assertEqual(bm.check({"id": media["id"], "kind": "video"})[1], "Картинку можно отправить только как фото")
        self.assertEqual(bm.check({"id": media["id"], "kind": "photo"}), ({"id": media["id"], "kind": "photo"}, None))


class SendTest(MediaDirTest):
    async def _send(self, media, bot, cache):
        return await bm.send(bot, 5, media, "Новый дизайн", None, cache)

    def test_uploads_once_then_reuses_the_file_id(self):
        import asyncio
        media = bm.store(GIF, "teaser.gif")
        bot = SimpleNamespace(send_animation=AsyncMock(return_value=SimpleNamespace(animation=SimpleNamespace(file_id="F1"))))
        cache = {}
        asyncio.run(self._send(media, bot, cache))
        asyncio.run(self._send(media, bot, cache))
        first, second = bot.send_animation.await_args_list
        self.assertEqual(type(first.args[1]).__name__, "FSInputFile")
        self.assertEqual(second.args[1], "F1")
        self.assertEqual(second.kwargs["caption"], "Новый дизайн")


class BroadcastApiTest(MediaDirTest):
    def test_media_only_with_a_custom_message_and_a_short_caption(self):
        media = bm.store(PNG, "a.png")
        ref = {"id": media["id"], "kind": "photo"}
        with patch.object(admin, "get_settings", return_value=SimpleNamespace(referral_program_enabled=True)):
            spec, error = admin._check_broadcast({"text": "", "media": ref})
            self.assertIsNone(error)
            self.assertEqual(spec["media"], ref)
            self.assertIn("только к своему", admin._check_broadcast({"template": "gift3", "media": ref})[1])
            self.assertIn("не длиннее", admin._check_broadcast({"text": "я" * 1000, "media": ref})[1])
            self.assertEqual(admin._check_broadcast({"text": ""})[1], "Пустой текст")


class DeliveryTest(unittest.IsolatedAsyncioTestCase):
    async def test_broadcast_passes_media_and_logs_its_kind(self):
        job = {"running": True, "media": {"id": "x.gif", "kind": "animation"}}
        with patch.object(db, "notification_allowed", AsyncMock(return_value=True)), \
                patch.object(db, "reserve_optional_message", AsyncMock(return_value=1)), \
                patch.object(db, "finish_optional_message", AsyncMock()), \
                patch.object(db, "log_bot_message", AsyncMock()) as log, \
                patch.object(admin, "get_settings"), \
                patch.object(admin, "_deliver_broadcast", AsyncMock(return_value=SimpleNamespace(message_id=1))) as send, \
                patch.object(admin.asyncio, "sleep", AsyncMock()):
            await admin._broadcast_all(None, "Новый дизайн", job, [1, 2])
        self.assertEqual(send.await_count, 2)
        self.assertEqual(send.await_args.kwargs["media"], job["media"])
        self.assertIs(send.await_args_list[0].kwargs["cache"], send.await_args_list[1].kwargs["cache"])
        self.assertEqual(log.await_args.kwargs["extra"]["media"], "animation")


if __name__ == "__main__":
    unittest.main()
