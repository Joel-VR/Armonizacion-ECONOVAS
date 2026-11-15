from datetime import date, datetime, time, timedelta, timezone
import os

import psycopg
from fastapi import FastAPI, HTTPException, Query
from psycopg.rows import dict_row

from .database import database_config

app = FastAPI(title="T'UKRI API", version='0.2.0')


@app.get('/api/huanuco/events/analysis')
def event_analysis():
    from .services.events import summary
    try:
        with connection(events=True) as conn:
            return summary(conn)
    except (ValueError, psycopg.Error):
        return {'year': 2026, 'daily': [], 'event_daily': [], 'weekly': [], 'grid_km': None, 'message': 'Eventos no inicializados.'}


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
    except (ValueError, psycopg.Error):
        return {'data': [], 'total': 0, 'truncated': False, 'unit': 'probable_events'}


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
    if not 2000 <= start.year <= 2026 or end.year != start.year or end < start or sensor not in ('all', 'MODIS', 'VIIRS') or confidence not in ('all', 'high') or fire_type not in ('all', '0', '1', '2', '3', 'unknown', 'vegetation'):
        raise HTTPException(422, 'Seleccione un intervalo dentro de un año entre 2000 y 2026 y filtros válidos.')
    from .services.huanuco import points
    try:
        with connection() as conn:
            rows = points(conn, start, end, confidence, fire_type, 'PE-HUC', sensor)
        return {'data': rows[:20000], 'total': len(rows), 'truncated': len(rows) > 20000}
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
    if year < 2000 or year > 2026 or grid not in (2, 5, 10) or confidence not in ('all', 'high') or fire_type not in ('all', 'vegetation'):
        raise HTTPException(422, 'Filtros no válidos')
    try:
        with connection() as conn:
            return analysis(conn, grid, confidence, fire_type, year)
    except psycopg.Error as exc:
        raise HTTPException(503, 'No se pudo calcular el análisis') from exc


@app.get('/api/huanuco/points')
def huanuco_points(start: date, end: date, confidence: str = 'all', fire_type: str = 'all'):
    from .services.huanuco import points
    if start.year < 2000 or end.year > 2026 or start.year != end.year or end < start or (end-start).days > 366 or confidence not in ('all', 'high') or fire_type not in ('all', 'vegetation'):
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
    if not 2000 <= start.year <= 2026 or start.weekday() != 0 or end.year != start.year or grid not in (2, 5, 10) or confidence not in ('all', 'high') or fire_type not in ('all', 'vegetation'):
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
    if year < 2000 or year > 2026 or grid not in (2, 5, 10) or confidence not in ('all', 'high') or fire_type not in ('all', 'vegetation'):
        raise HTTPException(422, 'Filtros no válidos')
    try:
        with connection() as conn:
            # 1. Intentar leer directamente de datos_armonizados en PostgreSQL
            try:
                res = stored_analysis(conn, year, code)
                if res and res.get('weekly'):
                    return res
            except Exception:
                pass
            if os.environ.get('DB_DATA_SOURCE') == 'armonizados':
                return stored_analysis(conn, year, code)
            return analysis(conn, grid, confidence, fire_type, year, code)
    except psycopg.Error as exc:
        raise HTTPException(503, 'No se pudo calcular el análisis') from exc


@app.get('/api/departments/{code}/points')
def department_points(code: str, start: date, end: date, sensor: str = 'all', confidence: str = 'all', fire_type: str = 'all'):
    from .services.huanuco import points
    valid_department(code)
    if start.year < 2000 or end.year > 2026 or start.year != end.year or end < start or (end-start).days > 366 or sensor not in ('all', 'MODIS', 'VIIRS') or confidence not in ('all', 'high') or fire_type not in ('all', 'vegetation', '0', '1', '2', '3', 'unknown'):
        raise HTTPException(422, 'Intervalo o filtros no válidos')
    try:
        with connection() as conn:
            rows = points(conn, start, end, confidence, fire_type, code, sensor)
            return {'data': rows[:20000], 'total': len(rows), 'truncated': len(rows) > 20000}
    except psycopg.Error as exc:
        raise HTTPException(503, 'No se pudieron consultar las observaciones') from exc


