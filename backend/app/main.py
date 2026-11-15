from datetime import date, datetime, time, timedelta, timezone
import os

import psycopg
from fastapi import FastAPI, HTTPException, Query
from psycopg.rows import dict_row

from .database import database_config

app = FastAPI(title='Brinco Alerta API', version='0.2.0')


@app.get('/api/huanuco/events/analysis')
def event_analysis():
    from .services.events import summary
    try:
        with connection(events=True) as conn:
            return summary(conn)
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    except psycopg.Error as exc:
        raise HTTPException(503, 'No se pudieron consultar los eventos de Huánuco.') from exc


@app.get('/api/huanuco/events')
def event_points(start: date = date(2026,1,1), end: date = date(2026,12,31), month: int | None = None):
    from .services.events import points
    if month is not None:
        if month < 1 or month > 12:
            raise HTTPException(422, 'Mes debe estar entre 1 y 12.')
        start = date(2026, month, 1)
        end = date(2027, 1, 1) - timedelta(days=1) if month == 12 else date(2026, month + 1, 1) - timedelta(days=1)
    if start.year != 2026 or end.year != 2026 or end < start:
        raise HTTPException(422, 'Seleccione un intervalo válido dentro de 2026.')
    try:
        with connection(events=True) as conn:
            return points(conn, start, end)
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    except psycopg.Error as exc:
        raise HTTPException(503, 'No se pudieron consultar los eventos de Huánuco.') from exc


@app.get('/api/huanuco/events/{event_id}')
def event_detail(event_id: int):
    from .services.events import detail
    if event_id < 1:
        raise HTTPException(422, 'Identificador de evento inválido.')
    try:
        with connection(events=True) as conn:
            result = detail(conn, event_id)
        if result is None:
            raise HTTPException(404, 'Evento no disponible en la ejecución activa de Huánuco.')
        return result
    except psycopg.Error as exc:
        raise HTTPException(503, 'No se pudo consultar el detalle del evento.') from exc


@app.get('/api/huanuco/land-cover')
def huanuco_land_cover():
    from .services.screening import metadata
    return metadata()


@app.get('/api/huanuco/screened/analysis')
def screened_analysis(decision: str = 'candidate', cover: str = 'all', confidence: str = 'all'):
    from .services.screening import summary
    try:
        with connection() as conn:
            return summary(conn, decision, cover, confidence)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except psycopg.Error as exc:
        raise HTTPException(503, 'No se pudieron consultar las evaluaciones. Prepare primero la capa de Huánuco.') from exc


@app.get('/api/huanuco/screened/points')
def screened_points(start: date, end: date, decision: str = 'candidate', cover: str = 'all', confidence: str = 'all'):
    from .services.screening import points
    if start.year != 2026 or end.year != 2026 or end < start:
        raise HTTPException(422, 'Seleccione un intervalo válido dentro de 2026.')
    try:
        with connection() as conn:
            return points(conn, start, end, decision, cover, confidence)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except psycopg.Error as exc:
        raise HTTPException(503, 'No se pudieron consultar las observaciones evaluadas.') from exc


def connection(events=False):
    try:
        if events and os.environ.get('DB_DATA_SOURCE') == 'armonizados' and not os.environ.get('EVENTS_DB_HOST'):
            raise ValueError('Para mostrar eventos en el mapa configure la conexión EVENTS_DB_* a una base con eventos de Huánuco.')
        source = 'EVENTS' if events and os.environ.get('EVENTS_DB_HOST') else None
        return psycopg.connect(**database_config(source), row_factory=dict_row, options='-c timezone=UTC')
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    except psycopg.Error:
        raise HTTPException(503, 'No se pudo conectar a PostgreSQL')


@app.get('/api/health')
def health():
    return {'status': 'ok'}


