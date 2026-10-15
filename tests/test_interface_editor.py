import copy
import unittest
from app.interface_editor import DEFAULT, validate

class InterfaceValidationTest(unittest.TestCase):
    def test_default_and_unknown_configuration(self):
        self.assertEqual(validate(DEFAULT),DEFAULT)
        for value in [None, [], {'javascript':'alert(1)'}, {**DEFAULT,'texts':{'balance':'0'}}]:
            with self.assertRaises(ValueError): validate(value)

    def test_preserve_required_block_and_unique_order(self):
        value=copy.deepcopy(DEFAULT)
        value['blocks'][0]['visible']=False
        with self.assertRaises(ValueError): validate(value)
        value=copy.deepcopy(DEFAULT)
        value['blocks'][1]=value['blocks'][0]
        with self.assertRaises(ValueError): validate(value)

    def test_button_actions_and_links(self):
        value=copy.deepcopy(DEFAULT)
        block=dict(id='test',screen='home',type='button',label='Подробнее',action='url',url='https://example.com',visible=True)
        value['custom']=[block]
        self.assertEqual(validate(value)['custom'][0],block)
        for url in ['javascript:alert(1)','http://example.com','https://user:secret@example.com','https:///bad']:
            block['url']=url
            with self.assertRaises(ValueError): validate(value)
        block['url']='https://example.com';block['action']='delete_all'
        with self.assertRaises(ValueError): validate(value)

    def test_plain_text_and_color_validation(self):
        value=copy.deepcopy(DEFAULT)
        value['texts']={'devices_title':'<script>alert(1)</script>'}
        self.assertEqual(validate(value)['texts'],value['texts'])  # rendered as textContent
        value['theme']={'background':'red;display:none'}
        with self.assertRaises(ValueError): validate(value)
        value['theme']={'radius':100}
        with self.assertRaises(ValueError): validate(value)

class InterfaceAuthTest(unittest.IsolatedAsyncioTestCase):
    async def test_admin_editor_and_preview_require_auth(self):
        from unittest.mock import patch
        from aiohttp import web
        from aiohttp.test_utils import make_mocked_request
        from app import admin
        denied=web.json_response({'ok':False},status=401)
        with patch.object(admin,'_need_auth',return_value=denied):
            for method in ['GET','POST']:
                response=await admin.api_interface_editor(make_mocked_request(method,'/admin/api/interface'))
                self.assertEqual(response.status,401)
            self.assertEqual((await admin.interface_preview(make_mocked_request('GET','/admin/interface-preview'))).status,401)

    async def test_preview_has_no_live_application_or_telegram_scripts(self):
        from unittest.mock import patch
        from aiohttp.test_utils import make_mocked_request
        from app import admin
        with patch.object(admin,'_need_auth',return_value=None):
            response=await admin.interface_preview(make_mocked_request('GET','/admin/interface-preview'))
        self.assertNotIn('telegram-web-app.js',response.text)
        self.assertNotIn('src="app.js',response.text)
        self.assertIn('interface-preview.js',response.text)
