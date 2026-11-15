"""Configura e importa todos los datos FIRMS y el Calendario de Quemas en PostgreSQL local.

Uso:
    python data-pipeline/setup_local_database.py
    python data-pipeline/setup_local_database.py --force  # sobrescribe datos previos
"""
import argparse
import json
import math
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import ijson
import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.database import database_config
from app.services.huanuco import departments, weekly_analysis

GEO_PATH = ROOT / 'frontend/public/geo/peru-departments.geojson'
CALENDAR_JSON = ROOT / 'data/processed/burn_calendar_summary.json'

COLUMNS_FIRMS = (
    'latitude', 'longitude', 'acq_date', 'acq_time', 'instrument', 'track',
    'daynight', 'scan', 'version', 'confidence', 'satellite', 'brightness',
    'type', 'frp', 'bright_t31', 'departamento'
)
REQUIRED_FIRMS = set(COLUMNS_FIRMS) - {'type', 'departamento'}

SOURCE_FOLDERS = (
    ('MODIS C6.1', 'modis', {'Aqua', 'Terra'}),
    ('SUOMI VIIRS C2', 'viirs', {'SNPP'}),
    ('J1 VIIRS C2', 'viirs', {'N20'}),
    ('J2 VIIRS C2', 'viirs', {'N21'}),
)

DDL_TABLES = """
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS public.modis (
    latitude double precision,
    longitude double precision,
    acq_date text,
    acq_time text,
    instrument text,
    track double precision,
    daynight text,
    scan double precision,
    version text,
    confidence text,
    satellite text,
    brightness double precision,
    type text,
    frp double precision,
    bright_t31 double precision,
    departamento text
);

CREATE TABLE IF NOT EXISTS public.viirs (
    latitude double precision,
    longitude double precision,
    acq_date text,
    acq_time text,
    instrument text,
    track double precision,
    daynight text,
    scan double precision,
    version text,
    confidence text,
    satellite text,
    brightness double precision,
    type text,
    frp double precision,
    bright_t31 double precision,
    departamento text
);

CREATE TABLE IF NOT EXISTS public.calendario_quemas (
    departamento_codigo text NOT NULL,
    departamento_nombre text NOT NULL,
    anio smallint NOT NULL,
    mes smallint NOT NULL,
    mes_nombre text NOT NULL,
    mes_corto text NOT NULL,
    indice_armonizado double precision,
    mediana_historica double precision,
    anomalia_delta double precision,
    anomalia_pct double precision,
    anomalia_estado text NOT NULL,
    modis_celdas integer NOT NULL DEFAULT 0,
    viirs_celdas integer NOT NULL DEFAULT 0,
    total_celdas integer NOT NULL DEFAULT 0,
    temporada_alta boolean NOT NULL DEFAULT false,
    periodo_atipico boolean NOT NULL DEFAULT false,
    era_sensor text NOT NULL,
    PRIMARY KEY (departamento_codigo, anio, mes)
);

CREATE TABLE IF NOT EXISTS public.calendario_lineas_base (
    departamento_codigo text NOT NULL,
    mes smallint NOT NULL,
    mediana double precision NOT NULL,
    p25 double precision NOT NULL,
    p75 double precision NOT NULL,
    minimo double precision NOT NULL,
    maximo double precision NOT NULL,
    PRIMARY KEY (departamento_codigo, mes)
);

CREATE TABLE IF NOT EXISTS public.datos_armonizados (
    departamento text NOT NULL,
    anio smallint NOT NULL,
    semana_inicio date NOT NULL,
    semana_fin date NOT NULL,
    semana_iso smallint NOT NULL,
    cuadricula_km smallint NOT NULL,
    epsg integer NOT NULL,
    modis_celdas_dia integer,
    viirs_suomi_celdas_dia integer,
    modis_percentil double precision,
    viirs_suomi_percentil double precision,
    modis_semanas_referencia smallint NOT NULL,
    viirs_semanas_referencia smallint NOT NULL,
    modis_anios_referencia smallint NOT NULL,
    viirs_anios_referencia smallint NOT NULL,
    modis_fraccion_empates double precision,
    viirs_fraccion_empates double precision,
    indice_combinado double precision,
    diferencia_sensores double precision,
    estado text NOT NULL,
    referencia_inicio smallint NOT NULL DEFAULT 2016,
    referencia_fin smallint NOT NULL DEFAULT 2024,
    fuente_modis text NOT NULL DEFAULT 'Terra y Aqua',
    fuente_viirs text NOT NULL DEFAULT 'Suomi NPP',
    ultimo_registro_modis date NOT NULL,
    ultimo_registro_viirs date NOT NULL,
    cobertura text NOT NULL DEFAULT 'desconocida',
    metodo text NOT NULL DEFAULT 'experimental_v1',
    calculado_en timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (departamento, anio, semana_inicio, cuadricula_km, metodo),
    CHECK (semana_fin = semana_inicio + 6),
    CHECK (indice_combinado IS NULL OR indice_combinado BETWEEN 0 AND 1),
    CHECK (diferencia_sensores IS NULL OR diferencia_sensores BETWEEN 0 AND 1)
);
"""

