import unittest

from app import experiments as ex


STEPS = {
    "unpaid-1": {"id": "unpaid-1", "text": "Пополните баланс", "gift": False},
    "recovery-recover-payment-3": {"id": "recovery-recover-payment-3", "text": "Дарим {gift_days}", "gift": True},
}


class Arms(unittest.TestCase):
    def test_arm_is_stable_and_shares_hold(self):
        exp = {"id": 7, "holdout_pct": 20, "b_pct": 50}
        arms = [ex.arm_for(exp, uid) for uid in range(1, 20001)]
        self.assertEqual(arms, [ex.arm_for(exp, uid) for uid in range(1, 20001)])
        control = arms.count("control") / len(arms)
        self.assertAlmostEqual(control, 0.2, delta=0.015)
        rest = [a for a in arms if a != "control"]
        self.assertAlmostEqual(rest.count("b") / len(rest), 0.5, delta=0.015)

    def test_new_test_reshuffles(self):
        a = [ex.arm_for({"id": 1, "holdout_pct": 50, "b_pct": 0}, uid) for uid in range(1000)]
        b = [ex.arm_for({"id": 2, "holdout_pct": 50, "b_pct": 0}, uid) for uid in range(1000)]
        self.assertNotEqual(a, b)

    def test_holdout_only_has_no_b(self):
        exp = {"id": 3, "holdout_pct": 10, "b_pct": 0}
        self.assertNotIn("b", {ex.arm_for(exp, uid) for uid in range(5000)})

    def test_variant_only_for_b(self):
        step = {"text": "A"}
        exp = {"b_text": "B", "b_gift_days": 5}
        self.assertEqual(ex.variant(step, exp, "a"), ("A", None))
        self.assertEqual(ex.variant(step, exp, "b"), ("B", 5))
        self.assertEqual(ex.variant(step, {"b_text": None, "b_gift_days": 5}, "b"), ("A", 5))
        self.assertEqual(ex.variant(step, None, "b"), ("A", None))


class Check(unittest.TestCase):
    def test_holdout_alone(self):
        got = ex.check({"step_id": "unpaid-1", "holdout_pct": 20}, STEPS)
        self.assertEqual((got["holdout_pct"], got["b_pct"], got["b_text"]), (20, 0, None))

    def test_text_variant(self):
        got = ex.check({"step_id": "unpaid-1", "b_pct": 50, "b_text": " Новый текст "}, STEPS)
        self.assertEqual(got["b_text"], "Новый текст")

    def test_rejects(self):
        for body, needle in [
            ({"step_id": "nope", "holdout_pct": 10}, "из списка"),
            ({"step_id": "unpaid-1"}, "Нечего сравнивать"),
            ({"step_id": "unpaid-1", "holdout_pct": 60}, "от 0 до 50"),
            ({"step_id": "unpaid-1", "b_pct": 50}, "напишите текст"),
            ({"step_id": "unpaid-1", "b_text": "Другой"}, "какой доле"),
            ({"step_id": "unpaid-1", "b_pct": 50, "b_text": "Пополните баланс"}, "совпадает"),
            ({"step_id": "unpaid-1", "b_pct": 50, "b_gift_days": 5}, "нет подарка"),
            ({"step_id": "recovery-recover-payment-3", "b_pct": 50, "b_gift_days": 30}, "от 1 до 14"),
            ({"step_id": "unpaid-1", "holdout_pct": True}, "целое"),
        ]:
            with self.subTest(body=body), self.assertRaises(ValueError) as caught:
                ex.check(body, STEPS)
            self.assertIn(needle, str(caught.exception))

    def test_gift_offer(self):
        got = ex.check({"step_id": "recovery-recover-payment-3", "b_pct": 50, "b_gift_days": "5"}, STEPS)
        self.assertEqual(got["b_gift_days"], 5)


class Stats(unittest.TestCase):
    def test_p_value(self):
        self.assertLess(ex.p_value(100, 1000, 50, 1000), 0.001)
        self.assertGreater(ex.p_value(10, 100, 9, 100), 0.5)
        self.assertIsNone(ex.p_value(0, 0, 1, 10))
        self.assertEqual(ex.p_value(0, 10, 0, 10), 1.0)

    def test_compare_verdicts(self):
        arm = {"users": 1000, "payers": 100, "rub": 30000}
        base = {"users": 1000, "payers": 50, "rub": 15000}
        got = ex.compare(arm, base, "control")
        self.assertTrue(got["sure"])
        self.assertEqual(got["payers_pp"], 5.0)
        self.assertEqual(got["rub_per_100"], 1500)
        self.assertIn("Лучше", got["verdict"])
        small = ex.compare({"users": 20, "payers": 3, "rub": 900}, {"users": 20, "payers": 2, "rub": 600}, "a")
        self.assertFalse(small["sure"])
        self.assertIn("нужно хотя бы", small["verdict"])
        tiny = ex.compare({"users": 11, "payers": 0, "rub": 0}, {"users": 2, "payers": 1, "rub": 100}, "control")
        self.assertFalse(tiny["sure"])
        same = ex.compare({"users": 5000, "payers": 500, "rub": 1}, {"users": 5000, "payers": 502, "rub": 1}, "a")
        self.assertIn("Разницы не видно", same["verdict"])


class Steps(unittest.IsolatedAsyncioTestCase):
    async def test_money_warnings_are_not_testable(self):
        from unittest.mock import AsyncMock, patch
        from app import funnel_board
        with patch.object(funnel_board, "_flag", AsyncMock(return_value=True)):
            graph = await funnel_board.default_graph()
        ids = {s["id"] for s in ex.testable_steps(graph)}
        self.assertNotIn("pay-1", ids)
        self.assertNotIn("balance-1", ids)
        self.assertIn("recovery-recover-payment-1", ids)
        gifts = [s for s in ex.testable_steps(graph) if s["gift"]]
        self.assertTrue(gifts)


if __name__ == "__main__":
    unittest.main()


class BroadcastAB(unittest.TestCase):
    def test_check_keeps_and_refuses(self):
        from app import admin
        spec, err = admin._check_broadcast({"text": "A", "variant_b": "B", "holdout": "20"})
        self.assertIsNone(err)
        self.assertEqual((spec["holdout"], spec["variant_b"]), (20, "B"))
        again, err = admin._check_broadcast(spec)  # a scheduled broadcast is checked again at launch
        self.assertEqual((again["holdout"], again["variant_b"]), (20, "B"))
        for body, needle in [
            ({"text": "A", "holdout": 70}, "от 1 до 50"),
            ({"text": "A", "variant_b": "A"}, "совпадает"),
        ]:
            self.assertIn(needle, admin._check_broadcast(body)[1])

    def test_broadcast_arms(self):
        arms = [ex.broadcast_arm(5, uid, 20, True) for uid in range(10000)]
        self.assertAlmostEqual(arms.count("control") / 10000, 0.2, delta=0.02)
        self.assertAlmostEqual(arms.count("b") / 10000, 0.4, delta=0.02)
        self.assertNotIn("b", {ex.broadcast_arm(5, uid, 20, False) for uid in range(2000)})
