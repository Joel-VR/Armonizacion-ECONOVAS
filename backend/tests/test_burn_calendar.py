import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.huanuco import burn_calendar, department, departments

class BurnCalendarTest(unittest.TestCase):
    def test_burn_calendar_structure(self):
        cal = burn_calendar(None, 'PE-HUC')
        self.assertIn('department', cal)
        self.assertEqual(cal['department']['code'], 'PE-HUC')
        self.assertEqual(cal['department']['name'], 'Huánuco')
        self.assertIn('years', cal)
        self.assertEqual(len(cal['years']), 27)  # 2000 - 2026 (27 years)
        self.assertEqual(len(cal['months']), 12)
        self.assertIn('2026', cal['matrix'])
        self.assertEqual(len(cal['matrix']['2026']), 12)
        self.assertIn('highest_month', cal)
        self.assertIn('alerts', cal)
        self.assertIn('methodology', cal)

    def test_other_departments_work(self):
        for code in ('PE-UCA', 'PE-MDD', 'PE-CUS', 'PE-LOR'):
            cal = burn_calendar(None, code)
            self.assertEqual(cal['department']['code'], code)
            self.assertEqual(len(cal['years']), 27)

if __name__ == '__main__':
    unittest.main()
