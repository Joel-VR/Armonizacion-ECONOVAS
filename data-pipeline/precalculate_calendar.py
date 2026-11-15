"""Precalcula los agregados mensuales de MODIS y VIIRS por departamento (2000-2026)."""
import json
import math
from collections import defaultdict
from pathlib import Path
import ijson

ROOT = Path(__file__).resolve().parents[1]
GEO_PATH = ROOT / 'frontend/public/geo/peru-departments.geojson'
MODIS_ARCHIVE = ROOT / 'data/modisViirs/MODIS C6.1/fire_archive_M-C61_850336.json'
MODIS_NRT = ROOT / 'data/modisViirs/MODIS C6.1/fire_nrt_M-C61_850336.json'
VIIRS_ARCHIVE = ROOT / 'data/modisViirs/SUOMI VIIRS C2/fire_archive_SV-C2_850337.json'
VIIRS_NRT = ROOT / 'data/modisViirs/SUOMI VIIRS C2/fire_nrt_SV-C2_850337.json'
OUTPUT = ROOT / 'data/processed/burn_calendar_summary.json'


def point_in_poly(x, y, poly):
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(1, n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def load_departments():
    with open(GEO_PATH, encoding='utf-8') as f:
        geo = json.load(f)
    deps = {}
    for feat in geo['features']:
        props = feat['properties']
        code = 'PE-LIM' if props['shapeISO'] == 'PE-LMA*' else props['shapeISO']
        name = 'Lima' if code == 'PE-LIM' else props['shapeName']
        geom = feat['geometry']
        rings = []
        if geom['type'] == 'Polygon':
            for r in geom['coordinates']: rings.append([(float(p[0]), float(p[1])) for p in r])
        elif geom['type'] == 'MultiPolygon':
            for poly in geom['coordinates']:
                for r in poly: rings.append([(float(p[0]), float(p[1])) for p in r])
        all_pts = [p for r in rings for p in r]
        lons = [p[0] for p in all_pts]
        lats = [p[1] for p in all_pts]
        deps[code] = {
            'name': name,
            'bbox': (min(lons), min(lats), max(lons), max(lats)),
            'rings': rings
        }
    return deps


def find_department(lon, lat, deps):
    candidates = [
        (code, d) for code, d in deps.items()
        if d['bbox'][0] <= lon <= d['bbox'][2] and d['bbox'][1] <= lat <= d['bbox'][3]
    ]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0][0]
    for code, d in candidates:
        for ring in d['rings']:
            if point_in_poly(lon, lat, ring):
                return code
    return candidates[0][0]


def process_stream(path, sensor, data, deps):
    if not path.exists():
        print(f"Omitiendo {path}, no existe.")
        return
    print(f"Procesando {sensor} desde {path.name}...")
    count = 0
    with open(path, 'rb') as f:
        for item in ijson.items(f, 'item'):
            lat, lon = float(item['latitude']), float(item['longitude'])
            dep_code = find_department(lon, lat, deps)
            if not dep_code:
                continue
            acq_date = item['acq_date']
            yr = int(acq_date[:4])
            m = int(acq_date[5:7])
            # 5km spatial grid bucket (approx 0.045 degrees)
            gx = int(lon / 0.045)
            gy = int(lat / 0.045)
            key = (yr, m)
            dep_data = data[dep_code]
            dep_data[key][f'{sensor.lower()}_count'] += 1
            dep_data[key][f'{sensor.lower()}_cells'].add((gx, gy, acq_date))
            count += 1
            if count % 200000 == 0:
                print(f"  {count} observaciones clasificadas...")
    print(f"  Total {sensor}: {count} observaciones.")


def stats_summary(vals):
    if not vals:
        return {'median': 0.1, 'p25': 0.05, 'p75': 0.25, 'min': 0.0, 'max': 1.0}
    s = sorted(vals)
    n = len(s)
    def pct(p):
        idx = (n - 1) * p
        lo = int(idx)
        hi = min(lo + 1, n - 1)
        return s[lo] + (s[hi] - s[lo]) * (idx - lo)
    return {
        'median': round(pct(0.5), 3),
        'p25': round(pct(0.25), 3),
        'p75': round(pct(0.75), 3),
        'min': round(s[0], 3),
        'max': round(s[-1], 3)
    }


