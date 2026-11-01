import unittest
from datetime import datetime,timedelta,timezone
from app.revenue_forecast import repeat_probability,forecast

class ForecastTest(unittest.TestCase):
    def test_conditional_repeat_and_censoring(self):
        # Ten observed cycles, half repeat at day 5; others observed through day 40.
        intervals=[(5,True)]*5+[(40,False)]*5
        self.assertAlmostEqual(repeat_probability(intervals,0,7),.5)
        self.assertIsNone(repeat_probability(intervals,6,7))  # only 5 at risk
        self.assertIsNone(repeat_probability([(1,False)]*10,0,30))
        self.assertEqual(repeat_probability([(40,False)]*10,0,30),0)
        self.assertAlmostEqual(repeat_probability([(2,False)]*5+[(5,True)]*5+[(40,False)]*5,0,7),.5)

    def test_due_clients_amounts_and_insufficient_data(self):
        now=datetime(2026,10,29,tzinfo=timezone.utc)
        rows=[]
        # 20 initial payments 40 days ago; 10 repeated 5 days later.
        for uid in range(20):
            rows.append(dict(id=f'a{uid}',telegram_id=uid,at=now-timedelta(days=40),currency='RUB',amount=100,payment_number=1))
            if uid<10:
                rows.append(dict(id=f'b{uid}',telegram_id=uid,at=now-timedelta(days=35),currency='RUB',amount=300,payment_number=2))
        rows.append(dict(id='new',telegram_id=100,at=now-timedelta(days=1),currency='RUB',amount=100,payment_number=1))
        candidate=dict(telegram_id=100,balance_low=True,balance_rub=6,device_count=1,router_due=False,router_expire_at=None)
        result=forecast(rows,[candidate],now,6)
        self.assertEqual(result['average_repeat_rub'],300)
        self.assertEqual(result['periods'][0]['clients'],1)
        self.assertEqual(result['periods'][0]['rub'],100)  # 10 renewals / 30 observed cycles × 300
        unknown={**candidate,'telegram_id':101}
        self.assertIsNone(forecast(rows,[candidate,unknown],now,6)['periods'][0]['rub'])
        self.assertEqual(forecast(rows,[],now,6)['periods'][0]['rub'],0)
        future={**candidate,'balance_rub':60,'router_due':True,'router_expire_at':now+timedelta(days=2)}
        self.assertEqual(forecast(rows,[future],now,6)['periods'][0]['clients'],1) # once, earliest expiry
        self.assertEqual(forecast(rows,[{**candidate,'balance_rub':60}],now,6)['periods'][0]['clients'],0)
