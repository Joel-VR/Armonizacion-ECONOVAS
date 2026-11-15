import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.event_rules import assess, cover, corroborated, group_events


def observation(id=1, hours=0, **kwargs):
    return dict(id=id,acquired_at=datetime(2026,8,1,tzinfo=timezone.utc)+timedelta(hours=hours),
                latitude=-9.5,longitude=-76.,sensor='VIIRS',satellite='N',confidence='n',
                fire_type='0',frp=10,cover_category='forest',**kwargs)


class EventRulesTest(unittest.TestCase):
    def test_peru_legend_does_not_call_wetland_or_mosaic_crops(self):
        self.assertEqual(cover(82),'other')
        self.assertEqual(cover(12),'mixed')
        self.assertEqual(cover(21),'mixed')
        self.assertEqual(cover(15),'pasture')
        self.assertEqual(cover(9),'plantation')
        for code in (35,40): self.assertEqual(cover(code),'agriculture')

    def test_urban_water_and_nonvegetation_are_excluded(self):
        for code in (24,33): self.assertEqual(assess(observation(),[code]*9)[0],'excluida')
        row=observation();row['fire_type']='2'
        self.assertEqual(assess(row,[3]*9)[0],'excluida')

    def test_unknown_type_or_invalid_quality_never_passes(self):
        for field,value in [('fire_type',None),('confidence','l'),('frp',0),('frp',None)]:
            row=observation();row[field]=value
            self.assertEqual(assess(row,[3]*9)[0],'revision')

    def test_water_neighbors_are_not_hidden_by_forest_centre(self):
        codes=[3]*9;codes[0]=33
        self.assertEqual(assess(observation(),codes)[0],'revision')
        self.assertEqual(assess(observation(),[3]*9)[0],'apta')

    def test_simultaneous_same_pass_is_not_independent_evidence(self):
        self.assertFalse(corroborated(observation(),observation(2)))
        self.assertTrue(corroborated(observation(),observation(2,hours=1)))
        self.assertFalse(corroborated(observation(),observation(2,hours=25)))
        distant=observation(2,hours=1);distant['longitude']=-75
        self.assertFalse(corroborated(observation(),distant))

    def test_groups_have_bounded_duration_and_separate_land_use(self):
        rows=[observation(i,hours=i*24) for i in range(6)]
        groups=group_events(rows)
        self.assertEqual([len(g) for g in groups],[4,2])
        crop=observation(99);crop['cover_category']='agriculture'
        self.assertEqual(len(group_events([observation(),crop])),2)

    def test_grouping_deterministic_and_every_row_assigned_once(self):
        rows=[observation(i,hours=i) for i in range(4)]
        self.assertEqual(group_events(rows),group_events(list(reversed(rows))))
        self.assertEqual(sorted(r['id'] for g in group_events(rows) for r in g),[0,1,2,3])
