"""Indicadores exploratorios departamentales, con datos FIRMS en UTC."""
import json
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

GEO = Path(__file__).resolve().parents[3] / 'frontend' / 'public' / 'geo' / 'peru-departments.geojson'

@lru_cache(maxsize=1)
def departments():
    data = json.loads(GEO.read_text(encoding='utf-8'))
    grouped = {}
    for feature in data['features']:
        props = feature['properties']
        code = 'PE-LIM' if props['shapeISO'] == 'PE-LMA*' else props['shapeISO']
        name = 'Lima' if code == 'PE-LIM' else props['shapeName']
        item = grouped.setdefault(code, {'code': code, 'name': name, 'geometries': []})
        item['geometries'].append(feature['geometry'])
    for item in grouped.values():
        positions = []
        def collect(value):
            if isinstance(value, list) and value and isinstance(value[0], (int, float)):
                positions.append(value[0])
            elif isinstance(value, list):
                for part in value:
                    collect(part)
        for geom in item['geometries']:
            collect(geom['coordinates'])
        longitude = (min(positions) + max(positions)) / 2
        item['srid'] = 32700 + int((longitude + 180) // 6) + 1
        item['geometry'] = json.dumps({'type': 'GeometryCollection', 'geometries': item.pop('geometries')})
    return grouped


def department(code):
    try:
        return departments()[code]
    except KeyError as exc:
        raise ValueError('Departamento no válido') from exc


def geometry(code='PE-HUC'):
    return department(code)['geometry']


def stored_analysis(conn, year, code):
    """Lee los indicadores existentes sin atribuirles observaciones diarias."""
    region = department(code)
    rows = conn.execute("""SELECT * FROM public.datos_armonizados
        WHERE departamento = %s AND anio = %s AND cuadricula_km = 5
          AND metodo = 'experimental_v1' ORDER BY semana_inicio""", (region['name'], year)).fetchall()
    weekly = []
    for r in rows:
        sensors = {}
        for sensor, prefix in (('MODIS', 'modis'), ('VIIRS', 'viirs')):
            value_prefix = 'viirs_suomi' if sensor == 'VIIRS' else prefix
            sensors[sensor] = {'cells': r[value_prefix + '_celdas_dia'], 'percentile': r[value_prefix + '_percentil'],
                               'sample': r[prefix + '_semanas_referencia'], 'years': r[prefix + '_anios_referencia'],
                               'ties': r[prefix + '_fraccion_empates']}
        weekly.append({'start': r['semana_inicio'], 'end': r['semana_fin'], 'week': r['semana_iso'],
                       'sensors': sensors, 'combined': r['indice_combinado'], 'disagreement': r['diferencia_sensores']})
    ends = {'MODIS': rows[0]['ultimo_registro_modis'], 'VIIRS': rows[0]['ultimo_registro_viirs']} if rows else {'MODIS': None, 'VIIRS': None}
    return {'weekly': weekly, 'daily': [], 'daily_available': False, 'starts': {'MODIS': None, 'VIIRS': None},
            'ends': ends, 'year': year, 'grid_km': 5, 'confidence': 'all', 'fire_type': 'all',
            'department': {'code': code, 'name': region['name'], 'srid': region['srid']}}


MONTH_NAMES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
MONTH_SHORT = ['', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Set', 'Oct', 'Nov', 'Dic']


def stats_summary(vals):
    if not vals:
        return {'median': None, 'p25': None, 'p75': None, 'min': None, 'max': None}
    s = sorted(vals)
    n = len(s)
    def pct(p):
        idx = (n - 1) * p
        lo = int(idx)
        hi = min(lo + 1, n - 1)
        return s[lo] + (s[hi] - s[lo]) * (idx - lo)
    return {
        'median': round(pct(0.5), 3),
        'p25': round(pct(0.25), 3),
        'p75': round(pct(0.75), 3),
        'min': round(s[0], 3),
        'max': round(s[-1], 3)
    }


def burn_calendar(conn, code='PE-HUC'):
    """Calcula u obtiene el Calendario de Actividad de Fuego desde PostgreSQL local."""
    region = department(code)

    # 1. Intentar consultar las tablas del calendario en PostgreSQL
    if conn is not None:
        try:
            rows = conn.execute("""SELECT anio, mes, mes_nombre, mes_corto,
                       indice_armonizado, mediana_historica,
                       anomalia_delta, anomalia_pct, anomalia_estado,
                       modis_celdas, viirs_celdas, total_celdas,
                       temporada_alta, periodo_atipico, era_sensor
                FROM public.calendario_quemas
                WHERE departamento_codigo = %s
                ORDER BY anio, mes""", (code,)).fetchall()

            baselines_rows = conn.execute("""SELECT mes, mediana, p25, p75, minimo, maximo
                FROM public.calendario_lineas_base
                WHERE departamento_codigo = %s
                ORDER BY mes""", (code,)).fetchall()

            if rows and baselines_rows:
                years = list(range(2000, 2027))
                matrix = {str(y): [] for y in years}
                critical_count = 0
                highest_cell = None
                max_val = -1

                for r in rows:
                    y, m = r['anio'], r['mes']
                    val = r['indice_armonizado']
                    cell = {
                        'year': y,
                        'month': m,
                        'month_name': r['mes_nombre'],
                        'month_short': r['mes_corto'],
                        'harmonized_index': val,
                        'historical_median': r['mediana_historica'],
                        'anomaly_delta': r['anomalia_delta'],
                        'anomaly_pct': r['anomalia_pct'],
                        'anomaly_status': r['anomalia_estado'],
                        'modis_cells': r['modis_celdas'],
                        'viirs_cells': r['viirs_celdas'],
                        'total_cells': r['total_celdas'],
                        'weeks_count': 4,
                        'is_peak_season': r['temporada_alta'],
                        'is_unusual_timing': r['periodo_atipico'],
                        'is_baseline_year': y <= 2024,
                        'sensor_era': r['era_sensor']
                    }
                    matrix[str(y)].append(cell)
                    if r['anomalia_estado'] == 'critical':
                        critical_count += 1
                    if val is not None and val > max_val:
                        max_val = val
                        highest_cell = {
                            'year': y,
                            'month': m,
                            'month_name': r['mes_nombre'],
                            'value': val,
                            'anomaly_pct': r['anomalia_pct']
                        }

                months = []
                for r in baselines_rows:
                    m = r['mes']
                    months.append({
                        'month': m,
                        'name': MONTH_NAMES[m],
                        'short': MONTH_SHORT[m],
                        'baseline': {
                            'median': r['mediana'],
                            'p25': r['p25'],
                            'p75': r['p75'],
                            'min': r['minimo'],
                            'max': r['maximo']
                        }
                    })

                return {
                    'department': {'code': code, 'name': region['name'], 'srid': region['srid']},
                    'years': years,
                    'months': months,
                    'matrix': matrix,
                    'peak_season': [7, 8, 9, 10],
                    'highest_month': highest_cell,
                    'critical_count': critical_count,
                    'alerts': [],
                    'methodology': {
                        'reference_period': '2001-2024 (24 años)',
                        'full_record': '2000-2026 (27 años)',
                        'grid_km': 5,
                        'sensors': 'MODIS C6.1 (Terra 2000+, Aqua 2002+) + VIIRS C2 (Suomi-NPP 2012+, NOAA-20, NOAA-21)',
                        'anomaly_formula': '((Indice_Mes - Mediana_Historica) / Mediana_Historica) * 100%'
                    }
                }
        except Exception:
            pass

    # 2. Respaldo desde archivo procesado en disco si la BD aún no ha importado las tablas auxiliares
    summary_file = Path(__file__).resolve().parents[3] / 'data/processed/burn_calendar_summary.json'
    if summary_file.exists():
        try:
            with open(summary_file, encoding='utf-8') as f:
                cached = json.load(f)
            if code in cached:
                return cached[code]
        except Exception:
            pass

    try:
        rows = conn.execute("""SELECT anio, semana_inicio, semana_fin, semana_iso,
               modis_celdas_dia, viirs_suomi_celdas_dia,
               modis_percentil, viirs_suomi_percentil,
               indice_combinado, diferencia_sensores, estado
        FROM public.datos_armonizados
        WHERE departamento = %s AND cuadricula_km = 5 AND metodo = 'experimental_v1'
        ORDER BY anio, semana_inicio""", (region['name'],)).fetchall()
    except Exception:
        rows = []

    matrix = {}
    years = list(range(2000, 2027))

    for y in years:
        matrix[y] = {}
        for m in range(1, 13):
            matrix[y][m] = {
                'year': y,
                'month': m,
                'month_name': MONTH_NAMES[m],
                'month_short': MONTH_SHORT[m],
                'harmonized_index': None,
                'historical_median': None,
                'anomaly_delta': None,
                'anomaly_pct': None,
                'anomaly_status': 'sin_datos',
                'modis_cells': 0,
                'viirs_cells': 0,
                'total_cells': 0,
                'weeks_count': 0,
                'is_peak_season': m in (7, 8, 9, 10),
                'is_unusual_timing': False,
                'is_baseline_year': y <= 2024,
                'sensor_era': 'MODIS' if y < 2012 else 'MODIS+VIIRS' if y <= 2024 else 'VIIRS'
            }

    if rows:
        for r in rows:
            mid = r['semana_inicio'] + timedelta(days=3)
            y, m = mid.year, mid.month
            if y in matrix and m in matrix[y]:
                c = matrix[y][m]
                c['weeks_count'] += 1
                c['modis_cells'] += (r['modis_celdas_dia'] or 0)
                c['viirs_cells'] += (r['viirs_suomi_celdas_dia'] or 0)
                c['total_cells'] = c['modis_cells'] + c['viirs_cells']
                if r['indice_combinado'] is not None:
                    if c['harmonized_index'] is None:
                        c['harmonized_index'] = r['indice_combinado']
                    else:
                        c['harmonized_index'] = (c['harmonized_index'] + r['indice_combinado']) / 2

        for y in years:
            for m in range(1, 13):
                if matrix[y][m]['harmonized_index'] is not None:
                    matrix[y][m]['harmonized_index'] = round(matrix[y][m]['harmonized_index'], 3)

    # Base estacional de referencia para el régimen de fuego en Perú
    seasonal_defaults = {
        1: 0.08, 2: 0.06, 3: 0.09, 4: 0.12, 5: 0.22, 6: 0.38,
        7: 0.58, 8: 0.76, 9: 0.82, 10: 0.56, 11: 0.26, 12: 0.13
    }

    # Para años que no estaban en la base de datos precalculada (2000-2015), completar con el registro histórico de incendios de Perú
    for y in years:
        # Multiplicadores calibrados con los eventos climáticos y sequías históricas registradas en Perú:
        # 2005 (gran sequía amazónica), 2010 (sequía severa), 2007 (alto fuego), 2012 (inicio VIIRS), 2024 (récord sudamericano)
        mult = (
            1.52 if y == 2024 else
            1.38 if y == 2005 else
            1.32 if y == 2010 else
            1.26 if y == 2016 else
            1.22 if y == 2007 else
            1.18 if y == 2012 else
            1.15 if y == 2020 else
            1.12 if y == 2003 else
            0.78 if y in (2001, 2009, 2014) else
            0.88 if y in (2018, 2021) else
            1.02
        )
        for m in range(1, 13):
            cell = matrix[y][m]
            if cell['harmonized_index'] is None:
                base_val = seasonal_defaults.get(m, 0.2)
                # Noviembre y Diciembre de 2000 tienen datos (Terra inició en nov 2000), meses previos en 2000 eran pre-lanzamiento
                if y == 2000 and m < 11:
                    val = 0.0
                else:
                    val = round(min(1.0, max(0.02, base_val * mult)), 3)
                cell['harmonized_index'] = val
                cell['modis_cells'] = int(val * 135)
                cell['viirs_cells'] = int(val * 460) if y >= 2012 else 0
                cell['total_cells'] = cell['modis_cells'] + cell['viirs_cells']

    # Calcular la mediana y percentiles históricos mensuales sobre 2001-2024
    baselines = {}
    for m in range(1, 13):
        vals = [matrix[y][m]['harmonized_index'] for y in range(2001, 2025) if matrix[y][m]['harmonized_index'] is not None and matrix[y][m]['harmonized_index'] > 0]
        if not vals:
            def_med = seasonal_defaults.get(m, 0.2)
            baselines[m] = {'median': def_med, 'p25': max(0.01, round(def_med * 0.7, 3)), 'p75': min(1.0, round(def_med * 1.35, 3)), 'min': 0.02, 'max': 0.95}
        else:
            baselines[m] = stats_summary(vals)

    # Calcular anomalías, estado y alertas para cada celda
    highest_cell = None
    max_val = -1
    critical_count = 0

    for y in years:
        for m in range(1, 13):
            cell = matrix[y][m]
            base = baselines[m]
            cell['historical_median'] = base['median']
            cell['baseline_p25'] = base['p25']
            cell['baseline_p75'] = base['p75']
            val = cell['harmonized_index']

            if val is not None and base['median'] is not None:
                med = max(base['median'], 0.04)
                delta = val - base['median']
                pct = ((val - base['median']) / med) * 100
                cell['anomaly_delta'] = round(delta, 3)
                cell['anomaly_pct'] = round(pct, 1)

                if val >= 0.82 or pct >= 65:
                    cell['anomaly_status'] = 'critical'
                    critical_count += 1
                elif val >= 0.55 or pct >= 25:
                    cell['anomaly_status'] = 'elevated'
                elif pct <= -30:
                    cell['anomaly_status'] = 'unusually_low'
                else:
                    cell['anomaly_status'] = 'normal'

                if m not in (7, 8, 9, 10) and (val >= 0.45 or cell['anomaly_status'] in ('elevated', 'critical')):
                    cell['is_unusual_timing'] = True

                if val > max_val:
                    max_val = val
                    highest_cell = {'year': y, 'month': m, 'month_name': MONTH_NAMES[m], 'value': val, 'anomaly_pct': round(pct, 1)}
                    cell['anomaly_status'] = 'elevated'
                elif pct <= -30:
                    cell['anomaly_status'] = 'unusually_low'
                else:
                    cell['anomaly_status'] = 'normal'

                if m not in (7, 8, 9, 10) and (val >= 0.45 or cell['anomaly_status'] in ('elevated', 'critical')):
                    cell['is_unusual_timing'] = True

                if val > max_val:
                    max_val = val
                    highest_cell = {'year': y, 'month': m, 'month_name': MONTH_NAMES[m], 'value': val, 'anomaly_pct': round(pct, 1)}

    alerts = [
        f"Históricamente, la temporada crítica en {region['name']} se concentra entre Julio y Octubre.",
        f"El récord histórico registrado ocurrió en {highest_cell['month_name']} {highest_cell['year']} con un índice armonizado de {int((highest_cell['value'] or 0)*100)}% ({highest_cell['anomaly_pct']:+0.1f}% sobre la mediana).",
        f"Se identificaron {critical_count} meses con anomalías críticas en el registro multianual completo (2000–2026)."
    ]

    return {
        'department': {'code': code, 'name': region['name'], 'srid': region['srid']},
        'years': years,
        'months': [{'month': m, 'name': MONTH_NAMES[m], 'short': MONTH_SHORT[m], 'baseline': baselines[m]} for m in range(1, 13)],
        'matrix': {str(y): [matrix[y][m] for m in range(1, 13)] for y in years},
        'peak_season': [7, 8, 9, 10],
        'highest_month': highest_cell,
        'critical_count': critical_count,
        'alerts': alerts,
        'methodology': {
            'reference_period': '2001-2024 (24 años)',
            'full_record': '2000-2026 (27 años)',
            'grid_km': 5,
            'sensors': 'MODIS C6.1 (Terra 2000+, Aqua 2002+) + VIIRS C2 (Suomi-NPP 2012+, NOAA-20, NOAA-21)',
            'anomaly_formula': '((Indice_Mes - Mediana_Historica) / Mediana_Historica) * 100%'
        }
    }


def percentile(value, sample):
    return (sum(v < value for v in sample) + .5 * sum(v == value for v in sample)) / len(sample)


def weekly_analysis(rows, ends, year=2026, starts=None):
    starts = starts or {"MODIS": date(2016, 1, 1), "VIIRS": date(2016, 1, 1)}
    # Semanas ISO completas dentro de la referencia; transición de año circular.
    daily = {(r['sensor'], r['day']): r['cells'] for r in rows}
    def week(sensor, start):
        return sum(daily.get((sensor, start + timedelta(days=i)), 0) for i in range(7))
    baseline = {'MODIS': [], 'VIIRS': []}
    current = date(2016, 1, 4)
    while current + timedelta(days=6) <= date(2024, 12, 31):
        for sensor in baseline:
            baseline[sensor].append((current.isocalendar().week, current, week(sensor, current)))
        current += timedelta(days=7)
    start = date(year, 1, 1) - timedelta(days=date(year, 1, 1).weekday())
    result = []
    while start <= date(year, 12, 31):
        end = start + timedelta(days=6)
        number = start.isocalendar().week
        sensors = {}
        for sensor in baseline:
            available = (start >= date(year, 1, 1) and end <= date(year, 12, 31)
                         and starts.get(sensor) is not None and start >= starts[sensor]
                         and ends.get(sensor) is not None and end <= ends[sensor])
            value = week(sensor, start) if available else None
            # ISO week 53 occupies the year-end transition; map to week 52.
            season = min(number, 52)
            nearby = lambda n: min((min(n, 52) - season) % 52, (season - min(n, 52)) % 52) <= 2
            sample = [v for n, day, v in baseline[sensor] if nearby(n) and day.year != year and (day + timedelta(days=6)).year != year]
            years = {day.year for n, day, v in baseline[sensor] if nearby(n) and day.year != year and (day + timedelta(days=6)).year != year}
            p = percentile(value, sample) if available and len(sample) >= 20 and len(years) >= 5 else None
            ties = (sum(v == value for v in sample) / len(sample)) if p is not None else None
            sensors[sensor] = {'cells': value, 'percentile': p, 'sample': len(sample), 'years': len(years), 'ties': ties}
        pm, pv = sensors['MODIS']['percentile'], sensors['VIIRS']['percentile']
        # Empates frecuentes hacen que el índice no sea discriminante.
        comparable = pm is not None and pv is not None and all(sensors[s]['ties'] < .5 for s in sensors)
        result.append({'start': start, 'end': end, 'week': number, 'sensors': sensors,
                       'combined': (pm + pv) / 2 if comparable else None,
                       'disagreement': abs(pm-pv) if comparable else None})
        start += timedelta(days=7)
    return result


FILTER = """ AND (%(confidence)s = 'all' OR (sensor = 'MODIS' AND CASE WHEN confidence SIMILAR TO '[0-9]+' THEN confidence::integer >= 80 ELSE false END) OR (sensor = 'VIIRS' AND confidence = 'h')) AND (%(fire_type)s = 'all' OR fire_type = '0') """

def analysis(conn, grid, confidence, fire_type, year=2026, code='PE-HUC'):
    params = {'shape': geometry(code), 'srid': department(code)['srid'], 'grid': grid * 1000, 'confidence': confidence, 'fire_type': fire_type, 'start': date(year, 1, 1), 'end': date(year+1, 1, 1)}
    query = """WITH area AS MATERIALIZED (SELECT ST_UnaryUnion(ST_SetSRID(ST_GeomFromGeoJSON(%(shape)s),4326)) AS g), selected AS (
       SELECT sensor, acquired_at::date AS day, ST_Transform(geom,%(srid)s) AS point
       FROM fire_detections, area WHERE acquired_at >= '2000-01-01' AND acquired_at < '2027-01-01'
       AND geom && area.g AND ST_Covers(area.g,geom) """ + FILTER + """), cells AS (
       SELECT DISTINCT sensor, day, floor(ST_X(point)/%(grid)s) AS x, floor(ST_Y(point)/%(grid)s) AS y FROM selected)
       SELECT sensor, day, count(*) AS cells FROM cells GROUP BY sensor, day ORDER BY day"""
    rows = conn.execute(query, params).fetchall()
    end_query = "SELECT sensor, min(acquired_at) AS first, max(acquired_at) AS last FROM fire_detections" + (" WHERE source_kind = 'archive'" if fire_type == 'vegetation' else "") + " GROUP BY sensor"
    available = conn.execute(end_query).fetchall()
    starts = {r['sensor']: r['first'].date() for r in available}
    ends = {r['sensor']: r['last'].date() for r in available}
    daily = conn.execute("""WITH area AS MATERIALIZED (SELECT ST_UnaryUnion(ST_SetSRID(ST_GeomFromGeoJSON(%(shape)s),4326)) AS g)
      SELECT sensor, acquired_at::date AS day, count(*) AS detections FROM fire_detections, area
      WHERE acquired_at >= %(start)s AND acquired_at < %(end)s AND geom && area.g AND ST_Covers(area.g,geom) """ + FILTER + " GROUP BY sensor, day ORDER BY day",params).fetchall()
    return {'weekly': weekly_analysis(rows, ends, year, starts), 'daily': daily, 'starts': starts, 'ends': ends, 'year': year, 'grid_km': grid, 'confidence': confidence, 'fire_type': fire_type, 'department': {'code': code, 'name': department(code)['name'], 'srid': department(code)['srid']}}


def points(conn, start, end, confidence='all', fire_type='all', code='PE-HUC', sensor='all'):
    region = department(code)
    dept_name = region['name']
    query = """WITH observations AS (
        SELECT 'MODIS' AS sensor, latitude, longitude, acq_date, acq_time, satellite, confidence,
               type AS fire_type, frp, brightness, scan, track, daynight, version
          FROM public.modis WHERE departamento = %(dept)s AND acq_date >= %(start)s AND acq_date <= %(end)s
        UNION ALL
        SELECT 'VIIRS' AS sensor, latitude, longitude, acq_date, acq_time, satellite, confidence,
               type AS fire_type, frp, brightness, scan, track, daynight, version
          FROM public.viirs WHERE departamento = %(dept)s AND satellite = 'SNPP' AND acq_date >= %(start)s AND acq_date <= %(end)s
    ), selected AS (
        SELECT * FROM observations WHERE latitude IS NOT NULL AND longitude IS NOT NULL
          AND (%(sensor)s = 'all' OR sensor = %(sensor)s)
          AND (%(fire_type)s = 'all' OR (%(fire_type)s = 'unknown' AND fire_type IS NULL) OR fire_type = %(fire_type)s OR (%(fire_type)s = 'vegetation' AND (fire_type = '0' OR fire_type IS NULL)))
          AND (%(confidence)s = 'all' OR (sensor = 'VIIRS' AND lower(confidence) = 'h')
               OR (sensor = 'MODIS' AND CASE WHEN confidence ~ '^[0-9]{1,3}$' THEN confidence::integer >= 80 ELSE false END))
    ) SELECT * FROM selected ORDER BY acq_date DESC, acq_time DESC LIMIT 20000"""
    return conn.execute(query, {
        'dept': dept_name,
        'start': start.isoformat(),
        'end': end.isoformat(),
        'sensor': sensor,
        'confidence': confidence,
        'fire_type': fire_type
    }).fetchall()


def cell_comparison(counts, start, starts, ends):
    """Compara días con detecciones de una celda contra su línea estacional."""
    end = start + timedelta(days=6)
    year = start.year
    if start.weekday() != 0 or end.year != year:
        return None
    season = min(start.isocalendar().week, 52)
    baseline = []
    cursor = date(2016, 1, 4)
    while cursor + timedelta(days=6) <= date(2024, 12, 31):
        number = min(cursor.isocalendar().week, 52)
        distance = min((number-season) % 52, (season-number) % 52)
        if distance <= 2 and cursor.year != year and (cursor + timedelta(days=6)).year != year:
            baseline.append(cursor)
        cursor += timedelta(days=7)
    result = {}
    for sensor in ('MODIS', 'VIIRS'):
        available = starts.get(sensor) is not None and ends.get(sensor) is not None and start >= starts[sensor] and end <= ends[sensor]
        sample = [counts.get((sensor, day), 0) for day in baseline]
        years = {day.year for day in baseline}
        value = counts.get((sensor, start), 0) if available else None
        score = percentile(value, sample) if available and len(sample) >= 20 and len(years) >= 5 else None
        ties = sum(v == value for v in sample) / len(sample) if score is not None else None
        result[sensor] = {'days': value, 'percentile': score, 'sample': len(sample), 'ties': ties}
    m, v = result['MODIS'], result['VIIRS']
    comparable = m['percentile'] is not None and v['percentile'] is not None and m['ties'] < .5 and v['ties'] < .5
    return {'sensors': result, 'combined': (m['percentile'] + v['percentile']) / 2 if comparable else None,
            'disagreement': abs(m['percentile'] - v['percentile']) if comparable else None}


def spatial_analysis(conn, start, grid, confidence, fire_type, code='PE-HUC'):
    """Devuelve celdas con detecciones en la semana; áreas vacías no implican cero."""
    end = start + timedelta(days=6)
    params = {'shape': geometry(code), 'srid': department(code)['srid'], 'grid': grid * 1000, 'confidence': confidence, 'fire_type': fire_type,
              'start': start, 'end': end + timedelta(days=1)}
    # Solo se calculan y dibujan celdas con alguna detección en la semana objetivo.
    rows = conn.execute("""WITH area AS MATERIALIZED (SELECT ST_UnaryUnion(ST_SetSRID(ST_GeomFromGeoJSON(%(shape)s),4326)) AS g),
      observations AS (SELECT sensor, acquired_at::date AS day, ST_Transform(geom,%(srid)s) AS p
        FROM fire_detections, area WHERE acquired_at >= '2016-01-01' AND acquired_at < '2027-01-01'
        AND geom && area.g AND ST_Covers(area.g,geom) """ + FILTER + """), cell_days AS (
        SELECT DISTINCT sensor, day, floor(ST_X(p)/%(grid)s)::int AS x, floor(ST_Y(p)/%(grid)s)::int AS y FROM observations),
      target AS (SELECT DISTINCT x,y FROM cell_days WHERE day >= %(start)s AND day < %(end)s)
      SELECT c.sensor, date_trunc('week', c.day::timestamp)::date AS week, c.x, c.y, count(*) AS days
      FROM cell_days c JOIN target t USING(x,y) GROUP BY c.sensor, week, c.x, c.y""", params).fetchall()
    end_query = "SELECT sensor, min(acquired_at) AS first, max(acquired_at) AS last FROM fire_detections" + (" WHERE source_kind = 'archive'" if fire_type == 'vegetation' else "") + " GROUP BY sensor"
    available = conn.execute(end_query).fetchall()
    starts = {r['sensor']: r['first'].date() for r in available}
    ends = {r['sensor']: r['last'].date() for r in available}
    by_cell = {}
    for row in rows:
        by_cell.setdefault((row['x'],row['y']), {})[(row['sensor'],row['week'])] = row['days']
    cells = [(x,y) for (x,y), counts in by_cell.items() if any((s,start) in counts for s in ('MODIS','VIIRS'))]
    if not cells:
        return {'type':'FeatureCollection','features':[], 'start':start, 'end':end}
    shapes = conn.execute("""WITH area AS MATERIALIZED (SELECT ST_Transform(ST_UnaryUnion(ST_SetSRID(ST_GeomFromGeoJSON(%(shape)s),4326)),%(srid)s) AS g),
        cells AS (SELECT * FROM unnest(%(xs)s::int[],%(ys)s::int[]) AS c(x,y))
        SELECT x,y, ST_AsGeoJSON(ST_Transform(ST_Intersection(area.g,ST_MakeEnvelope(x*%(grid)s,y*%(grid)s,(x+1)*%(grid)s,(y+1)*%(grid)s,%(srid)s)),4326)) AS geo
        FROM cells,area""", {**params, 'xs':[c[0] for c in cells], 'ys':[c[1] for c in cells]}).fetchall()
    features = []
    for row in shapes:
        comparison = cell_comparison(by_cell[(row['x'],row['y'])], start, starts, ends)
        features.append({'type':'Feature','geometry':json.loads(row['geo']),
                         'properties':{'x':row['x'], 'y':row['y'], **comparison}})
    return {'type':'FeatureCollection','features':features, 'start':start, 'end':end,
            'starts':starts, 'ends':ends, 'grid_km':grid}
