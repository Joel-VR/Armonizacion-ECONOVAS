"""Crea o copia las tablas FIRMS originales a Neon sin sobrescribir datos."""
import argparse
import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.database import database_config

TABLES = ('modis', 'viirs')
COLUMNS = ('latitude', 'longitude', 'acq_date', 'acq_time', 'instrument', 'track',
           'daynight', 'scan', 'version', 'confidence', 'satellite', 'brightness',
           'type', 'frp', 'bright_t31', 'departamento')
DDL = '''CREATE TABLE IF NOT EXISTS public.{} (
 latitude double precision, longitude double precision, acq_date text, acq_time text,
 instrument text, track double precision, daynight text, scan double precision,
 version text, confidence text, satellite text, brightness double precision,
 type text, frp double precision, bright_t31 double precision, departamento text
)'''


def connection_settings():
    """Usa PG* para Neon y EVENTS_DB_* o DB_* para la base local."""
    names = {'host': 'PGHOST', 'dbname': 'PGDATABASE', 'user': 'PGUSER', 'password': 'PGPASSWORD'}
    missing = [name for name in names.values() if not os.environ.get(name)]
    if missing:
        raise ValueError('Faltan variables de Neon: ' + ', '.join(missing))
    neon = {key: os.environ[name] for key, name in names.items()}
    neon['port'] = int(os.environ.get('PGPORT', '5432'))
    neon['connect_timeout'] = 5
    for name, parameter in (('PGSSLMODE', 'sslmode'), ('PGCHANNELBINDING', 'channel_binding')):
        if os.environ.get(name):
            neon[parameter] = os.environ[name]
    return neon


def local_settings():
    if os.environ.get('EVENTS_DB_HOST'):
        return database_config('EVENTS')
    names = {'host': 'DB_HOST', 'port': 'DB_PORT', 'dbname': 'DB_NAME',
             'user': 'DB_USER', 'password': 'DB_PASSWORD'}
    missing = [name for name in names.values() if not os.environ.get(name)]
    if missing:
        raise ValueError('Faltan variables de PostgreSQL local: ' + ', '.join(missing))
    result = {key: os.environ[name] for key, name in names.items()}
    result['port'] = int(result['port'])
    result['connect_timeout'] = 5
    # No heredar PGSSLMODE/PGCHANNELBINDING de la conexión de Neon.
    result['sslmode'] = os.environ.get('DB_SSLMODE', 'prefer')
    result['channel_binding'] = 'prefer'
    return result


def create_tables(conn):
    for table in TABLES:
        conn.execute(sql.SQL(DDL).format(sql.Identifier(table)))


def transfer(source, target):
    columns = sql.SQL(', ').join(map(sql.Identifier, COLUMNS))
    with source.transaction(), target.transaction():
        source.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        create_tables(target)
        for table in TABLES:
            name = sql.Identifier('public', table)
            if not source.execute(sql.SQL('SELECT EXISTS(SELECT 1 FROM {})').format(name)).fetchone()[0]:
                raise ValueError(f'La tabla local {table} está vacía; no se copió ningún dato')
            target.execute(sql.SQL('LOCK TABLE {} IN ACCESS EXCLUSIVE MODE').format(name))
            if target.execute(sql.SQL('SELECT EXISTS(SELECT 1 FROM {})').format(name)).fetchone()[0]:
                raise ValueError(f'La tabla destino {table} no está vacía; no se modificó ninguna tabla')
        for table in TABLES:
            name = sql.Identifier('public', table)
            count = 0
            with source.cursor(name='export_' + table) as reader, target.cursor() as writer:
                reader.execute(sql.SQL('SELECT {} FROM {}').format(columns, name))
                with writer.copy(sql.SQL('COPY {} ({}) FROM STDIN').format(name, columns)) as copy:
                    for row in reader:
                        copy.write_row(row)
                        count += 1
            actual = target.execute(sql.SQL('SELECT count(*) FROM {}').format(name)).fetchone()[0]
            if actual != count:
                raise ValueError(f'Conteo inesperado en {table}: {actual} != {count}')
            print(f'{table}: {count} filas verificadas', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--crear-tablas', action='store_true', help='Solo crear tablas vacías si no existen')
    args = parser.parse_args()
    neon = connection_settings()
    with psycopg.connect(**neon) as target:
        if args.crear_tablas:
            with target.transaction():
                create_tables(target)
            print('Tablas verificadas en el destino; no se copiaron datos.')
        else:
            local = local_settings()
            local.setdefault('sslmode', 'prefer')
            local.setdefault('channel_binding', 'prefer')
            if all(local[k] == neon[k] for k in ('host', 'port', 'dbname', 'user')):
                raise ValueError('La base local y la base destino no pueden ser la misma')
            with psycopg.connect(**local) as source:
                transfer(source, target)
            print('Carga confirmada en Neon; datos_armonizados no fue modificada.')


if __name__ == '__main__':
    main()
