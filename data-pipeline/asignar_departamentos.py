"""Asigna departamentos por el centro del píxel, sin alterar campos originales."""
import sys
from pathlib import Path

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.database import database_config
from app.services.huanuco import departments

BATCH = 10000


def prepare_regions(conn):
    conn.execute('CREATE TEMP TABLE regiones (nombre text NOT NULL, geom geometry(Geometry,4326) NOT NULL)')
    for region in departments().values():
        conn.execute('INSERT INTO regiones VALUES (%s, ST_UnaryUnion(ST_SetSRID(ST_GeomFromGeoJSON(%s),4326)))',
                     (region['name'], region['geometry']))
    conn.execute('ANALYZE regiones')


def backfill_table(conn, table):
    ident = sql.Identifier(table)
    print(f'Preparando puntos de {table}...', flush=True)
    conn.execute(sql.SQL("""CREATE TEMP TABLE puntos AS
        SELECT ctid AS fila, ST_SetSRID(ST_MakePoint(longitude,latitude),4326) AS geom
        FROM public.{} WHERE departamento IS NULL AND longitude BETWEEN -180 AND 180 AND latitude BETWEEN -90 AND 90""").format(ident))
    conn.execute('CREATE INDEX puntos_geom_idx ON puntos USING gist(geom)')
    conn.execute('ANALYZE puntos')
    print(f'Cruzando puntos de {table} con límites departamentales...', flush=True)
    conn.execute("""CREATE TEMP TABLE coincidencias AS
        SELECT p.fila, min(r.nombre) AS nombre, count(*) AS cantidad
        FROM regiones r JOIN puntos p ON p.geom && r.geom AND ST_Covers(r.geom,p.geom)
        GROUP BY p.fila""")
    found = conn.execute('SELECT count(*) FROM coincidencias WHERE cantidad=1').fetchone()[0]
    ambiguous = conn.execute('SELECT count(*) FROM coincidencias WHERE cantidad>1').fetchone()[0]
    total = conn.execute('SELECT count(*) FROM puntos').fetchone()[0]
    print(f'{table}: {total} sin asignar; {found} con un departamento; {ambiguous} ambiguos; {total-found-ambiguous} fuera de límites.', flush=True)
    conn.commit()
    updated = 0
    while True:
        with conn.transaction():
            conn.execute('SET LOCAL enable_hashjoin = off')
            conn.execute('SET LOCAL enable_mergejoin = off')
            result = conn.execute(sql.SQL("""WITH lote AS (
                DELETE FROM coincidencias WHERE ctid IN
                  (SELECT ctid FROM coincidencias WHERE cantidad=1 LIMIT %s)
                RETURNING fila, nombre
                ) UPDATE public.{} AS destino SET departamento=lote.nombre
                  FROM lote WHERE destino.ctid=lote.fila AND destino.departamento IS NULL""").format(ident), (BATCH,))
            count = result.rowcount
        if not count:
            break
        updated += count
        if updated % 100000 == 0 or updated == found:
            print(f'{table}: {updated}/{found} asignados', flush=True)
    if updated != found:
        raise RuntimeError(f'Se asignaron {updated} de {found}; revisar escrituras simultáneas')
    conn.execute('DROP TABLE coincidencias, puntos')
    conn.commit()


def main():
    with psycopg.connect(**database_config()) as conn:
        prepare_regions(conn)
        conn.commit()
        for table in ('modis','viirs'):
            backfill_table(conn, table)
        for table in ('modis','viirs'):
            rows = conn.execute(sql.SQL('SELECT departamento, count(*) FROM public.{} GROUP BY departamento ORDER BY departamento NULLS LAST').format(sql.Identifier(table))).fetchall()
            print(table, rows, flush=True)


if __name__ == '__main__':
    main()
