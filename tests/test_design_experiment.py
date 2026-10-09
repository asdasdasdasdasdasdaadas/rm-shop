import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from app import design_experiment as exp, db

class DesignExperimentTest(unittest.IsolatedAsyncioTestCase):
    def test_stable_balanced_assignment_for_large_ids(self):
        ids = range(8000000000,8000010000)
        modern = sum(exp.variant_for(i)=='modern' for i in ids)
        self.assertTrue(4800 < modern < 5200)
        self.assertEqual(exp.variant_for(96003472116),exp.variant_for(96003472116))

    async def test_admin_and_stopped_test_do_not_assign(self):
        pool=SimpleNamespace(fetchrow=AsyncMock())
        with patch.object(db,'_pool_req',return_value=pool),patch.object(exp,'get_settings',return_value=SimpleNamespace(admin_id_set={7})),patch.object(exp,'enabled',AsyncMock(return_value=False)):
            self.assertFalse((await exp.assignment(7))['active'])
            self.assertFalse((await exp.assignment(8))['active'])
        pool.fetchrow.assert_not_called()

    async def test_saved_assignment_wins_and_does_not_rewrite_variant(self):
        pool=SimpleNamespace(fetchrow=AsyncMock(return_value={'variant':'classic'}))
        with patch.object(db,'_pool_req',return_value=pool),patch.object(exp,'get_settings',return_value=SimpleNamespace(admin_id_set=set())),patch.object(exp,'enabled',AsyncMock(return_value=True)):
            self.assertEqual((await exp.assignment(8))['variant'],'classic')
        self.assertNotIn('SET variant=',pool.fetchrow.call_args.args[0])

    async def test_endpoints_require_auth_and_validate_payload(self):
        from app import admin, web as handlers
        from aiohttp import web
        denied=web.json_response({'ok':False},status=401)
        with patch.object(admin,'_need_auth',return_value=denied),patch.object(exp,'statistics',AsyncMock()) as stats:
            self.assertEqual((await admin.api_design_experiment(SimpleNamespace())).status,401)
            stats.assert_not_called()
        for body in [[], {'stage':[],'variant':'modern'},{'stage':'paid','variant':'modern'},{'stage':'exposure','variant':{}}]:
            with patch.object(handlers,'_require_tg',AsyncMock(return_value=(7,None))),patch.object(exp,'record',AsyncMock()) as record:
                response=await handlers.api_design_event(SimpleNamespace(json=AsyncMock(return_value=body)))
                self.assertEqual(response.status,400)
                record.assert_not_called()