def main():
    deps = load_departments()
    print(f"Cargados {len(deps)} departamentos.")
    data = defaultdict(lambda: defaultdict(lambda: {
        'modis_count': 0, 'viirs_count': 0,
        'modis_cells': set(), 'viirs_cells': set()
    }))

    for p in (MODIS_ARCHIVE, MODIS_NRT):
        process_stream(p, 'MODIS', data, deps)
    for p in (VIIRS_ARCHIVE, VIIRS_NRT):
        process_stream(p, 'VIIRS', data, deps)

    # Compile structured summary
    MONTH_NAMES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    MONTH_SHORT = ['', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Set', 'Oct', 'Nov', 'Dic']
    result = {}

    for code, d in deps.items():
        dep_name = d['name']
        dep_records = data[code]
        matrix = {}
        # Max observed counts across entire historical series for normalisation
        all_modis_cells = [len(dep_records[(y, m)]['modis_cells']) for y in range(2000, 2027) for m in range(1, 13)]
        all_viirs_cells = [len(dep_records[(y, m)]['viirs_cells']) for y in range(2012, 2027) for m in range(1, 13)]
        max_m_cells = max(all_modis_cells) if all_modis_cells and max(all_modis_cells) > 0 else 1
        max_v_cells = max(all_viirs_cells) if all_viirs_cells and max(all_viirs_cells) > 0 else 1

        for y in range(2000, 2027):
            matrix[str(y)] = []
            for m in range(1, 13):
                rec = dep_records[(y, m)]
                m_count = rec['modis_count']
                v_count = rec['viirs_count']
                m_cells = len(rec['modis_cells'])
                v_cells = len(rec['viirs_cells'])

                # Harmonized fire index
                if y < 2012:
                    p_modis = m_cells / max_m_cells if max_m_cells > 0 else 0
                    harmonized = round(min(1.0, math.sqrt(p_modis) * 0.95), 3) if m_cells > 0 else 0.0
                else:
                    p_modis = m_cells / max_m_cells if max_m_cells > 0 else 0
                    p_viirs = v_cells / max_v_cells if max_v_cells > 0 else 0
                    harmonized = round(min(1.0, (math.sqrt(p_modis) + math.sqrt(p_viirs)) / 2), 3) if (m_cells > 0 or v_cells > 0) else 0.0

                cell_obj = {
                    'year': y,
                    'month': m,
                    'month_name': MONTH_NAMES[m],
                    'month_short': MONTH_SHORT[m],
                    'harmonized_index': harmonized,
                    'modis_count': m_count,
                    'viirs_count': v_count,
                    'modis_cells': m_cells,
                    'viirs_cells': v_cells,
                    'total_cells': m_cells + v_cells,
                    'is_peak_season': m in (7, 8, 9, 10),
                    'is_baseline_year': 2001 <= y <= 2024,
                    'sensor_era': 'MODIS' if y < 2012 else 'MODIS+VIIRS' if y <= 2024 else 'VIIRS'
                }
                matrix[str(y)].append(cell_obj)

        # Baseline per month (2001-2024)
        baselines = {}
        for m in range(1, 13):
            month_vals = [matrix[str(y)][m - 1]['harmonized_index'] for y in range(2001, 2025)]
            baselines[m] = stats_summary(month_vals)

        # Fill anomalies
        highest_cell = None
        max_val = -1
        critical_count = 0

        for y in range(2000, 2027):
            for m in range(1, 13):
                c = matrix[str(y)][m - 1]
                b = baselines[m]
                c['historical_median'] = b['median']
                c['baseline_p25'] = b['p25']
                c['baseline_p75'] = b['p75']
                val = c['harmonized_index']
                med = max(b['median'], 0.03)
                delta = val - b['median']
                pct = ((val - b['median']) / med) * 100
                c['anomaly_delta'] = round(delta, 3)
                c['anomaly_pct'] = round(pct, 1)

                if val >= 0.80 or pct >= 65:
                    c['anomaly_status'] = 'critical'
                    critical_count += 1
                elif val >= 0.50 or pct >= 25:
                    c['anomaly_status'] = 'elevated'
                elif pct <= -30:
                    c['anomaly_status'] = 'unusually_low'
                else:
                    c['anomaly_status'] = 'normal'

                if m not in (7, 8, 9, 10) and (val >= 0.35 or c['anomaly_status'] in ('elevated', 'critical')):
                    c['is_unusual_timing'] = True
                else:
                    c['is_unusual_timing'] = False

                if val > max_val:
                    max_val = val
                    highest_cell = {'year': y, 'month': m, 'month_name': MONTH_NAMES[m], 'value': val, 'anomaly_pct': round(pct, 1)}

        result[code] = {
            'department': {'code': code, 'name': dep_name},
            'years': list(range(2000, 2027)),
            'months': [{'month': m, 'name': MONTH_NAMES[m], 'short': MONTH_SHORT[m], 'baseline': baselines[m]} for m in range(1, 13)],
            'matrix': matrix,
            'peak_season': [7, 8, 9, 10],
            'highest_month': highest_cell,
            'critical_count': critical_count,
            'alerts': [
                f"Históricamente, la temporada crítica en {dep_name} se concentra entre Julio y Octubre.",
                f"El récord histórico registrado ocurrió en {highest_cell['month_name']} {highest_cell['year']} con un índice de {int((highest_cell['value'] or 0)*100)}% ({highest_cell['anomaly_pct']:+0.1f}% vs mediana).",
                f"Se identificaron {critical_count} meses con anomalías críticas en el registro multianual continuo (2000–2026)."
            ],
            'methodology': {
                'reference_period': '2001-2024 (24 años)',
                'full_record': '2000-2026 (27 años)',
                'grid_km': 5,
                'sensors': 'MODIS C6.1 (Terra 2000+, Aqua 2002+) + VIIRS C2 (Suomi-NPP 2012+, NOAA-20, NOAA-21)'
            }
        }
        print(f"Departamento {dep_name} ({code}) precalculado: max {highest_cell['year']} {highest_cell['month_name']}.")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False)
    print(f"Archivo de resumen generado exitosamente en {OUTPUT} ({OUTPUT.stat().st_size / 1024:.1f} KB).")


if __name__ == '__main__':
    main()
