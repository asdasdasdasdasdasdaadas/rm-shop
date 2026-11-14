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

    def test_required_fields_and_zero_delay(self):
        base = _step("s")
        for key, value in [("text", "   "), ("condition", ""), ("wait_hours", ""), ("wait_hours", None), ("wait_hours", 1.5), ("wait_hours", True), ("wait_hours", -1), ("wait_from", "")]:
            with self.subTest(key=key,value=value), self.assertRaises(ValueError):
                validate({"branches":[{"id":"b","title":"Ветка","steps":[{**base,key:value}]}]})
        clean=validate({"branches":[{"id":"b","title":"Ветка","steps":[{**base,"wait_hours":0}]}]})
        self.assertEqual(clean["branches"][0]["steps"][0]["wait_hours"],0)
        with self.assertRaises(ValueError):
            validate({"branches":[{"id":"b","title":"   ","steps":[base]}]})


if __name__ == "__main__":
    unittest.main()

class RecoveryNavigationTest(unittest.TestCase):
    def test_all_journeys_have_green_cabinet_with_target_and_menu(self):
        from unittest.mock import patch
        from app.funnel_board import markup
        from app.recovery_funnel import branches, ACTION_LABELS
        graph=validate({'branches':branches()})
        with patch('app.keyboards.mini_app_url',return_value='https://example.test/'):
            for branch in graph['branches']:
                for step in branch['steps']:
                    # Without an issued gift the gift button is left out, so the action button leads.
                    shown=[b for b in step['buttons'] if b!='claim_gift']
                    buttons=markup(step['buttons'],1).inline_keyboard
                    self.assertEqual(buttons[0][0].text, ACTION_LABELS.get(shown[0]['action'], 'Личный кабинет'))
                    self.assertEqual(buttons[0][0].style,'success')
                    # only the action button is green; «Меню» opens the profile wherever a step has it
                    for row in buttons[1:]:
                        self.assertIsNone(row[0].style)
                    if 'menu' in shown:
                        self.assertIn('profile', [row[0].callback_data for row in buttons[1:]])
            self.assertIn('screen=gift',markup(graph['branches'][0]['steps'][0]['buttons'],1).inline_keyboard[0][0].web_app.url)

class FunnelOffersTest(unittest.TestCase):
    def test_gift_button_needs_an_issued_gift(self):
        from unittest.mock import patch
        from app.funnel_board import markup
        with patch('app.keyboards.mini_app_url',return_value='https://example.test/'):
            without=markup(['claim_gift','menu'],1).inline_keyboard
            with_gift=markup(['claim_gift','menu'],1,gift_id=77).inline_keyboard
        self.assertEqual([r[0].callback_data for r in without],['profile'])
        self.assertEqual(with_gift[0][0].callback_data,'fgift:77')
        self.assertIn('3 дня',with_gift[0][0].text)

