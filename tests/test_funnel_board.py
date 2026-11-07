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
                    self.assertEqual(buttons[1][0].callback_data,'profile')
                    self.assertIsNone(buttons[1][0].style)
            self.assertIn('screen=gift',markup(graph['branches'][0]['steps'][0]['buttons'],1).inline_keyboard[0][0].web_app.url)

class MenuLayoutTest(unittest.TestCase):
    def test_menu_keeps_primary_rows_and_pairs_secondary_actions(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from app.funnel_board import main_menu_markup
        with patch('app.keyboards.mini_app_url',return_value='https://example.test'), patch('app.config.get_settings',return_value=SimpleNamespace(required_channel_enabled=True, required_channel_url='https://t.me/test')):
            kb=main_menu_markup(['cabinet',{'action':'channel','text':'Канал'},'invite','about'],1)
        self.assertEqual([len(row) for row in kb.inline_keyboard],[1,1,2])
        self.assertEqual([b.callback_data for b in kb.inline_keyboard[-1]],['share','about_service'])
        self.assertEqual(kb.inline_keyboard[0][0].style,'success')


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

    def test_goodbyes_become_offers_and_new_branches_exist(self):
        from app.recovery_funnel import branches, OLD_THIRD, GIFT_BRANCHES
        graph=validate({'branches':branches()})
        by_id={b['id']:b for b in graph['branches']}
        for bid,old in OLD_THIRD.items():
            third=by_id[bid]['steps'][2]
            self.assertNotIn(old,third['text'])
            self.assertEqual('claim_gift' in third['buttons'], bid in GIFT_BRANCHES)
        self.assertEqual(by_id['gift']['steps'][0]['wait_hours'],1)
        self.assertEqual([s['wait_hours'] for s in by_id['late']['steps']],[720,1440])
        self.assertEqual(by_id['terms-offer']['steps'][0]['condition'],'terms_offer')

    def test_saved_map_keeps_admin_edits(self):
        import copy
        from app.recovery_funnel import branches, refresh_offers, OLD_THIRD
        old=validate({'branches':branches()})
        old=copy.deepcopy(old)
        old['branches']=[b for b in old['branches'] if b['id'] not in {'late','terms-offer'}]
        for b in old['branches']:
            if b['id'] in OLD_THIRD:
                b['steps'][2]['text']=OLD_THIRD[b['id']]+'\n\nОткройте личный кабинет 👇'
                b['steps'][2]['buttons']=['menu']
            if b['id']=='gift':
                b['steps'][0]['wait_hours']=24
        old['branches'][0]['steps'][2]['text']='Свой текст админа'
        new=validate(refresh_offers(old))
        by_id={b['id']:b for b in new['branches']}
        self.assertEqual(by_id[old['branches'][0]['id']]['steps'][2]['text'],'Свой текст админа')
        self.assertIn('claim_gift',by_id['unpaid']['steps'][2]['buttons'])
        self.assertEqual(by_id['gift']['steps'][0]['wait_hours'],1)
        self.assertIn('late',by_id); self.assertIn('terms-offer',by_id)
