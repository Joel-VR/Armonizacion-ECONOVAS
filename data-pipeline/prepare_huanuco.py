"""Crop official land cover to Huanuco and cache five lightweight thematic layers.

Usage: python data-pipeline/prepare_huanuco.py --source URL_OR_LOCAL_TIF --year 2025 --collection 4
No national raster is ever sent to the browser. Original observations are untouched.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import psycopg
from psycopg.types.json import Jsonb
import rasterio
from rasterio.mask import mask
from rasterio.warp import transform_bounds, calculate_default_transform, reproject, transform
from rasterio.enums import Resampling
from shapely.geometry import shape, mapping
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.database import database_config
from app.services.huanuco import geometry
from app.services.quality import CATEGORIES, RULE_VERSION, category, evaluate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--year', type=int, required=True)
    parser.add_argument('--collection', type=int, default=4)
    args = parser.parse_args()
    provenance = args.source if args.source.startswith('https://') else 'https://plataforma.mapbiomas.org/projects/mapbiomas/peru'
    region = shape(json.loads(geometry()))
    output = ROOT / 'data' / 'processed' / f'huanuco-mapbiomas-{args.year}.tif'
    public = ROOT / 'frontend' / 'public' / 'geo' / 'huanuco'
    public.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.exists():
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', GDAL_HTTP_TIMEOUT='60'):
            with rasterio.open(args.source) as source:
                if not source.crs or source.count != 1:
                    raise ValueError('Se requiere un raster categórico de una banda y CRS conocido.')
                # Transform geometry if a source uses a projected CRS.
                from rasterio.warp import transform_geom
                geom = transform_geom('EPSG:4326', source.crs, mapping(region))
                data, affine = mask(source, [geom], crop=True, nodata=0, indexes=1)
                profile = dict(driver='GTiff', width=data.shape[1], height=data.shape[0],
                               count=1, dtype='uint8', crs=source.crs, transform=affine,
                               nodata=0, compress='deflate', tiled=True)
                with rasterio.open(output, 'w', **profile) as dest:
                    dest.write(data.astype('uint8'), 1)
        print('Recorte de Huánuco guardado.', flush=True)
    with rasterio.open(output) as source:
        affine, width, height = calculate_default_transform(source.crs, 'EPSG:3857', source.width,
                                                           source.height, *source.bounds, resolution=150)
        display = np.zeros((height, width), dtype='uint8')
        reproject(source=rasterio.band(source, 1), destination=display,
                  src_transform=source.transform, src_crs=source.crs,
                  dst_transform=affine, dst_crs='EPSG:3857', resampling=Resampling.nearest)
        left, bottom, right, top = rasterio.transform.array_bounds(height, width, affine)
        w, s, e, n = transform_bounds('EPSG:3857', 'EPSG:4326', left, bottom, right, top)
        groups = np.zeros(display.shape, dtype='uint8')
        for code in np.unique(display):
            if category(int(code)) in CATEGORIES:
                groups[display == code] = list(CATEGORIES).index(category(int(code))) + 1
        layers = []
        for index, (name, definition) in enumerate(CATEGORIES.items(), 1):
            rgba = np.zeros((*display.shape, 4), dtype='uint8')
            color = definition['color'].lstrip('#')
            rgba[groups == index] = [int(color[i:i+2], 16) for i in (0, 2, 4)] + [255]
            filename = f'{name}.png'
            Image.fromarray(rgba).save(public / filename, optimize=True)
            layers.append({'id': name, **definition, 'url': f'/geo/huanuco/{filename}'})
        checksum = hashlib.sha256(output.read_bytes()).hexdigest()
        metadata = {'ready': True, 'provider': 'MapBiomas Perú', 'year': args.year,
                    'collection': args.collection, 'department': 'PE-HUC', 'license': 'CC BY 4.0',
                    'source_url': provenance, 'rule_version': RULE_VERSION, 'checksum_sha256': checksum,
                    'coordinates': [[w, n], [e, n], [e, s], [w, s]], 'layers': layers,
                    'display_resolution_m': 150, 'classification': 'native pixel at observation centre',
                    'warning': f'Cobertura de referencia {args.year}; no describe cambios de 2026.'}
        layer_id = f'mapbiomas-peru-col{args.collection}-{args.year}-huanuco'
        with psycopg.connect(**database_config()) as conn:
            conn.execute((ROOT / 'backend' / 'sql' / 'context.sql').read_text())
            conn.execute('INSERT INTO reference_layers(id,provider,collection,reference_year,source_url,license,native_crs,checksum_sha256,metadata) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO UPDATE SET checksum_sha256=excluded.checksum_sha256, metadata=excluded.metadata',
                         (layer_id, 'MapBiomas Perú', str(args.collection), args.year, provenance,
                          'CC BY 4.0', str(source.crs), checksum, Jsonb(metadata)))
            rows = conn.execute('WITH a AS (SELECT ST_UnaryUnion(ST_SetSRID(ST_GeomFromGeoJSON(%s),4326)) g) SELECT id,longitude,latitude,sensor,confidence,fire_type FROM fire_detections,a WHERE geom && g AND ST_Covers(g,geom) ORDER BY id', (geometry(),)).fetchall()
            xs, ys = transform('EPSG:4326', source.crs, [r[1] for r in rows], [r[2] for r in rows])
            rr, cc = rasterio.transform.rowcol(source.transform, xs, ys)
            native = source.read(1)
            values = [int(native[r, c]) if 0 <= r < source.height and 0 <= c < source.width else 0 for r, c in zip(rr, cc)]
            conn.execute('CREATE TEMP TABLE evaluated (LIKE observation_evaluations INCLUDING DEFAULTS) ON COMMIT DROP')
            with conn.cursor().copy('COPY evaluated(observation_id,layer_id,rule_version,cover_code,cover_category,decision,reason) FROM STDIN') as copy:
                for row, code in zip(rows, values):
                    cover = category(code)
                    decision, reason = evaluate(row[3], row[4], row[5], cover, args.year)
                    copy.write_row((row[0], layer_id, RULE_VERSION, code, cover, decision, reason))
            conn.execute('INSERT INTO observation_evaluations SELECT * FROM evaluated ON CONFLICT(observation_id,layer_id,rule_version) DO UPDATE SET cover_code=excluded.cover_code,cover_category=excluded.cover_category,decision=excluded.decision,reason=excluded.reason,evaluated_at=excluded.evaluated_at')
            print('Evaluaciones:', conn.execute('SELECT decision,count(*) FROM observation_evaluations WHERE layer_id=%s GROUP BY decision', (layer_id,)).fetchall(), flush=True)
        metadata['layer_id'] = layer_id
        (public / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Capas locales y evaluaciones preparadas.', flush=True)


if __name__ == '__main__':
    main()
