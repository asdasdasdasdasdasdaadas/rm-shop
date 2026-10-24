import unittest
from datetime import datetime, timedelta, timezone
from app.funnel_journey_metrics import summarize

class MetricsTest(unittest.TestCase):
    def test_same_observation_window_and_median(self):
        now=datetime(2026,10,24,tzinfo=timezone.utc)
        start=now-timedelta(days=20)
        rows=[dict(started=start,gift=start,device=start+timedelta(hours=2),online=start+timedelta(hours=3),paid=start+timedelta(days=1),repeat_paid=start+timedelta(days=3),blocked=start+timedelta(days=4)),
              dict(started=now-timedelta(days=1),gift=now-timedelta(days=1),device=now,blocked=None)]
        current=summarize(rows,now)['items'][1]
        self.assertEqual(current['transitions'][0]['eligible'],1)
        self.assertEqual(current['transitions'][0]['median_hours'],2)
        self.assertEqual(current['block_rate'],100)
        self.assertEqual(current['transitions'][3]['rate'],100)

    def test_out_of_order_and_empty_cohort(self):
        now=datetime(2026,10,24,tzinfo=timezone.utc)
        start=now-timedelta(days=20)
        data=summarize([dict(started=start,gift=start,device=start-timedelta(days=1))],now)
        self.assertIsNone(data['items'][0]['transitions'][0]['rate'])
        self.assertEqual(data['items'][1]['transitions'][0]['converted'],0)
        self.assertEqual(data['items'][1]['transitions'][1]['eligible'],0)
