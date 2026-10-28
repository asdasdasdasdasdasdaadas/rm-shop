import json
import os
from pathlib import Path
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlsplit
from app import db, funnel_board, live, referral_followup
from app.config import Settings


class ReferralFollowupTest(unittest.IsolatedAsyncioTestCase):
    async def test_tracks_without_admin_channel_and_does_not_track_other_actions(self):
        with patch.object(live, '_chat_id', return_value=None), patch.object(referral_followup, 'record_interest', AsyncMock()) as record:
            await live.user_action({'telegram_id': 42}, 'invite')
            await live.web_user_action(42, 'copy')
            await live.user_action({'telegram_id': 42}, 'cabinet')
        self.assertEqual(record.await_count, 2)
        record.assert_awaited_with(42)

    async def test_preserves_custom_graph_and_uses_personal_share_link(self):
        graph={'version':1,'branches':[]}
        updated=referral_followup.upgrade(graph)
        self.assertEqual(graph['branches'], [])
        funnel_board.validate(updated)
        self.assertEqual(referral_followup.upgrade(updated), updated)
        step=updated['branches'][0]['steps'][0]
        self.assertEqual(step['wait_hours'],72)
        settings=Settings.model_construct(bot_username='vpn_test_bot')
        with patch('app.keyboards.get_settings',return_value=settings), patch('app.funnel_board.get_settings',return_value=settings,create=True):
            markup=funnel_board.markup(step['buttons'],42)
        button=markup.inline_keyboard[0][0]
        self.assertEqual(button.text,'Отправить приглашение')
        query=parse_qs(urlsplit(button.url).query)
        self.assertEqual(query['url'],['https://t.me/vpn_test_bot?start=ref_42'])
        self.assertTrue(query['text'][0])
        self.assertTrue(button.icon_custom_emoji_id)

    def test_full_graph_is_preserved_and_id_collisions_are_avoided(self):
        graph={'branches':[{'id':f'b{i}', 'title':f'Branch {i}', 'steps':[
            funnel_board._step(f's{i}', 'invite', 48, 'Текст', ['menu'])]} for i in range(32)]}
        self.assertEqual(funnel_board.validate(referral_followup.upgrade(graph)), graph)
        graph['branches'].pop()
        graph['branches'][0]['id']='invite-followup'
        graph['branches'][0]['steps'][0]['id']='invite-followup-1'
        updated=funnel_board.validate(referral_followup.upgrade(graph))
        self.assertEqual(updated['branches'][:-1], graph['branches'])
        self.assertEqual(len(updated['branches']),32)
        self.assertEqual(referral_followup.upgrade(updated),updated)

    async def test_full_graph_defers_migration_without_marking_it_complete(self):
        from app import recovery_funnel
        graph={'branches':[{'id':f'b{i}', 'title':f'Branch {i}', 'steps':[
            funnel_board._step(f's{i}', 'invite', 48, 'Текст', ['menu'])]} for i in range(32)]}
        conn=MagicMock()
        conn.execute=AsyncMock()
        conn.fetchrow=AsyncMock(return_value={'graph':graph})
        conn.fetchval=AsyncMock(return_value=None)
        conn.transaction.return_value.__aenter__=AsyncMock()
        conn.transaction.return_value.__aexit__=AsyncMock(return_value=False)
        pool=MagicMock()
        pool.acquire.return_value.__aenter__=AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__=AsyncMock(return_value=False)
        with patch.object(recovery_funnel,'migrate',AsyncMock(return_value=graph)):
            self.assertEqual(await referral_followup.migrate(pool,graph),graph)
            self.assertEqual(conn.execute.await_count,1)  # lock only, no graph or flag writes
            graph['branches'].pop()
            result=await referral_followup.migrate(pool,graph)
        self.assertEqual(len(result['branches']),32)
        self.assertTrue(any('UPDATE funnel_graphs' in call.args[0] for call in conn.execute.call_args_list))
        self.assertTrue(any(call.args[1:]==(referral_followup.VERSION,'1') for call in conn.execute.call_args_list))

    @unittest.skipUnless(os.environ.get('PGLITE_MODULE'),'PostgreSQL integration')
    async def test_real_selection_stops_after_registration_and_delivery(self):
        pool=SimpleNamespace(fetch=AsyncMock(return_value=[]))
        step=referral_followup.upgrade({'branches':[]})['branches'][0]['steps'][0]
        with patch.object(db,'_pool_req',return_value=pool), patch('app.config.get_settings',return_value=SimpleNamespace(vpn_day_price_rub=6)):
            await funnel_board._due(step,None,20,[])
        sql,*args=pool.fetch.call_args.args
        proc=subprocess.Popen(['node',str(Path(__file__).parent/'support/pglite_bridge.mjs')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
        self.addCleanup(proc.terminate)
        def query(sql,args=None,script=False):
            proc.stdin.write(json.dumps(dict(sql=sql,args=args or [],script=script))+'\n');proc.stdin.flush()
            result=json.loads(proc.stdout.readline());self.assertNotIn('error',result,result)
            return result['rows']
        query('''CREATE TABLE users(telegram_id bigint,first_name text,referred_by bigint,invite_opened_at timestamptz,
        idle_snoozed_at timestamptz,blocked_at timestamptz,bot_blocked_at timestamptz,bot_started_at timestamptz DEFAULT NOW(),
        billing_paused_at timestamptz,quiet_notifications boolean DEFAULT false,marketing_pause_until timestamptz,vpn_feedback text);
        CREATE TABLE tickets(telegram_id bigint,status text);
        CREATE TABLE message_log(telegram_id bigint,status text,kind text,created_at timestamptz);
        CREATE TABLE funnel_step_sends(telegram_id bigint,step_id text,sent_at timestamptz);
        INSERT INTO users(telegram_id,invite_opened_at) SELECT n,NOW()-INTERVAL '4 days' FROM generate_series(1,8) n;
        UPDATE users SET invite_opened_at=NOW()-INTERVAL '1 day' WHERE telegram_id=2;
        UPDATE users SET invite_opened_at=NULL WHERE telegram_id=3;
        UPDATE users SET quiet_notifications=true WHERE telegram_id=4;
        UPDATE users SET bot_blocked_at=NOW() WHERE telegram_id=5;
        INSERT INTO users(telegram_id,referred_by) VALUES(20,6);
        INSERT INTO funnel_step_sends VALUES(7,'invite-followup-1',NOW());
        INSERT INTO message_log VALUES(8,'sent','nudge_board',NOW());''',script=True)
        query("""INSERT INTO users(telegram_id,invite_opened_at,idle_snoozed_at) VALUES
            (9,NOW()-INTERVAL '4 days',NOW()-INTERVAL '5 days'),
            (10,NOW()-INTERVAL '5 days',NOW()-INTERVAL '4 days');""",script=True)
        self.assertEqual([int(r['telegram_id']) for r in query(sql,args)],[1,9])
        recorder=SimpleNamespace(execute=AsyncMock())
        with patch.object(db,'_pool_req',return_value=recorder):
            await referral_followup.record_interest(10)
        update_sql,*update_args=recorder.execute.call_args.args
        query(update_sql,update_args)
        first=query('SELECT invite_opened_at FROM users WHERE telegram_id=10')
        query(update_sql,update_args)
        self.assertEqual(query('SELECT invite_opened_at FROM users WHERE telegram_id=10'),first)
        self.assertTrue(query('SELECT invite_opened_at > idle_snoozed_at AS resumed FROM users WHERE telegram_id=10')[0]['resumed'])
        self.assertEqual([int(r['telegram_id']) for r in query(sql,args)],[1,9])
        query("UPDATE users SET invite_opened_at=NOW()-INTERVAL '73 hours' WHERE telegram_id=10",script=True)
        self.assertEqual([int(r['telegram_id']) for r in query(sql,args)],[1,9,10])
        query('INSERT INTO users(telegram_id,referred_by) VALUES(21,1)',script=True)
        self.assertEqual([int(r['telegram_id']) for r in query(sql,args)],[9,10])
        proc.stdin.close();proc.wait(timeout=10);proc.stdout.close()
