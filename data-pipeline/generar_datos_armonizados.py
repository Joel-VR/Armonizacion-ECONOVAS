"""Genera indicadores semanales experimentales MODIS + VIIRS Suomi por departamento."""
import sys
from datetime import date
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.database import database_config
from app.services.huanuco import departments, weekly_analysis

COLUMNS = ('departamento','anio','semana_inicio','semana_fin','semana_iso','cuadricula_km','epsg',
           'modis_celdas_dia','viirs_suomi_celdas_dia','modis_percentil','viirs_suomi_percentil',
           'modis_semanas_referencia','viirs_semanas_referencia','modis_anios_referencia','viirs_anios_referencia',
           'modis_fraccion_empates','viirs_fraccion_empates','indice_combinado','diferencia_sensores','estado',
           'ultimo_registro_modis','ultimo_registro_viirs')


def status(week):
    if week['combined'] is not None:
        return 'comparable_experimental'
    sensors = week['sensors']
    if any(sensors[s]['cells'] is None for s in ('MODIS', 'VIIRS')):
        return 'semana_o_fuente_incompleta'
    if any(sensors[s]['percentile'] is None for s in ('MODIS', 'VIIRS')):
        return 'referencia_insuficiente'
    return 'empates_excesivos'


def records(region, rows, starts, ends):
    for year in range(2016, 2027):
        for week in weekly_analysis(rows, ends, year, starts):
            m, v = week['sensors']['MODIS'], week['sensors']['VIIRS']
            yield (region['name'], year, week['start'], week['end'], week['week'], 5, region['srid'],
                   m['cells'], v['cells'], m['percentile'], v['percentile'], m['sample'], v['sample'],
                   m['years'], v['years'], m['ties'], v['ties'], week['combined'], week['disagreement'],
                   status(week), ends['MODIS'], ends['VIIRS'])


def main():
    regions = list(departments().values())
    with psycopg.connect(**database_config(), row_factory=dict_row, options='-c timezone=UTC') as conn:
        with conn.transaction():
            conn.execute('LOCK TABLE public.datos_armonizados IN EXCLUSIVE MODE')
            if conn.execute('SELECT count(*) AS n FROM public.datos_armonizados').fetchone()['n']:
                raise ValueError('La tabla datos_armonizados no está vacía; no se sobrescribirá')
            conn.execute('CREATE TEMP TABLE regiones_arm (nombre text PRIMARY KEY, srid integer NOT NULL) ON COMMIT DROP')
            with conn.cursor() as cur:
                cur.executemany('INSERT INTO regiones_arm VALUES (%s,%s)', [(r['name'], r['srid']) for r in regions])
            sources = conn.execute("""SELECT 'MODIS' AS sensor, min(acq_date)::date AS first, max(acq_date)::date AS last, count(*) AS total FROM public.modis
                UNION ALL SELECT 'VIIRS' AS sensor, min(acq_date)::date, max(acq_date)::date, count(*) FROM public.viirs WHERE satellite='SNPP'""").fetchall()
            if len(sources) != 2 or any(not row['total'] for row in sources):
                raise ValueError('Se necesitan datos de MODIS y VIIRS Suomi para generar la referencia')
            starts = {row['sensor']: row['first'] for row in sources}
            ends = {row['sensor']: row['last'] for row in sources}
            print('Fuentes:', sources, flush=True)
            print('Calculando celdas-día por departamento; puede tardar varios minutos...', flush=True)
            rows = conn.execute("""WITH observaciones AS (
                SELECT departamento, 'MODIS'::text AS sensor, acq_date, latitude, longitude FROM public.modis
                  WHERE departamento IS NOT NULL AND acq_date >= '2016-01-01' AND acq_date < '2027-01-01'
                UNION ALL
                SELECT departamento, 'VIIRS'::text AS sensor, acq_date, latitude, longitude FROM public.viirs
                  WHERE satellite='SNPP' AND departamento IS NOT NULL AND acq_date >= '2016-01-01' AND acq_date < '2027-01-01'
                ), proyectados AS MATERIALIZED (
                  SELECT o.departamento,o.sensor,o.acq_date::date AS day,
                         ST_Transform(ST_SetSRID(ST_MakePoint(o.longitude,o.latitude),4326),r.srid) AS p
                  FROM observaciones o JOIN regiones_arm r ON r.nombre=o.departamento
                ), celdas AS (
                  SELECT DISTINCT departamento,sensor,day,floor(ST_X(p)/5000)::int AS x,floor(ST_Y(p)/5000)::int AS y
                  FROM proyectados
                ) SELECT departamento,sensor,day,count(*) AS cells FROM celdas GROUP BY departamento,sensor,day
                ORDER BY departamento,day,sensor""").fetchall()
            by_department = {r['name']: [] for r in regions}
            for row in rows:
                by_department[row['departamento']].append(row)
            expected = 0
            command = 'COPY public.datos_armonizados (' + ','.join(COLUMNS) + ') FROM STDIN'
            with conn.cursor() as cur:
                with cur.copy(command) as copy:
                    for region in regions:
                        count = 0
                        for record in records(region, by_department[region['name']], starts, ends):
                            copy.write_row(record)
                            count += 1
                        expected += count
                        print(region['name'], count, 'semanas', flush=True)
            actual = conn.execute('SELECT count(*) AS n FROM public.datos_armonizados').fetchone()['n']
            if actual != expected:
                raise ValueError(f'Conteo inesperado: {actual} != {expected}')
            print('Total verificado:',actual,flush=True)
    print('Datos armonizados confirmados.',flush=True)


if __name__ == '__main__':
    main()
