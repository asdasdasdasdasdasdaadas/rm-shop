import unittest
from unittest.mock import AsyncMock, patch
from app import funnel_board as board

class FairSelectionTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        board._scan_cursors.clear()

    async def test_moves_beyond_first_twenty(self):
        async def due(step, prev, limit, skip, *, after_id):
            return [{'telegram_id': i} for i in range(after_id+1, min(46, after_id+limit+1))]
        with patch.object(board, '_due', side_effect=due):
            ids = [r['telegram_id'] async for r in board._candidates({'id':'x'}, None, [], [])]
        self.assertEqual(ids, list(range(1,46)))
        self.assertNotIn('x', board._scan_cursors)

    async def test_bounded_scan_continues_next_tick(self):
        async def due(step, prev, limit, skip, *, after_id):
            return [{'telegram_id': i} for i in range(after_id+1, after_id+limit+1)]
        with patch.object(board, '_due', side_effect=due), patch.object(board, 'SCAN_PAGES', 1):
            first = [r async for r in board._candidates({'id':'x'}, None, [], [])]
            second = [r async for r in board._candidates({'id':'x'}, None, [], [])]
        self.assertEqual(first[-1]['telegram_id'],20)
        self.assertEqual(second[0]['telegram_id'],21)

    def test_refresh_preserves_custom_settings(self):
        from app.recovery_funnel import refresh_saved_graph
        graph={'branches':[{'id':'custom','steps':[{'id':'keep','condition':'recover_gift','enabled':False,'wait_hours':17,'text':'Своя фраза','buttons':[{'action':'gift','text':'Личный кабинет','emoji':'123'},{'action':'topup','text':'Моя кнопка'}]}]}]}
        updated=refresh_saved_graph(graph)
        step=updated['branches'][0]['steps'][0]
        self.assertEqual(step['buttons'][0]['text'],'Забрать подарок')
        self.assertEqual(step['buttons'][0]['emoji'],'123')
        self.assertEqual(step['buttons'][1]['text'],'Моя кнопка')
        self.assertEqual(step['wait_hours'],17)
        self.assertFalse(step['enabled'])
        self.assertEqual(step['text'],'Своя фраза')
        self.assertEqual(refresh_saved_graph(updated),updated)
        self.assertEqual(graph['branches'][0]['steps'][0]['buttons'][0]['text'],'Личный кабинет')
