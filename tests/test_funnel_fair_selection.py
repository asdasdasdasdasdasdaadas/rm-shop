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

