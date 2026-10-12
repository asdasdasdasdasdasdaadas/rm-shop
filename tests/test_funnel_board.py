import unittest

from app.funnel_board import validate


def _step(sid, condition="no_device", buttons=None):
    return {
        "id": sid, "condition": condition, "wait_hours": 24, "wait_from": "anchor",
        "text": "Текст", "buttons": buttons or ["cabinet"], "enabled": True,
    }


class FunnelBoardTest(unittest.TestCase):
    def test_keeps_known_buttons_and_rejects_a_second_special_step(self):
        graph = validate({"branches": [{
            "id": "start", "title": "Старт",
            "steps": [_step("start-1", buttons=["gift", "help"])],
        }]})
        self.assertEqual(graph["branches"][0]["steps"][0]["buttons"], ["gift", "help"])
        with self.assertRaises(ValueError):
            validate({"branches": [
                {"id": "a", "title": "Счёт", "steps": [_step("a1", "unpaid_invoice")]},
                {"id": "b", "title": "Ещё счёт", "steps": [_step("b1", "unpaid_invoice")]},
            ]})

    def test_rejects_an_unknown_button(self):
        with self.assertRaises(ValueError):
            validate({"branches": [{
                "id": "start", "title": "Старт",
                "steps": [_step("start-1", buttons=["delete-user"])],
            }]})


if __name__ == "__main__":
    unittest.main()
