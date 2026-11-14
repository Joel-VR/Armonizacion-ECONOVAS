import sys
import unittest
from pathlib import Path
from datetime import date
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.huanuco import percentile, weekly_analysis, cell_comparison, departments, geometry

class HuanucoTest(unittest.TestCase):
    def test_departments_and_lima_components(self):
        import json
        regions = departments()
        self.assertEqual(len(regions), 25)
        self.assertEqual(len(json.loads(geometry('PE-LIM'))['geometries']), 2)
        self.assertEqual(regions['PE-HUC']['srid'], 32718)
        self.assertIn(regions['PE-TUM']['srid'], (32717, 32718))
        self.assertIn('PE-CAL', regions)
        with self.assertRaises(ValueError):
            geometry('PE-INVALID')

    def test_empirical_percentile_ties(self):
        self.assertEqual(percentile(2, [1, 2, 2, 4]), .5)

    def test_cell_comparison_and_unavailable_sensor(self):
        starts = {'MODIS': date(2016, 1, 1), 'VIIRS': date(2016, 1, 1)}
        ends = {'MODIS': date(2026, 11, 13), 'VIIRS': date(2026, 11, 1)}
        day = date(2025, 9, 8)
        result = cell_comparison({('MODIS', day): 2, ('VIIRS', day): 1}, day, starts, ends)
        self.assertEqual(result['combined'], 1)
        self.assertEqual(result['sensors']['MODIS']['sample'], 45)
        only_modis = cell_comparison({('MODIS', day): 2}, day, starts, ends)
        self.assertIsNone(only_modis['combined'])
        self.assertEqual(only_modis['sensors']['VIIRS']['ties'], 1)
        incomplete = cell_comparison({('MODIS', date(2026, 11, 2)): 1}, date(2026, 11, 2), starts, ends)
        self.assertIsNone(incomplete['combined'])
        self.assertIsNone(incomplete['sensors']['VIIRS']['days'])
        self.assertIsNone(cell_comparison({}, date(2025, 12, 29), starts, ends))

    def test_reference_excludes_selected_year(self):
        ends = {'MODIS': date(2026, 11, 13), 'VIIRS': date(2026, 11, 1)}
        baseline_year = weekly_analysis([], ends, 2020)
        later_year = weekly_analysis([], ends, 2025)
        selected = next(w for w in baseline_year if w['start'] == date(2020, 9, 7))
        later = next(w for w in later_year if w['start'] == date(2025, 9, 8))
        self.assertEqual(selected['sensors']['MODIS']['sample'], 40)
        self.assertEqual(selected['sensors']['MODIS']['years'], 8)
        self.assertEqual(later['sensors']['MODIS']['sample'], 45)
        self.assertEqual(later['sensors']['MODIS']['years'], 9)

    def test_complete_weeks_and_sensor_cutoff(self):
        rows = [{'sensor': 'MODIS', 'day': date(2026, 9, 1), 'cells': 4},
                {'sensor': 'MODIS', 'day': date(2026, 9, 2), 'cells': 2},
                {'sensor': 'VIIRS', 'day': date(2026, 9, 1), 'cells': 7}]
        result = weekly_analysis(rows, {'MODIS': date(2026, 11, 13), 'VIIRS': date(2026, 11, 1)})
        week = next(w for w in result if w['start'] == date(2026, 8, 31))
        self.assertEqual(week['sensors']['MODIS']['cells'], 6)
        self.assertEqual(week['sensors']['VIIRS']['cells'], 7)
        self.assertEqual(week['sensors']['MODIS']['sample'], 45)
        later = next(w for w in result if w['start'] == date(2026, 11, 2))
        self.assertIsNone(later['sensors']['VIIRS']['cells'])
        self.assertIsNone(later['combined'])
        self.assertIsNone(result[0]['combined'])

if __name__ == '__main__':
    unittest.main()