@app.get('/api/departments/{code}/cells')
def department_cells(code: str, start: date, grid: int = 5, confidence: str = 'all', fire_type: str = 'all'):
    from .services.huanuco import spatial_analysis
    valid_department(code)
    end = start + timedelta(days=6)
    if not 2000 <= start.year <= 2026 or start.weekday() != 0 or end.year != start.year or grid not in (2, 5, 10) or confidence not in ('all', 'high') or fire_type not in ('all', 'vegetation'):
        raise HTTPException(422, 'Se requiere una semana ISO completa dentro de un año y filtros válidos')
    try:
        with connection() as conn:
            return spatial_analysis(conn, start, grid, confidence, fire_type, code)
    except psycopg.Error as exc:
        raise HTTPException(503, 'No se pudo calcular la comparación por celda') from exc


@app.get('/api/burn-calendar')
def burn_calendar_endpoint(department: str = 'PE-HUC'):
    return get_department_calendar(department)


@app.get('/api/departments/{code}/calendar')
def get_department_calendar(code: str):
    from .services.huanuco import burn_calendar
    valid_department(code)
    try:
        with connection() as conn:
            return burn_calendar(conn, code)
    except Exception:
        from .services.huanuco import burn_calendar
        return burn_calendar(None, code)


@app.get('/api/departments/{code}/calendar/export.csv')
def export_department_calendar_csv(code: str):
    import io, csv
    from fastapi.responses import Response
    from .services.huanuco import burn_calendar
    valid_department(code)
    try:
        with connection() as conn:
            data = burn_calendar(conn, code)
    except Exception:
        from .services.huanuco import burn_calendar
        data = burn_calendar(None, code)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'departamento_codigo', 'departamento_nombre', 'anio', 'mes', 'nombre_mes',
        'indice_armonizado', 'mediana_historica_2016_2024', 'desviacion_anomalia',
        'porcentaje_anomalia', 'estado_anomalia', 'temporada_critica',
        'horario_inusual', 'celdas_modis', 'celdas_viirs', 'total_celdas'
    ])
    dep_name = data['department']['name']
    for year_str, cells in data['matrix'].items():
        for c in cells:
            writer.writerow([
                code, dep_name, c['year'], c['month'], c['month_name'],
                c['harmonized_index'] if c['harmonized_index'] is not None else '',
                c['historical_median'] if c['historical_median'] is not None else '',
                c['anomaly_delta'] if c['anomaly_delta'] is not None else '',
                f"{c['anomaly_pct']:+.1f}%" if c['anomaly_pct'] is not None else '',
                c['anomaly_status'],
                'SI' if c['is_peak_season'] else 'NO',
                'SI' if c['is_unusual_timing'] else 'NO',
                c['modis_cells'], c['viirs_cells'], c['total_cells']
            ])

    filename = f"calendario_quemas_{code}_{dep_name.lower().replace(' ', '_')}.csv"
    return Response(
        content=output.getvalue().encode('utf-8-sig'),
        media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


@app.get('/api/departments/{code}/export/observations.csv')
def export_observations_csv(code: str, start: date, end: date, sensor: str = 'all', confidence: str = 'all', fire_type: str = 'all'):
    import io, csv
    from fastapi.responses import Response
    from .services.huanuco import points
    valid_department(code)
    try:
        with connection() as conn:
            rows = points(conn, start, end, confidence, fire_type, code)
    except Exception:
        rows = []

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['id', 'fecha_utc', 'latitud', 'longitud', 'sensor', 'satelite', 'confianza', 'frp_mw', 'brillo_k', 'tipo_fuego', 'departamento'])
    for r in rows:
        writer.writerow([
            r.get('id', ''), r.get('acquired_at', ''), r.get('latitude', ''), r.get('longitude', ''),
            r.get('sensor', ''), r.get('satellite', ''), r.get('confidence', ''), r.get('frp', ''),
            r.get('brightness', ''), r.get('fire_type', ''), code
        ])
    filename = f"detecciones_firms_{code}_{start}_{end}.csv"
    return Response(
        content=output.getvalue().encode('utf-8-sig'),
        media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )
