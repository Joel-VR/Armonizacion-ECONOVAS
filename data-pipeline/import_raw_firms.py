"""Carga sin normalizar los JSON FIRMS originales en las tablas modis y viirs vacías."""
import argparse
import sys
from pathlib import Path

import ijson
import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.database import database_config

COLUMNS = ('latitude', 'longitude', 'acq_date', 'acq_time', 'instrument', 'track',
           'daynight', 'scan', 'version', 'confidence', 'satellite', 'brightness',
           'type', 'frp', 'bright_t31')
REQUIRED = set(COLUMNS) - {'type'}
SOURCE_FOLDERS = (
    ('MODIS C6.1', 'modis', {'Aqua', 'Terra'}),
    ('SUOMI VIIRS C2', 'viirs', {'SNPP'}),
    ('J1 VIIRS C2', 'viirs', {'N20'}),
    ('J2 VIIRS C2', 'viirs', {'N21'}),
)


def raw_row(record, satellites):
    missing = REQUIRED - record.keys()
    extra = record.keys() - set(COLUMNS)
    if missing or extra:
        raise ValueError(f'Columnas inesperadas: faltantes={sorted(missing)}, adicionales={sorted(extra)}')
    if record['satellite'] not in satellites:
        raise ValueError(f"Satélite inesperado: {record['satellite']}")
    return tuple(record.get(column) for column in COLUMNS)


def source_files(data_dir):
    paths = []
    for folder, table, satellites in SOURCE_FOLDERS:
        for prefix in ('fire_archive_', 'fire_nrt_'):
            matches = sorted((data_dir / folder).glob(prefix + '*.json'))
            if len(matches) != 1:
                raise ValueError(f'Se esperaba exactamente un archivo {prefix} en {folder}')
            paths.append((matches[0], table, satellites))
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'data' / 'modisViirs')
    args = parser.parse_args()
    paths = source_files(args.data_dir)
    counts = {'modis': 0, 'viirs': 0}
    # Toda la carga es una sola transacción: un error revierte los ocho archivos.
    with psycopg.connect(**database_config()) as conn:
        with conn.transaction():
            conn.execute('LOCK TABLE public.modis, public.viirs IN ACCESS EXCLUSIVE MODE')
            for table in counts:
                count = conn.execute(sql.SQL('SELECT count(*) FROM public.{}').format(sql.Identifier(table))).fetchone()[0]
                if count:
                    raise ValueError(f'La tabla {table} no está vacía; no se modifica ningún dato')
            for path, table, satellites in paths:
                print('Cargando', path.name, 'en', table, flush=True)
                count = 0
                statement = sql.SQL('COPY public.{} ({}) FROM STDIN').format(
                    sql.Identifier(table), sql.SQL(',').join(map(sql.Identifier, COLUMNS)))
                with path.open('rb') as source, conn.cursor() as cur:
                    with cur.copy(statement) as copy:
                        for record in ijson.items(source, 'item', use_float=True):
                            copy.write_row(raw_row(record, satellites))
                            count += 1
                counts[table] += count
                print('  leídos:', count, flush=True)
            for table, expected in counts.items():
                actual = conn.execute(sql.SQL('SELECT count(*) FROM public.{}').format(sql.Identifier(table))).fetchone()[0]
                if actual != expected:
                    raise ValueError(f'Conteo distinto en {table}: {actual} != {expected}')
            print('Verificado:', counts, flush=True)
    print('Carga confirmada.', flush=True)


if __name__ == '__main__':
    main()
