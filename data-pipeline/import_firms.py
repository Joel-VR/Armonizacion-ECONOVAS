"""Importa archivos JSON FIRMS de MODIS y Suomi sin cargar el archivo en memoria."""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import ijson
import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.database import database_config
COLUMNS = ('fingerprint', 'latitude', 'longitude', 'acquired_at', 'sensor', 'satellite',
           'confidence', 'frp', 'brightness', 'bright_t31', 'scan', 'track', 'daynight',
           'fire_type', 'version', 'source_kind', 'source_file')


def convert(record, path, sensor):
    lat, lon = float(record['latitude']), float(record['longitude'])
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError('Coordenadas inválidas')
    when = datetime.strptime(record['acq_date'] + str(record['acq_time']).zfill(4), '%Y-%m-%d%H%M').replace(tzinfo=timezone.utc)
    satellite = str(record['satellite'])
    if satellite not in ({'Terra', 'Aqua'} if sensor == 'MODIS' else {'SNPP'}):
        raise ValueError('Satélite inesperado: ' + satellite)
    kind = 'nrt' if path.name.startswith('fire_nrt_') else 'archive'
    fingerprint = hashlib.sha256((sensor + kind + json.dumps(record, sort_keys=True, default=str)).encode()).hexdigest()
    return (fingerprint, lat, lon, when, sensor, satellite, str(record.get('confidence', '')),
            record.get('frp'), record.get('brightness'), record.get('bright_t31'), record.get('scan'),
            record.get('track'), record.get('daynight'), record.get('type'), str(record['version']), kind, path.name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'data' / 'modisViirs')
    args = parser.parse_args()
    parser.error('La importación anterior está deshabilitada: el proyecto usa tablas originales modis y viirs sin normalizar.')
    try:
        config = database_config()
    except ValueError as exc:
        parser.error(str(exc))
    files = [(p, sensor) for folder, sensor in [('MODIS C6.1', 'MODIS'), ('SUOMI VIIRS C2', 'VIIRS')]
             for p in sorted((args.data_dir / folder).glob('fire_*.json'))]
    if len(files) != 4:
        parser.error('Se esperan los cuatro JSON de MODIS y Suomi')
    with psycopg.connect(**config) as conn:
        conn.execute((ROOT / 'backend' / 'sql' / 'schema.sql').read_text(encoding='utf-8'))
        conn.commit()
        for path, sensor in files:
            print('Importando', path.name, flush=True)
            # Una transacción por archivo: un error no deja una carga parcial.
            with conn.transaction():
                conn.execute('CREATE TEMP TABLE staging (LIKE fire_detections INCLUDING DEFAULTS) ON COMMIT DROP')
                count = 0
                with path.open('rb') as source, conn.cursor() as cur:
                    with cur.copy('COPY staging (' + ','.join(COLUMNS) + ') FROM STDIN') as copy:
                        for record in ijson.items(source, 'item', use_float=True):
                            copy.write_row(convert(record, path, sensor))
                            count += 1
                before = conn.execute('SELECT count(*) FROM fire_detections').fetchone()[0]
                conn.execute('INSERT INTO fire_detections (' + ','.join(COLUMNS) + ') SELECT ' + ','.join(COLUMNS) + ' FROM staging ON CONFLICT (fingerprint) DO NOTHING')
                after = conn.execute('SELECT count(*) FROM fire_detections').fetchone()[0]
                print(f'  leídos={count}, nuevos={after-before}, duplicados={count-(after-before)}', flush=True)


if __name__ == '__main__':
    main()
