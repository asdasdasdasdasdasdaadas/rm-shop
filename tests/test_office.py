from datetime import datetime, timedelta, timezone
import unittest

from app.office import (
    build_office_payload,
    clip_message,
    effective_state,
    normalize_state,
    resolve_agent_id,
)


class OfficeLogicTest(unittest.TestCase):
    def test_resolve_agent_aliases(self):
        self.assertEqual(resolve_agent_id("monday"), "monday")
        self.assertEqual(resolve_agent_id("Понедельник"), "monday")
        self.assertEqual(resolve_agent_id("продакт"), "product")
        self.assertIsNone(resolve_agent_id("unknown"))

    def test_normalize_state(self):
        self.assertEqual(normalize_state("active"), "busy")
        self.assertEqual(normalize_state("IDLE"), "idle")
        self.assertEqual(normalize_state("offline"), "offline")
        self.assertIsNone(normalize_state("running"))

    def test_clip_message(self):
        self.assertEqual(clip_message("  пишет   фичу  "), "пишет фичу")
        long = "x" * 200
        self.assertEqual(len(clip_message(long)), 160)

    def test_stale_without_row(self):
        state, stale = effective_state(None, 8)
        self.assertEqual(state, "offline")
        self.assertTrue(stale)

    def test_recent_busy_stays_busy(self):
        now = datetime(2026, 9, 13, 20, 0, tzinfo=timezone.utc)
        row = {"state": "busy", "updated_at": now - timedelta(minutes=2)}
        state, stale = effective_state(row, 8, now)
        self.assertEqual(state, "busy")
        self.assertFalse(stale)

    def test_old_update_becomes_offline(self):
        now = datetime(2026, 9, 13, 20, 0, tzinfo=timezone.utc)
        row = {"state": "busy", "updated_at": now - timedelta(minutes=20), "message": "старое"}
        state, stale = effective_state(row, 8, now)
        self.assertEqual(state, "offline")
        self.assertTrue(stale)

    def test_payload_has_fixed_roster(self):
        now = datetime(2026, 9, 13, 20, 0, tzinfo=timezone.utc)
        payload = build_office_payload(
            [
                {
                    "agent_id": "monday",
                    "state": "busy",
                    "message": "пишет кабинет",
                    "updated_at": now,
                }
            ],
            8,
            now,
        )
        ids = [a["id"] for a in payload["agents"]]
        self.assertEqual(ids, ["monday", "friday", "thursday", "product"])
        monday = payload["agents"][0]
        self.assertEqual(monday["state"], "busy")
        self.assertEqual(monday["message"], "пишет кабинет")
        self.assertFalse(monday["stale"])
        self.assertEqual(payload["agents"][1]["state"], "offline")


if __name__ == "__main__":
    unittest.main()
