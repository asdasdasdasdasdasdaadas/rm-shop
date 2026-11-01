import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from app import live

class LiveSourceTest(unittest.IsolatedAsyncioTestCase):
    def test_source_details_and_escaping(self):
        text=live.acquisition_text(dict(ad_link_id=1,ad_title='<Канал & чат>',ad_slug='channel',
            referrer_id=42,referrer_name='<Друг>',referrer_username='friend'))
        self.assertIn('&lt;Канал &amp; чат&gt;',text)
        self.assertIn('ad_channel',text)
        self.assertIn('tg://user?id=42',text)
        self.assertIn('&lt;Друг&gt;',text)
        self.assertIn('Без метки источника',live.acquisition_text({}))
        self.assertIn('не удалось получить',live.acquisition_text(None))
        self.assertNotIn('Амбассадор',live.acquisition_text({'ambassador_id':42}))
        self.assertIn('История',live.acquisition_text({'ad_link_id':1,'ad_kind':'story'}))

    async def test_batch_loads_sources_once_and_posts_for_each_user(self):
        pool=SimpleNamespace(fetch=AsyncMock(return_value=[
            {'telegram_id':1,'ad_link_id':2,'ad_title':'Канал','ad_slug':'channel'},
            {'telegram_id':2,'referrer_id':42,'referrer_name':'Друг'},
            {'telegram_id':3}]))
        with patch.object(live.db,'_pool_req',return_value=pool), patch.object(live,'post') as post:
            await live._first_online_notifications([{'telegram_id':i} for i in (1,2,3)])
        pool.fetch.assert_awaited_once()
        self.assertEqual(pool.fetch.call_args.args[1],[1,2,3])
        self.assertEqual(post.call_count,3)
        self.assertIn('Канал',post.call_args_list[0].args[0])
        self.assertIn('tg://user?id=42',post.call_args_list[1].args[0])
        self.assertIn('Без метки источника',post.call_args_list[2].args[0])

    async def test_source_failure_does_not_drop_notification(self):
        with patch.object(live.db,'_pool_req',side_effect=RuntimeError('unavailable')), patch.object(live,'post') as post, patch.object(live.logger,'exception'):
            await live._first_online_notifications([{'telegram_id':1}])
        post.assert_called_once()
        self.assertIn('не удалось получить данные',post.call_args.args[0])
