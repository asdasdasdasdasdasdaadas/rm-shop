import unittest
from unittest.mock import AsyncMock

from app.remnawave import RemnawaveClient, RemnawaveError


def client(side_effect):
    rw = RemnawaveClient.__new__(RemnawaveClient)
    rw._request = AsyncMock(side_effect=side_effect)
    return rw


class ReissueClearsHwidTest(unittest.IsolatedAsyncioTestCase):
    async def test_revoke_unbinds_old_devices(self):
        user = {'uuid': 'u-1', 'subscriptionUrl': 'https://vpn.test/new'}
        rw = client([{'response': user}, None])
        self.assertEqual(await rw.revoke_subscription({'uuid': 'u-1'}), user)
        calls = [c.args[:2] + (c.kwargs.get('json'),) for c in rw._request.await_args_list]
        self.assertEqual(calls, [
            ('POST', '/users/u-1/actions/revoke', {}),
            ('POST', '/hwid/devices/delete-all', {'userUuid': 'u-1'}),
        ])

    async def test_falls_back_to_one_by_one_delete(self):
        devices = {'response': {'devices': [{'hwid': 'a'}, {'hwid': 'b'}]}}
        rw = client([RemnawaveError('404'), devices, None, None])
        self.assertTrue(await rw.clear_hwid_devices('u-1'))
        deleted = [c.kwargs['json']['hwid'] for c in rw._request.await_args_list[2:]]
        self.assertEqual(deleted, ['a', 'b'])

    async def test_hwid_failure_does_not_break_reissue(self):
        user = {'uuid': 'u-1', 'subscriptionUrl': 'https://vpn.test/new'}
        rw = client([{'response': user}, RemnawaveError('500'), RemnawaveError('500')])
        self.assertEqual(await rw.revoke_subscription({'uuid': 'u-1'}), user)


if __name__ == '__main__':
    unittest.main()
