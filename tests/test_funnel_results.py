import json
import os
from pathlib import Path
import subprocess
import unittest
from app.funnel_results import SQL

@unittest.skipUnless(os.environ.get('PGLITE_MODULE'),'PostgreSQL integration')
class ResultsTest(unittest.TestCase):
    def test_last_message_window_amounts_blocks_and_test_exclusion(self):
        proc=subprocess.Popen(['node',str(Path(__file__).parent/'support/pglite_bridge.mjs')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
        self.addCleanup(proc.terminate)
        def query(sql,args=None,script=False):
            proc.stdin.write(json.dumps(dict(sql=sql,args=args or [],script=script))+'\n');proc.stdin.flush()
            result=json.loads(proc.stdout.readline());self.assertNotIn('error',result,result)
            return result['rows']
        query('''CREATE TABLE users(telegram_id bigint,first_online_at timestamptz);
        CREATE TABLE message_log(id bigint,telegram_id bigint,kind text,source text,status text,title text,created_at timestamptz,extra jsonb);
        CREATE TABLE rollypay_orders(order_id text,telegram_id bigint,paid_at timestamptz,created_at timestamptz,status text);
        CREATE TABLE gram_orders(id text,telegram_id bigint,plan_code text,paid_at timestamptz,status text,amount_rub bigint);
        CREATE TABLE payment_receipts(payment_key text,amount bigint);
        CREATE TABLE payments(telegram_id bigint,created_at timestamptz,stars bigint);
        INSERT INTO users VALUES(1,'2026-10-05'),(2,NULL);
        INSERT INTO message_log VALUES
         (1,1,'nudge_board','auto','sent','First','2026-10-01','{"step_id":"first"}'),
         (2,1,'nudge_board','auto','sent','Second','2026-10-04','{"step_id":"second"}'),
         (3,1,'nudge_board','test','sent','Test','2026-10-05','{"step_id":"test"}'),
         (4,2,'nudge_board','auto','failed','First','2026-10-02','{"step_id":"first","error_raw":"Forbidden: bot was blocked by the user"}'),
         (5,3,'nudge_board','auto','failed','First','2026-10-03','{"step_id":"first","error_raw":"Forbidden: user is deactivated"}');
        INSERT INTO rollypay_orders VALUES
         ('a',1,'2026-10-03','2026-10-03','granted'),
         ('b',1,'2026-10-06','2026-10-06','granted'),
         ('unknown',1,'2026-10-07','2026-10-07','granted'),
         ('late',1,'2026-10-12','2026-10-12','granted');
        INSERT INTO payment_receipts VALUES('rollypay:a',100),('rollypay:b',300),('rollypay:late',500);
        INSERT INTO payments VALUES(1,'2026-10-06',50);''',script=True)
        rows={r['step']:r for r in query(SQL,['2026-10-01','2026-10-20'])}
        self.assertEqual(set(rows),{'first','second'})
        self.assertEqual(int(rows['first']['rub']),100)
        self.assertEqual(rows['first']['connected'],0)
        self.assertEqual(rows['first']['blocked'],1)
        self.assertEqual(rows['first']['attempted_users'],3)
        self.assertEqual(int(rows['second']['rub']),300)
        self.assertEqual(int(rows['second']['stars']),50)
        self.assertEqual(rows['second']['payments'],3)
        self.assertEqual(rows['second']['payers'],1)
        self.assertEqual(rows['second']['unknown'],1)
        self.assertEqual(rows['second']['connected'],1)
        # Newer message outside report period must still end attribution for the older one.
        rows=query(SQL,['2026-10-01','2026-10-04'])
        self.assertEqual(sum(int(r['rub']) for r in rows),100)
        proc.stdin.close();proc.wait(timeout=10);proc.stdout.close()
