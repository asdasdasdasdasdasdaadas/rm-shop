import asyncio
import unittest
from unittest.mock import patch

from app import funnel_board as fb
from app import shop_config
from app.config import get_settings, set_shop_overlay, shop_overlay


class ReferralNudges(unittest.TestCase):
    def test_conditions_are_known_and_repeat_per_reason(self):
        for cid in ("invite_silent", "friend_stuck", "friend_rewarded"):
            self.assertIn(cid, fb.CONDITION_IDS)
            self.assertEqual(fb.CONDITION_IDS[cid]["gate"], "referral")
        self.assertEqual(fb.REFERRAL_CYCLE, {"friend_stuck", "friend_rewarded"})

    def test_board_has_the_follow_ups(self):
        async def flag(*a, **k):
            return True
        with patch.object(fb, "_flag", flag):
            graph = asyncio.run(fb.default_graph())
        steps = {s["id"]: (b["id"], s) for b in graph["branches"] for s in b["steps"]}
        self.assertEqual(steps["invite-2"][0], "friends")
        self.assertEqual(steps["invite-2"][1]["wait_from"], "previous")
        self.assertEqual(steps["friend-stuck-1"][1]["condition"], "friend_stuck")
        self.assertEqual(steps["invite-more-1"][1]["condition"], "friend_rewarded")
        for sid in ("invite-2", "invite-more-1"):
            self.assertIn("{link}", steps[sid][1]["text"])


class WidgetsSwitch(unittest.TestCase):
    def setUp(self):
        self.saved = shop_overlay()

    def tearDown(self):
        set_shop_overlay(self.saved)

    def test_on_by_default_and_switchable(self):
        self.assertTrue(get_settings().widgets_enabled)
        set_shop_overlay({**self.saved, "widgets_enabled": False})
        self.assertFalse(get_settings().widgets_enabled)

    def test_snapshot_shows_the_switch(self):
        set_shop_overlay({**self.saved, "widgets_enabled": False})
        with patch.object(shop_config, "admin_pay_methods", return_value=[]):
            self.assertIs(shop_config.snapshot()["values"]["widgets_enabled"], False)


if __name__ == "__main__":
    unittest.main()