@app.get('/api/huanuco/observations')
def raw_huanuco_observations(start: date, end: date, sensor: str = 'all', confidence: str = 'all', fire_type: str = 'all'):
    if not 2016 <= start.year <= 2026 or end.year != start.year or end < start or sensor not in ('all', 'MODIS', 'VIIRS') or confidence not in ('all', 'high') or fire_type not in ('all', '0', '1', '2', '3', 'unknown'):
        raise HTTPException(422, 'Seleccione un intervalo dentro de un año entre 2016 y 2026 y filtros válidos.')
    query = """WITH observations AS (
        SELECT 'MODIS' AS sensor, latitude, longitude, acq_date, acq_time, satellite, confidence,
               type AS fire_type, frp, brightness, scan, track, daynight, version
          FROM public.modis WHERE departamento = 'Huánuco' AND acq_date >= %(start)s AND acq_date <= %(end)s
        UNION ALL
        SELECT 'VIIRS' AS sensor, latitude, longitude, acq_date, acq_time, satellite, confidence,
               type AS fire_type, frp, brightness, scan, track, daynight, version
          FROM public.viirs WHERE departamento = 'Huánuco' AND satellite = 'SNPP' AND acq_date >= %(start)s AND acq_date <= %(end)s
    ), selected AS (
        SELECT * FROM observations WHERE latitude IS NOT NULL AND longitude IS NOT NULL
          AND (%(sensor)s = 'all' OR sensor = %(sensor)s)
          AND (%(fire_type)s = 'all' OR (%(fire_type)s = 'unknown' AND fire_type IS NULL) OR fire_type = %(fire_type)s)
          AND (%(confidence)s = 'all' OR (sensor = 'VIIRS' AND lower(confidence) = 'h')
               OR (sensor = 'MODIS' AND CASE WHEN confidence ~ '^[0-9]{1,3}$' THEN confidence::integer >= 80 ELSE false END))
    ) SELECT *, count(*) OVER () AS total FROM selected ORDER BY acq_date DESC, acq_time DESC LIMIT 20000"""
    try:
        with connection() as conn:
            rows = conn.execute(query, {'start': start.isoformat(), 'end': end.isoformat(), 'sensor': sensor, 'confidence': confidence, 'fire_type': fire_type}).fetchall()
        total = rows[0]['total'] if rows else 0
        for row in rows:
            row.pop('total')
        return {'data': rows, 'total': total, 'truncated': total > len(rows)}
    except psycopg.Error as exc:
        raise HTTPException(503, 'No se pudieron consultar las observaciones de Huánuco.') from exc


def bounds(start: date, end: date):
    if end < start or (end - start).days > 366:
        raise HTTPException(422, 'El intervalo debe ser válido y no superar 367 días')
    return (datetime.combine(start, time.min, tzinfo=timezone.utc),
            datetime.combine(end + timedelta(days=1), time.min, tzinfo=timezone.utc))


@app.get('/api/status')
def status():
    with connection() as conn:
        try:
            return conn.execute('SELECT count(*) AS total, min(acquired_at) AS first, max(acquired_at) AS last FROM fire_detections').fetchone()
        except psycopg.Error:
            raise HTTPException(503, 'La base no está inicializada; ejecute la importación')


@app.get('/api/fires')
def fires(start: date, end: date, limit: int = Query(5000, ge=1, le=20000), offset: int = Query(0, ge=0)):
    lo, hi = bounds(start, end)
    with connection() as conn:
        try:
            total = conn.execute('SELECT count(*) AS n FROM fire_detections WHERE acquired_at >= %s AND acquired_at < %s', (lo, hi)).fetchone()['n']
            rows = conn.execute('SELECT id, latitude, longitude, acquired_at, sensor, satellite, confidence, frp, brightness, bright_t31, scan, track, daynight, fire_type, version, source_kind FROM fire_detections WHERE acquired_at >= %s AND acquired_at < %s ORDER BY acquired_at DESC, id DESC LIMIT %s OFFSET %s', (lo, hi, limit, offset)).fetchall()
            return {'data': rows, 'total': total, 'limit': limit, 'offset': offset}
        except psycopg.Error:
            raise HTTPException(503, 'No se pudieron consultar las detecciones')


@app.get('/api/daily')
def daily(start: date, end: date):
    lo, hi = bounds(start, end)
    with connection() as conn:
        try:
            rows = conn.execute("SELECT (acquired_at AT TIME ZONE 'UTC')::date AS day, sensor, count(*) AS count FROM fire_detections WHERE acquired_at >= %s AND acquired_at < %s GROUP BY 1, 2 ORDER BY 1, 2", (lo, hi)).fetchall()
            return {'data': rows}
        except psycopg.Error:
            raise HTTPException(503, 'No se pudieron consultar los agregados')


@app.get('/api/huanuco/analysis')
def huanuco_analysis(grid: int = 5, confidence: str = 'all', fire_type: str = 'all', year: int = 2026):
    from .services.huanuco import analysis
    if year < 2016 or year > 2026 or grid not in (2, 5, 10) or confidence not in ('all', 'high') or fire_type not in ('all', 'vegetation'):
        raise HTTPException(422, 'Filtros no válidos')
    try:
        with connection() as conn:
            return analysis(conn, grid, confidence, fire_type, year)
    except psycopg.Error as exc:
        raise HTTPException(503, 'No se pudo calcular el análisis') from exc


