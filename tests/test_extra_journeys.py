import unittest
from unittest.mock import AsyncMock, patch

from app import extra_journeys, funnel_board, experiments


class ExtraJourneys(unittest.IsolatedAsyncioTestCase):
    async def test_branches_are_built_in_and_testable(self):
        with patch.object(funnel_board, "_flag", AsyncMock(return_value=True)):
            graph = await funnel_board.default_graph()
        ids = {s["id"] for s in experiments.testable_steps(graph)}
        for sid in ("checkout-again-1", "gift-ending-1", "upsell-device-1", "upsell-month-1"):
            self.assertIn(sid, ids)
        self.assertEqual(len(extra_journeys.upgrade(graph)["branches"]), len(graph["branches"]))  # no duplicates

    def test_conditions_and_kinds(self):
        for c in extra_journeys.CONDITIONS:
            self.assertIn(c["id"], funnel_board.CONDITION_IDS)
            self.assertTrue(extra_journeys.KINDS[c["id"]].startswith("nudge_"))  # daily and weekly caps apply
        self.assertIn("checkout_again", extra_journeys.CYCLE)

    def test_texts_render(self):
        month = funnel_board.render_text(extra_journeys.UPSELL_MONTH_TEXT, 1, "A")
        self.assertNotIn("{", month)
        self.assertNotIn("{", funnel_board.render_text(extra_journeys.GIFT_ENDING_TEXT, 1, "A"))
        self.assertNotIn("{", funnel_board.render_text(extra_journeys.UPSELL_DEVICE_TEXT, 1, "A"))


if __name__ == "__main__":
    unittest.main()
