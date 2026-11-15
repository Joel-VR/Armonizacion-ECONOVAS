import importlib.util
import unittest
from datetime import date
from pathlib import Path

path = Path(__file__).resolve().parents[2] / 'data-pipeline' / 'generar_datos_armonizados.py'
spec = importlib.util.spec_from_file_location('generar_armonizados', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class GeneratedRecordsTest(unittest.TestCase):
    def test_records_include_indicators_and_incomplete_weeks(self):
        region = {'name':'Huánuco', 'srid':32718}
        rows = [{'sensor':'MODIS','day':date(2026,9,1),'cells':4},
                {'sensor':'VIIRS','day':date(2026,9,1),'cells':7}]
        starts = {'MODIS':date(2016,1,1),'VIIRS':date(2016,1,1)}
        ends = {'MODIS':date(2026,11,13),'VIIRS':date(2026,11,1)}
        records = [dict(zip(module.COLUMNS, row)) for row in module.records(region,rows,starts,ends)]
        week = next(row for row in records if row['anio']==2026 and row['semana_inicio']==date(2026,8,31))
        self.assertEqual((week['modis_celdas_dia'],week['viirs_suomi_celdas_dia']), (4,7))
        self.assertEqual(week['modis_semanas_referencia'],45)
        unavailable = next(row for row in records if row['anio']==2026 and row['semana_inicio']==date(2026,11,2))
        self.assertIsNone(unavailable['viirs_suomi_celdas_dia'])
        self.assertIsNone(unavailable['indice_combinado'])
        self.assertEqual(unavailable['estado'],'semana_o_fuente_incompleta')
        earlier = next(row for row in records if row['anio']==2020 and row['semana_inicio']==date(2020,9,7))
        self.assertEqual(earlier['modis_semanas_referencia'],40)
        self.assertEqual(earlier['modis_anios_referencia'],8)

if __name__ == '__main__':
    unittest.main()
