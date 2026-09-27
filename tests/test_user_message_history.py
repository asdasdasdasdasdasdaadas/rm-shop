import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from app import admin, db

class UserMessageHistoryTest(unittest.IsolatedAsyncioTestCase):
    def test_exact_id_filter_is_not_text_search(self):
        clauses,args=db._message_log_filters('',{'telegram_id':123,'source':'manual','status':'failed'})
        self.assertEqual(args,[123,'manual','failed'])
        self.assertEqual(clauses,['telegram_id = $1','source = $2','status = $3'])

    async def test_endpoint_paginates_and_cannot_override_user_with_query(self):
        request=SimpleNamespace(match_info={'telegram_id':'123'},query={'page':'2','telegram_id':'999','source':'auto','status':'sent','q':'999'})
        with patch.object(admin,'_need_auth',return_value=None),patch.object(db,'admin_list_messages',AsyncMock(return_value=([],0))) as fetch:
            result=await admin.api_user_messages(request)
        self.assertEqual(result.status,200)
        fetch.assert_awaited_once_with('',20,20,{'telegram_id':123,'source':'auto','status':'sent'})

    async def test_bad_page_does_not_query_database(self):
        request=SimpleNamespace(match_info={'telegram_id':'123'},query={'page':'oops'})
        with patch.object(admin,'_need_auth',return_value=None),patch.object(db,'admin_list_messages',AsyncMock()) as fetch:
            self.assertEqual((await admin.api_user_messages(request)).status,400)
        fetch.assert_not_awaited()
