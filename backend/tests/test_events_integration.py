"""Opt-in real local DB checks, always rolled back/read-only."""
import os
import sys
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.main import connection
from app.services.events import points, summary, detail


@unittest.skipUnless(os.getenv('BRINCO_DB_TESTS')=='1','Local database integration disabled')
class EventsIntegrationTest(unittest.TestCase):
    def test_counts_match_memberships_and_all_accepted_have_events(self):
        with connection() as c:
            info=summary(c)
            run=info['processing']['id']
            members=c.execute('SELECT count(*) AS n FROM evento_detecciones WHERE ejecucion_id=%s',(run,)).fetchone()['n']
            self.assertEqual(members,info['total_selected'])
            events=points(c,date(2026,1,1),date(2026,12,31))
            self.assertEqual(events['total'],info['event_count'])
            self.assertEqual(sum(r['observation_count'] for r in events['data']),members)
            for event in events['data']:
                self.assertIn(event['cover_category'],('forest','agriculture'))
                self.assertEqual(event['fire_type'],'0')
                self.assertEqual(len(detail(c,event['id'])['detecciones']),event['observation_count'])
                self.assertEqual(event['verification_status'],'probable')

    def test_outside_month_empty_and_raw_count_unchanged(self):
        with connection() as c:
            self.assertEqual(points(c,date(2026,12,1),date(2026,12,31))['total'],0)
            self.assertEqual(c.execute('SELECT count(*) AS n FROM fire_detections').fetchone()['n'],995074)

    def test_active_run_balances_all_outcomes(self):
        with connection() as c:
            info=summary(c)['processing']['resumen']
            self.assertEqual(info['observations'],info['accepted_observations']+info['excluded']+info['review'])