@app.get('/api/huanuco/points')
def huanuco_points(start: date, end: date, confidence: str = 'all', fire_type: str = 'all'):
    from .services.huanuco import points
    if start.year < 2016 or end.year > 2026 or start.year != end.year or end < start or (end-start).days > 366 or confidence not in ('all', 'high') or fire_type not in ('all', 'vegetation'):
        raise HTTPException(422, 'Intervalo o filtros no válidos')
    try:
        with connection() as conn:
            rows = points(conn, start, end, confidence, fire_type)
            return {'data': rows[:20000], 'truncated': len(rows) > 20000}
    except psycopg.Error as exc:
        raise HTTPException(503, 'No se pudieron consultar las observaciones') from exc


@app.get('/api/huanuco/cells')
def huanuco_cells(start: date, grid: int = 5, confidence: str = 'all', fire_type: str = 'all'):
    from .services.huanuco import spatial_analysis
    end = start + timedelta(days=6)
    if not 2016 <= start.year <= 2026 or start.weekday() != 0 or end.year != start.year or grid not in (2, 5, 10) or confidence not in ('all', 'high') or fire_type not in ('all', 'vegetation'):
        raise HTTPException(422, 'Se requiere una semana ISO completa dentro de un año y filtros válidos')
    try:
        with connection() as conn:
            return spatial_analysis(conn, start, grid, confidence, fire_type)
    except psycopg.Error as exc:
        raise HTTPException(503, 'No se pudo calcular la comparación por celda') from exc


@app.get('/api/departments')
def list_departments():
    from .services.huanuco import departments
    return {'data': sorted(({'code': d['code'], 'name': d['name'], 'srid': d['srid']} for d in departments().values()), key=lambda d: d['name'])}


def valid_department(code):
    from .services.huanuco import department
    try:
        return department(code)
    except ValueError as exc:
        raise HTTPException(404, 'Departamento no válido') from exc


@app.get('/api/departments/{code}/analysis')
def department_analysis(code: str, grid: int = 5, confidence: str = 'all', fire_type: str = 'all', year: int = 2026):
    from .services.huanuco import analysis, stored_analysis
    import os
    valid_department(code)
    if year < 2016 or year > 2026 or grid not in (2, 5, 10) or confidence not in ('all', 'high') or fire_type not in ('all', 'vegetation'):
        raise HTTPException(422, 'Filtros no válidos')
    try:
        with connection() as conn:
            if os.environ.get('DB_DATA_SOURCE') == 'armonizados':
                if grid != 5 or confidence != 'all' or fire_type != 'all':
                    raise HTTPException(422, 'Los datos almacenados solo admiten cuadrícula de 5 km y filtros sin aplicar')
                return stored_analysis(conn, year, code)
            return analysis(conn, grid, confidence, fire_type, year, code)
    except psycopg.Error as exc:
        raise HTTPException(503, 'No se pudo calcular el análisis') from exc


@app.get('/api/departments/{code}/points')
def department_points(code: str, start: date, end: date, confidence: str = 'all', fire_type: str = 'all'):
    from .services.huanuco import points
    valid_department(code)
    if start.year < 2016 or end.year > 2026 or start.year != end.year or end < start or (end-start).days > 366 or confidence not in ('all', 'high') or fire_type not in ('all', 'vegetation'):
        raise HTTPException(422, 'Intervalo o filtros no válidos')
    try:
        with connection() as conn:
            rows = points(conn, start, end, confidence, fire_type, code)
            return {'data': rows[:20000], 'truncated': len(rows) > 20000}
    except psycopg.Error as exc:
        raise HTTPException(503, 'No se pudieron consultar las observaciones') from exc


@app.get('/api/departments/{code}/cells')
def department_cells(code: str, start: date, grid: int = 5, confidence: str = 'all', fire_type: str = 'all'):
    from .services.huanuco import spatial_analysis
    valid_department(code)
    end = start + timedelta(days=6)
    if not 2016 <= start.year <= 2026 or start.weekday() != 0 or end.year != start.year or grid not in (2, 5, 10) or confidence not in ('all', 'high') or fire_type not in ('all', 'vegetation'):
        raise HTTPException(422, 'Se requiere una semana ISO completa dentro de un año y filtros válidos')
    try:
        with connection() as conn:
            return spatial_analysis(conn, start, grid, confidence, fire_type, code)
    except psycopg.Error as exc:
        raise HTTPException(503, 'No se pudo calcular la comparación por celda') from exc
