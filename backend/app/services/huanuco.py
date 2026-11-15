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
       FROM fire_detections, area WHERE acquired_at >= '2016-01-01' AND acquired_at < '2027-01-01'
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


def points(conn, start, end, confidence, fire_type, code='PE-HUC'):
    return conn.execute("""WITH area AS MATERIALIZED (SELECT ST_UnaryUnion(ST_SetSRID(ST_GeomFromGeoJSON(%(shape)s),4326)) AS g)
     SELECT id, latitude, longitude, acquired_at, sensor, satellite, confidence, frp, brightness, scan, track, daynight, version, source_kind
     FROM fire_detections, area WHERE acquired_at >= %(start)s AND acquired_at < %(end)s
     AND geom && area.g AND ST_Covers(area.g,geom) """ + FILTER + " ORDER BY acquired_at DESC, id DESC LIMIT 20001",
     {'shape': geometry(code), 'start': start, 'end': end + timedelta(days=1), 'confidence': confidence, 'fire_type': fire_type}).fetchall()


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
