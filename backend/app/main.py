from datetime import date, datetime, time, timedelta, timezone

import psycopg
from fastapi import FastAPI, HTTPException, Query
from psycopg.rows import dict_row

from .database import database_config

app = FastAPI(title='Brinco Alerta API', version='0.2.0')


def connection():
    try:
        return psycopg.connect(**database_config(), row_factory=dict_row, options='-c timezone=UTC')
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    except psycopg.Error:
        raise HTTPException(503, 'No se pudo conectar a PostgreSQL')


@app.get('/api/health')
def health():
    return {'status': 'ok'}


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
