"""Broadcasts for conversion: segments, a test share first, then «остальным» without repeats."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import admin, db


class SegmentSqlTest(unittest.TestCase):
    def test_every_segment_builds_sql_with_the_price(self):
        for name in db.BROADCAST_SEGMENTS:
            sql = db._segment_sql(name)
            self.assertNotIn("{price}", sql)
        self.assertIn("$1::int", db._segment_sql("low_balance"))
        self.assertIn("$1::int", db._segment_sql("zero_off"))

    def test_unknown_segment_is_refused(self):
        with self.assertRaises(ValueError):
            db._segment_sql("everyone_ever")


class CheckTest(unittest.TestCase):
    def test_segment_and_test_share_pass(self):
        spec, error = admin._check_broadcast({"text": "Привет", "audience": "zero_off", "sample": 10})
        self.assertIsNone(error)
        self.assertEqual((spec["audience"], spec["sample"]), ("zero_off", 10))

    def test_bad_share_and_audience_are_refused(self):
        self.assertIsNotNone(admin._check_broadcast({"text": "x", "sample": 95})[1])
        self.assertIsNotNone(admin._check_broadcast({"text": "x", "audience": "nobody"})[1])


class PickTest(unittest.IsolatedAsyncioTestCase):
    async def test_share_is_a_random_tenth(self):
        with patch.object(db, "list_broadcast_ids", AsyncMock(return_value=list(range(1, 101)))):
            ids = await admin._broadcast_ids({"audience": "using", "template": "", "sample": 10})
        self.assertEqual(len(ids), 10)
        self.assertTrue(set(ids) <= set(range(1, 101)))

    async def test_rest_skips_who_got_the_test(self):
        with patch.object(db, "list_broadcast_ids", AsyncMock(return_value=[1, 2, 3, 4])), \
                patch.object(db, "broadcast_run_recipients", AsyncMock(return_value={2, 4})):
            self.assertEqual(await admin._broadcast_ids({"audience": "using", "template": "", "parent": 7}), [1, 3])

    async def test_plain_broadcast_keeps_its_usual_audience(self):
        self.assertIsNone(await admin._broadcast_ids({"audience": "all", "template": ""}))

    async def test_rest_only_once_and_only_after_a_test(self):
        run = {"id": 7, "spec": json.dumps({"audience": "using", "template": "", "text": "hi", "sample": 10})}
        with patch.object(db, "get_broadcast_run", AsyncMock(return_value=run)), \
                patch.object(db, "broadcast_child_exists", AsyncMock(return_value=False)):
            spec, error = await admin._rest_spec(7)
        self.assertIsNone(error)
        self.assertEqual(spec, {"audience": "using", "template": "", "text": "hi", "parent": 7})
        with patch.object(db, "get_broadcast_run", AsyncMock(return_value=run)), \
                patch.object(db, "broadcast_child_exists", AsyncMock(return_value=True)):
            self.assertEqual((await admin._rest_spec(7))[1], "Остальным уже отправлено")
        plain = {"id": 8, "spec": "{}"}
        with patch.object(db, "get_broadcast_run", AsyncMock(return_value=plain)):
            self.assertEqual((await admin._rest_spec(8))[1], "Это не тестовая рассылка")


class LaunchTest(unittest.IsolatedAsyncioTestCase):
    async def test_test_share_starts_with_picked_ids_and_remembers_the_spec(self):
        app = {}
        started = {}

        def start(app_, text, ids, template, media, spec):
            started.update(text=text, ids=ids, template=template, spec=spec)
            return {"running": True}

        with patch.object(admin, "_broadcast_ids", AsyncMock(return_value=[5, 9])), \
                patch.object(admin, "_bc_job", return_value={}), \
                patch.object(admin, "_start_broadcast_job", side_effect=start):
            payload, status = await admin._launch_broadcast(app, {"text": "Пополните", "audience": "low_balance", "sample": 10})
        self.assertEqual(status, 200)
        self.assertEqual(started["ids"], [5, 9])
        self.assertEqual(started["spec"]["sample"], 10)
        self.assertEqual(started["spec"]["audience"], "low_balance")


if __name__ == "__main__":
    unittest.main()
