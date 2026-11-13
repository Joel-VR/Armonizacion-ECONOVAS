import importlib.util
import unittest
from pathlib import Path
from datetime import timezone

path = Path(__file__).resolve().parents[2] / 'data-pipeline' / 'import_firms.py'
spec = importlib.util.spec_from_file_location('import_firms', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ImportTest(unittest.TestCase):
    def setUp(self):
        self.row = {'latitude': -9.0, 'longitude': -75.0, 'acq_date': '2020-01-01',
                    'acq_time': '0130', 'satellite': 'SNPP', 'version': '2', 'confidence': 'n'}
        self.path = Path('fire_archive_test.json')

    def test_time_fingerprint_and_missing_type(self):
        result = module.convert(self.row, self.path, 'VIIRS')
        self.assertEqual(result[3].tzinfo, timezone.utc)
        self.assertEqual(result[3].hour, 1)
        self.assertIsNone(result[13])
        self.assertEqual(result[0], module.convert(dict(reversed(list(self.row.items()))), self.path, 'VIIRS')[0])
        self.assertNotEqual(result[0], module.convert(self.row, Path('fire_nrt_test.json'), 'VIIRS')[0])

    def test_invalid_coordinate_and_satellite(self):
        with self.assertRaises(ValueError):
            module.convert({**self.row, 'latitude': 100}, self.path, 'VIIRS')
        with self.assertRaises(ValueError):
            module.convert({**self.row, 'satellite': 'N20'}, self.path, 'VIIRS')

if __name__ == '__main__':
    unittest.main()