INDEX_DDL = """
CREATE INDEX IF NOT EXISTS idx_modis_dept_date ON public.modis (departamento, acq_date);
CREATE INDEX IF NOT EXISTS idx_viirs_dept_date ON public.viirs (departamento, acq_date);
CREATE INDEX IF NOT EXISTS idx_modis_date ON public.modis (acq_date);
CREATE INDEX IF NOT EXISTS idx_viirs_date ON public.viirs (acq_date);
"""


def point_in_poly(x, y, poly):
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(1, n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def load_department_polygons():
    with open(GEO_PATH, encoding='utf-8') as f:
        geo = json.load(f)
    deps = {}
    for feat in geo['features']:
        props = feat['properties']
        code = 'PE-LIM' if props['shapeISO'] == 'PE-LMA*' else props['shapeISO']
        name = 'Lima' if code == 'PE-LIM' else props['shapeName']
        geom = feat['geometry']
        rings = []
        if geom['type'] == 'Polygon':
            for r in geom['coordinates']:
                rings.append([(float(p[0]), float(p[1])) for p in r])
        elif geom['type'] == 'MultiPolygon':
            for poly in geom['coordinates']:
                for r in poly:
                    rings.append([(float(p[0]), float(p[1])) for p in r])
        all_pts = [p for r in rings for p in r]
        lons = [p[0] for p in all_pts]
        lats = [p[1] for p in all_pts]
        deps[code] = {
            'name': name,
            'bbox': (min(lons), min(lats), max(lons), max(lats)),
            'rings': rings
        }
    return deps


def find_department(lon, lat, deps):
    for d in deps.values():
        bx0, by0, bx1, by1 = d['bbox']
        if bx0 <= lon <= bx1 and by0 <= lat <= by1:
            for r in d['rings']:
                if point_in_poly(lon, lat, r):
                    return d['name']
    return None


def raw_firms_row(record, satellites, deps):
    missing = REQUIRED_FIRMS - record.keys()
    if missing:
        raise ValueError(f'Campos requeridos faltantes: {sorted(missing)}')
    if record.get('satellite') not in satellites:
        raise ValueError(f"Satélite inesperado: {record.get('satellite')}")
    lat = float(record['latitude'])
    lon = float(record['longitude'])
    dept = find_department(lon, lat, deps)
    row = []
    for col in COLUMNS_FIRMS[:-1]:
        val = record.get(col)
        if val is not None and col in ('latitude', 'longitude', 'track', 'scan', 'brightness', 'frp', 'bright_t31'):
            row.append(float(val))
        elif val is not None:
            row.append(str(val))
        else:
            row.append(None)
    row.append(dept)
    return tuple(row)


def step_create_tables(conn):
    print('==> 1. Creando tablas en PostgreSQL (brinco)...', flush=True)
    with conn.cursor() as cur:
        cur.execute(DDL_TABLES)
    conn.commit()
    print('    Tablas y extensiones listas.', flush=True)


def step_import_calendar(conn, force=False):
    print('==> 2. Importando Calendario de Quemas en la base de datos...', flush=True)
    if not CALENDAR_JSON.exists():
        print('    AVISO: No se encontró burn_calendar_summary.json, omitiendo importación del calendario.')
        return

    with open(CALENDAR_JSON, encoding='utf-8') as f:
        all_data = json.load(f)

    with conn.transaction():
        conn.execute('TRUNCATE TABLE public.calendario_quemas, public.calendario_lineas_base')
        cal_count = 0
        base_count = 0

        cal_stmt = sql.SQL("""INSERT INTO public.calendario_quemas (
            departamento_codigo, departamento_nombre, anio, mes, mes_nombre, mes_corto,
            indice_armonizado, mediana_historica, anomalia_delta, anomalia_pct, anomalia_estado,
            modis_celdas, viirs_celdas, total_celdas, temporada_alta, periodo_atipico, era_sensor
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""")

        base_stmt = sql.SQL("""INSERT INTO public.calendario_lineas_base (
            departamento_codigo, mes, mediana, p25, p75, minimo, maximo
        ) VALUES (%s,%s,%s,%s,%s,%s,%s)""")

        for code, cdata in all_data.items():
            dept_name = cdata.get('department', {}).get('name', code)
            months_meta = cdata.get('months', [])
            for m_info in months_meta:
                m = m_info.get('month', 1)
                b = m_info.get('baseline', {})
                conn.execute(base_stmt, (code, m, b.get('median', 0), b.get('p25', 0), b.get('p75', 0), b.get('min', 0), b.get('max', 0)))
                base_count += 1

            matrix = cdata.get('matrix', {})
            for y_str, month_cells in matrix.items():
                y = int(y_str)
                # month_cells es una lista de 12 meses
                for cell in month_cells:
                    m = int(cell.get('month', 1))
                    conn.execute(cal_stmt, (
                        code, dept_name, y, m,
                        cell.get('month_name', ''), cell.get('month_short', ''),
                        cell.get('harmonized_index'), cell.get('historical_median'),
                        cell.get('anomaly_delta'), cell.get('anomaly_pct'),
                        cell.get('anomaly_status', 'sin_datos'),
                        cell.get('modis_cells', 0), cell.get('viirs_cells', 0),
                        cell.get('total_cells', 0),
                        cell.get('is_peak_season', False), cell.get('is_unusual_timing', False),
                        cell.get('sensor_era', 'MODIS')
                    ))
                    cal_count += 1

    print(f'    Calendario importado: {cal_count} celdas mensuales, {base_count} líneas base.', flush=True)


def step_import_raw_firms(conn, data_dir, force=False):
    print('==> 3. Importando observaciones satelitales FIRMS...', flush=True)
    deps = load_department_polygons()
    counts = {'modis': 0, 'viirs': 0}

    with conn.transaction():
        for table in ('modis', 'viirs'):
            cnt = conn.execute(sql.SQL('SELECT count(*) FROM public.{}').format(sql.Identifier(table))).fetchone()[0]
            if cnt > 0:
                if not force:
                    print(f'    La tabla {table} ya contiene {cnt:,} filas. (Usa --force para reiniciar).')
                    continue
                print(f'    Limpiando {table} (--force activado)...')
                conn.execute(sql.SQL('TRUNCATE TABLE public.{}').format(sql.Identifier(table)))

        for folder, table, satellites in SOURCE_FOLDERS:
            folder_path = data_dir / folder
            if not folder_path.exists():
                print(f'    Carpeta no encontrada: {folder_path}, saltando.')
                continue

            for prefix in ('fire_archive_', 'fire_nrt_'):
                matches = sorted(folder_path.glob(prefix + '*.json'))
                if not matches:
                    continue
                file_path = matches[0]
                print(f'    Leyendo {file_path.name} -> {table}...', flush=True)
                t0 = time.time()
                file_count = 0
                copy_stmt = sql.SQL('COPY public.{} ({}) FROM STDIN').format(
                    sql.Identifier(table),
                    sql.SQL(',').join(map(sql.Identifier, COLUMNS_FIRMS))
                )
                with file_path.open('rb') as src, conn.cursor() as cur:
                    with cur.copy(copy_stmt) as copy:
                        for record in ijson.items(src, 'item', use_float=True):
                            copy.write_row(raw_firms_row(record, satellites, deps))
                            file_count += 1
                dt = time.time() - t0
                counts[table] += file_count
                print(f'      {file_count:,} registros cargados en {dt:.1f}s ({file_count/max(dt,0.1):.0f} rec/s)', flush=True)

    print('==> 4. Creando índices optimizados en modis y viirs...', flush=True)
    with conn.cursor() as cur:
        cur.execute(INDEX_DDL)
    conn.commit()
    print('    Índices listos.', flush=True)


def step_populate_datos_armonizados(conn, force=False):
    print('==> 5. Generando tabla de indicadores semanales datos_armonizados (2000-2026)...', flush=True)
    cnt = conn.execute('SELECT count(*) FROM public.datos_armonizados').fetchone()[0]
    if cnt > 0 and not force:
        print(f'    La tabla datos_armonizados ya tiene {cnt:,} filas. (Usa --force para regenerar).')
        return

    regions = list(departments().values())
    sources = conn.execute("""SELECT 'MODIS' AS sensor, min(acq_date)::date AS first, max(acq_date)::date AS last, count(*) AS total FROM public.modis
        UNION ALL SELECT 'VIIRS' AS sensor, min(acq_date)::date, max(acq_date)::date, count(*) FROM public.viirs WHERE satellite='SNPP'""").fetchall()

    if len(sources) < 2 or any(not row[3] for row in sources):
        print('    AVISO: Se requieren observaciones en modis y viirs para calcular indicadores semanales.')
        return

    starts = {row[0]: row[1] for row in sources}
    ends = {row[0]: row[2] for row in sources}

    print('    Calculando celdas-día con PostGIS por departamento...', flush=True)
    with conn.transaction():
        conn.execute('TRUNCATE TABLE public.datos_armonizados')
        conn.execute('CREATE TEMP TABLE regiones_arm (nombre text PRIMARY KEY, srid integer NOT NULL) ON COMMIT DROP')
        with conn.cursor() as cur:
            cur.executemany('INSERT INTO regiones_arm VALUES (%s,%s)', [(r['name'], r['srid']) for r in regions])

        rows = conn.execute("""WITH observaciones AS (
            SELECT departamento, 'MODIS'::text AS sensor, acq_date, latitude, longitude FROM public.modis
              WHERE departamento IS NOT NULL AND acq_date >= '2000-01-01' AND acq_date < '2027-01-01'
            UNION ALL
            SELECT departamento, 'VIIRS'::text AS sensor, acq_date, latitude, longitude FROM public.viirs
              WHERE satellite='SNPP' AND departamento IS NOT NULL AND acq_date >= '2000-01-01' AND acq_date < '2027-01-01'
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
            by_department[row[0]].append({'departamento': row[0], 'sensor': row[1], 'day': row[2], 'cells': row[3]})

        def status_str(week):
            if week['combined'] is not None:
                return 'comparable_experimental'
            sensors = week['sensors']
            if any(sensors[s]['cells'] is None for s in ('MODIS', 'VIIRS')):
                return 'semana_o_fuente_incompleta'
            if any(sensors[s]['percentile'] is None for s in ('MODIS', 'VIIRS')):
                return 'referencia_insuficiente'
            return 'empates_excesivos'

        stmt = sql.SQL("""INSERT INTO public.datos_armonizados (
            departamento, anio, semana_inicio, semana_fin, semana_iso, cuadricula_km, epsg,
            modis_celdas_dia, viirs_suomi_celdas_dia, modis_percentil, viirs_suomi_percentil,
            modis_semanas_referencia, viirs_semanas_referencia, modis_anios_referencia, viirs_anios_referencia,
            modis_fraccion_empates, viirs_fraccion_empates, indice_combinado, diferencia_sensores,
            estado, ultimo_registro_modis, ultimo_registro_viirs
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""")

        total_semanas = 0
        for region in regions:
            dept_rows = by_department[region['name']]
            dept_count = 0
            for year in range(2000, 2027):
                for week in weekly_analysis(dept_rows, ends, year, starts):
                    m, v = week['sensors']['MODIS'], week['sensors']['VIIRS']
                    conn.execute(stmt, (
                        region['name'], year, week['start'], week['end'], week['week'], 5, region['srid'],
                        m['cells'], v['cells'], m['percentile'], v['percentile'], m['sample'], v['sample'],
                        m['years'], v['years'], m['ties'], v['ties'], week['combined'], week['disagreement'],
                        status_str(week), ends['MODIS'], ends['VIIRS']
                    ))
                    dept_count += 1
            total_semanas += dept_count

    print(f'    datos_armonizados generado exitosamente: {total_semanas:,} semanas registradas.', flush=True)


def verify_database(conn):
    print('\n================ RESUMEN DE LA BASE DE DATOS LOCAL ================', flush=True)
    tables = [
        'public.modis',
        'public.viirs',
        'public.calendario_quemas',
        'public.calendario_lineas_base',
        'public.datos_armonizados'
    ]
    for tbl in tables:
        try:
            cnt = conn.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.SQL(tbl))).fetchone()[0]
            print(f'  ✓ {tbl:<32}: {cnt:>10,} filas')
        except Exception as e:
            print(f'  ✗ {tbl:<32}: Error ({e})')

    # Chequeo específico de Huánuco
    huc_modis = conn.execute("SELECT count(*) FROM public.modis WHERE departamento = 'Huánuco'").fetchone()[0]
    huc_viirs = conn.execute("SELECT count(*) FROM public.viirs WHERE departamento = 'Huánuco'").fetchone()[0]
    print(f'\n  Focos en Huánuco:')
    print(f'    - MODIS: {huc_modis:,} detecciones')
    print(f'    - VIIRS: {huc_viirs:,} detecciones')
    print('====================================================================\n', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--force', action='store_true', help='Sobrescribe datos si ya existen')
    parser.add_argument('--skip-firms', action='store_true', help='Salta la importación pesada de JSON FIRMS')
    parser.add_argument('--skip-weekly', action='store_true', help='Salta la generación de datos_armonizados')
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'data' / 'modisViirs')
    args = parser.parse_args()

    config = database_config()
    print(f"Conectando a PostgreSQL local en {config['host']}:{config['port']} (BD: {config['dbname']}, usuario: {config['user']})...")
    with psycopg.connect(**config) as conn:
        step_create_tables(conn)
        step_import_calendar(conn, force=args.force)
        if not args.skip_firms:
            step_import_raw_firms(conn, args.data_dir, force=args.force)
        if not args.skip_weekly:
            step_populate_datos_armonizados(conn, force=args.force)
        verify_database(conn)

    print('Configuración de base de datos local completada con éxito.')


if __name__ == '__main__':
    main()
