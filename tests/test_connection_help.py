import json
import unittest
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from app.connection_help import connection_result, support_context

class ConnectionEvidenceTest(unittest.TestCase):
    def test_only_recent_actual_online_is_success(self):
        now=datetime.now(timezone.utc)
        self.assertEqual(connection_result({'onlineAt':now.isoformat()},now)['status'],'connected')
        for panel in [
            {'subLastOpenedAt':now.isoformat()},
            {'userTraffic':{'lifetimeUsedTrafficBytes':100}},
            {'onlineAt':(now-timedelta(hours=1)).isoformat()},
            {'onlineAt':(now+timedelta(minutes=1)).isoformat()},
            {'onlineAt':now.isoformat(),'status':'DISABLED'},
        ]:
            self.assertEqual(connection_result(panel,now)['status'],'not_confirmed')

class ConnectionSupportTest(unittest.IsolatedAsyncioTestCase):
    async def test_context_requires_owned_device_and_excludes_secrets(self):
        with patch('app.db.get_device',AsyncMock(return_value=None)) as get:
            self.assertEqual(await support_context(1,{'device_id':2}),'')
            get.assert_awaited_once_with(1,2)
        with patch('app.db.get_device',AsyncMock(return_value={'title':'Phone','platform':'ios','subscription_url':'SECRET','panel_status':'ACTIVE'})):
            text=await support_context(1,{'device_id':2,'client':'Incy','stage':'check','result':'not_confirmed'})
            self.assertIn('Incy',text)
            self.assertIn('Phone',text)
            self.assertIn('Проверка подключения',text)
            self.assertNotIn('SECRET',text)
            await support_context(1,{'device_id':2,'stage':[],'result':{}})

    async def test_endpoint_ownership_and_panel_failure(self):
        from app import web as endpoints
        request=SimpleNamespace(match_info={'device_id':'2'},app={'rw':SimpleNamespace(get_user_by_id=AsyncMock(return_value=None))})
        with patch.object(endpoints,'_require_tg',AsyncMock(return_value=(1,None))), patch('app.db.get_device',AsyncMock(return_value=None)):
            self.assertEqual((await endpoints.api_check_connection(request)).status,404)
            request.app['rw'].get_user_by_id.assert_not_awaited()
        with patch.object(endpoints,'_require_tg',AsyncMock(return_value=(1,None))), patch('app.db.get_device',AsyncMock(return_value={'remnawave_id':77})):
            response=await endpoints.api_check_connection(request)
            self.assertEqual(json.loads(response.text)['status'],'unavailable')

    async def test_ticket_endpoint_appends_context_to_actual_message(self):
        from app import web as endpoints, tickets
        class Request(dict):
            content_type='application/json'
            app={'bot':None}
            async def json(self):
                return {'text':'Не открывается сайт','connection_context':{'device_id':2,'client':'Incy','stage':'check'}}
        request=Request()
        with patch.object(endpoints,'_require_tickets',AsyncMock(return_value=(1,None))), \
             patch('app.db.get_device',AsyncMock(return_value={'title':'Phone','platform':'ios'})), \
             patch('app.db.get_user',AsyncMock(return_value={})), \
             patch('app.db.list_ticket_messages',AsyncMock(return_value=[])), \
             patch('app.db.user_list_tickets',AsyncMock(return_value=[])), \
             patch.object(tickets,'receive_user_message',AsyncMock(return_value={'id':3})) as receive:
            self.assertEqual((await endpoints.api_ticket_send(request)).status,200)
            body=receive.await_args.kwargs['body']
            self.assertIn('Не открывается сайт',body)
            self.assertIn('Phone',body)
            self.assertIn('Incy',body)
