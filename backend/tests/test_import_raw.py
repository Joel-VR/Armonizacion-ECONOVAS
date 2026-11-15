import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[2] / 'data-pipeline' / 'import_raw_firms.py'
spec = importlib.util.spec_from_file_location('import_raw_firms', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class RawImportTest(unittest.TestCase):
    def setUp(self):
        self.record = dict.fromkeys(module.COLUMNS, 1)
        self.record.update({'acq_date': '2026-01-01', 'acq_time': '0513', 'satellite': 'SNPP',
                            'instrument': 'SNPP', 'confidence': 'n', 'version': '2.0NRT'})
        del self.record['type']

    def test_values_preserved_and_missing_type_is_null(self):
        row = dict(zip(module.COLUMNS, module.raw_row(self.record, {'SNPP'})))
        self.assertEqual(row['instrument'], 'SNPP')
        self.assertEqual(row['acq_time'], '0513')
        self.assertEqual(row['confidence'], 'n')
        self.assertIsNone(row['type'])

    def test_rejects_wrong_satellite_or_extra_field(self):
        with self.assertRaises(ValueError):
            module.raw_row(self.record, {'N20'})
        with self.assertRaises(ValueError):
            module.raw_row({**self.record, 'unexpected': 1}, {'SNPP'})

if __name__ == '__main__':
    unittest.main()
