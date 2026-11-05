import json
import os
from pathlib import Path
import subprocess
import unittest
from datetime import datetime, date, timezone
from types import SimpleNamespace
from app.finance import PAYMENTS_SQL, DUE_SQL, payment_report

class FinanceReportTest(unittest.TestCase):
    def test_real_amounts_stars_and_first_repeat(self):
        rows=[dict(id='r1',telegram_id=1,plan_code='old',at=datetime(2026,10,27,22,tzinfo=timezone.utc),currency='RUB',amount=250,payment_number=2),
              dict(id='s1',telegram_id=2,plan_code='stars',at=datetime(2026,10,28,1,tzinfo=timezone.utc),currency='XTR',amount=100,payment_number=1),
              dict(id='r2',telegram_id=3,plan_code='old',at=datetime(2026,10,28,2,tzinfo=timezone.utc),currency='RUB',amount=None,payment_number=1)]
        report=payment_report(rows,date(2026,10,28),1,SimpleNamespace(topup_rub_for_code=lambda code:300))
        self.assertEqual(report['totals']['rub'],550)
        self.assertEqual(report['totals']['stars'],100)
        self.assertEqual(report['totals']['average_rub'],275)
        self.assertEqual(report['totals']['first'],2)
        self.assertEqual(report['totals']['repeat'],1)
        self.assertEqual(report['estimated'],1)
        self.assertFalse(report['items'][0]['estimated'])

@unittest.skipUnless(os.environ.get('PGLITE_MODULE'),'Set PGLITE_MODULE for PostgreSQL integration')
class FinanceSQLTest(unittest.TestCase):
    def test_paid_only_renewals_and_history(self):
        proc=subprocess.Popen(['node',str(Path(__file__).parent/'support/pglite_bridge.mjs')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
        self.addCleanup(proc.terminate)
        def query(sql,args=None,script=False):
            proc.stdin.write(json.dumps(dict(sql=sql,args=args or [],script=script))+'\n');proc.stdin.flush()
            result=json.loads(proc.stdout.readline())
            self.assertNotIn('error',result,result)
            return result['rows']
        query('''CREATE TABLE users(telegram_id bigint,first_name text,username text,balance_rub int,router_expire_at timestamptz,billing_paused_at timestamptz,blocked_at timestamptz);
        CREATE TABLE devices(telegram_id bigint,kind text);
        CREATE TABLE payments(telegram_id bigint,telegram_payment_id text,plan_code text,created_at timestamptz,stars bigint);
        CREATE TABLE rollypay_orders(order_id text,telegram_id bigint,plan_code text,paid_at timestamptz,created_at timestamptz,status text);
        CREATE TABLE payment_receipts(payment_key text,amount int);
        INSERT INTO users VALUES(1,'Paid','paid',6,NULL,NULL,NULL),(2,'Free','free',0,NULL,NULL,NULL),(3,'Router','router',100,NOW()+INTERVAL '2 days',NULL,NULL),(4,'Paused','paused',0,NULL,NOW(),NULL),(5,'Pending','pending',0,NULL,NULL,NULL),(6,'Funded','funded',500,NULL,NULL,NULL);
        INSERT INTO devices VALUES(1,''),(2,''),(3,'router'),(4,''),(5,''),(6,'');
        INSERT INTO payments VALUES(1,'s1','s','2026-09-01',50),(3,'s3','s','2026-10-28',100),(4,'s4','s','2026-10-28',100),(6,'s6','s','2026-10-28',100);
        INSERT INTO rollypay_orders VALUES('r1',1,'b300','2026-10-28','2026-10-27','granted'),('r5',5,'b300',NULL,'2026-10-28','pending');
        INSERT INTO payment_receipts VALUES('rollypay:r1',300);''',script=True)
        due=query(DUE_SQL,[6,3])
        self.assertEqual({int(r['telegram_id']) for r in due},{1,3})
        history=query(PAYMENTS_SQL,['2026-10-28T00:00:00Z','2026-10-29T00:00:00Z'])
        payment=next(r for r in history if r['id']=='rollypay:r1')
        self.assertEqual(int(payment['payment_number']),2)
        self.assertEqual(int(payment['amount']),300)
        self.assertNotIn(5,{int(r['telegram_id']) for r in history})
        proc.stdin.close();proc.wait(timeout=10);proc.stdout.close()
