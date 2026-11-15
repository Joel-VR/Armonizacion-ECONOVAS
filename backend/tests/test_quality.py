import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.quality import category, evaluate
from app.services.screening import parameters


class QualityTest(unittest.TestCase):
    def test_legend_does_not_invent_forest_or_agriculture(self):
        self.assertEqual(category(3), 'forest')
        self.assertEqual(category(21), 'agriculture')
        self.assertEqual(category(9), 'plantation')
        self.assertEqual(category(33), 'water')
        self.assertEqual(category(24), 'urban')
        self.assertEqual(category(12), 'other')  # Natural grassland is not a crop.
        self.assertEqual(category(27), 'unknown')
        self.assertEqual(category(0), 'unknown')

    def test_known_nonvegetation_is_never_a_candidate(self):
        for kind in ('1', '2', '3'):
            self.assertEqual(evaluate('VIIRS', 'h', kind, 'forest')[0], 'excluded')

    def test_unknown_nrt_type_requires_review(self):
        self.assertEqual(evaluate('MODIS', '99', None, 'forest')[0], 'review')
        self.assertEqual(evaluate('VIIRS', 'h', None, 'agriculture')[0], 'review')

    def test_confidence_is_sensor_specific(self):
        self.assertEqual(evaluate('MODIS', '29', '0', 'forest')[0], 'review')
        self.assertEqual(evaluate('MODIS', '30', '0', 'forest')[0], 'candidate')
        self.assertEqual(evaluate('VIIRS', 'n', '0', 'forest')[0], 'candidate')
        self.assertEqual(evaluate('VIIRS', 'l', '0', 'forest')[0], 'review')
        self.assertEqual(evaluate('MODIS', 'n', '0', 'forest')[0], 'review')

    def test_urban_water_and_unknown_are_reviewed_not_deleted(self):
        for cover in ('water','urban','other','unknown'):
            self.assertEqual(evaluate('VIIRS', 'h', '0', cover)[0], 'review')

    def test_reference_year_is_honest(self):
        self.assertIn('2024', evaluate('VIIRS', 'h', '0', 'forest', 2024)[1])
        self.assertIn('no confirmado', evaluate('VIIRS', 'h', '0', 'forest')[1])

    def test_api_rejects_invalid_filters_and_missing_reference(self):
        with patch('app.services.screening.metadata', return_value={'ready': True, 'layer_id': 'test'}):
            for args in [('all','all','all'),('candidate','bad','all'),('candidate','all','bad')]:
                with self.assertRaises(ValueError):
                    parameters(*args)
        with patch('app.services.screening.metadata', return_value={'ready': False}):
            with self.assertRaises(ValueError):
                parameters()


if __name__ == '__main__':
    unittest.main()
