"""Indicadores exploratorios de Huánuco, con datos FIRMS en UTC."""
import json
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

GEO = Path(__file__).resolve().parents[3] / 'frontend' / 'public' / 'geo' / 'peru-departments.geojson'

@lru_cache(maxsize=1)
def geometry():
    data = json.loads(GEO.read_text(encoding='utf-8'))
    return json.dumps(next(f['geometry'] for f in data['features'] if f['properties']['shapeISO'] == 'PE-HUC'))


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

def analysis(conn, grid, confidence, fire_type, year=2026):
    params = {'shape': geometry(), 'grid': grid * 1000, 'confidence': confidence, 'fire_type': fire_type, 'start': date(year, 1, 1), 'end': date(year+1, 1, 1)}
    query = """WITH area AS (SELECT ST_SetSRID(ST_GeomFromGeoJSON(%(shape)s),4326) AS g), selected AS (
       SELECT sensor, acquired_at::date AS day, ST_Transform(geom,32718) AS point
       FROM fire_detections, area WHERE acquired_at >= '2016-01-01' AND acquired_at < '2027-01-01'
       AND geom && area.g AND ST_Covers(area.g,geom) """ + FILTER + """), cells AS (
       SELECT DISTINCT sensor, day, floor(ST_X(point)/%(grid)s) AS x, floor(ST_Y(point)/%(grid)s) AS y FROM selected)
       SELECT sensor, day, count(*) AS cells FROM cells GROUP BY sensor, day ORDER BY day"""
    rows = conn.execute(query, params).fetchall()
    end_query = "SELECT sensor, min(acquired_at) AS first, max(acquired_at) AS last FROM fire_detections" + (" WHERE source_kind = 'archive'" if fire_type == 'vegetation' else "") + " GROUP BY sensor"
    available = conn.execute(end_query).fetchall()
    starts = {r['sensor']: r['first'].date() for r in available}
    ends = {r['sensor']: r['last'].date() for r in available}
    daily = conn.execute("""WITH area AS (SELECT ST_SetSRID(ST_GeomFromGeoJSON(%(shape)s),4326) AS g)
      SELECT sensor, acquired_at::date AS day, count(*) AS detections FROM fire_detections, area
      WHERE acquired_at >= %(start)s AND acquired_at < %(end)s AND geom && area.g AND ST_Covers(area.g,geom) """ + FILTER + " GROUP BY sensor, day ORDER BY day",params).fetchall()
    return {'weekly': weekly_analysis(rows, ends, year, starts), 'daily': daily, 'starts': starts, 'ends': ends, 'year': year, 'grid_km': grid, 'confidence': confidence, 'fire_type': fire_type}


def points(conn, start, end, confidence, fire_type):
    return conn.execute("""WITH area AS (SELECT ST_SetSRID(ST_GeomFromGeoJSON(%(shape)s),4326) AS g)
     SELECT id, latitude, longitude, acquired_at, sensor, satellite, confidence, frp, brightness, scan, track, daynight, version, source_kind
     FROM fire_detections, area WHERE acquired_at >= %(start)s AND acquired_at < %(end)s
     AND geom && area.g AND ST_Covers(area.g,geom) """ + FILTER + " ORDER BY acquired_at DESC, id DESC LIMIT 20001",
     {'shape': geometry(), 'start': start, 'end': end + timedelta(days=1), 'confidence': confidence, 'fire_type': fire_type}).fetchall()
