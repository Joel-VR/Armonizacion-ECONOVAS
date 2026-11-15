"""Conservative, explicit application policy; not a validated NASA classifier."""
from math import asin, cos, radians, sin, sqrt

VERSION = 'huanuco-events-v5-alerts'
PARAMETERS = {'distance_m': 750, 'hours': 24, 'max_event_hours': 48,
              'independent_pass_minutes': 15, 'minimum_target_fraction': 0.55,
              'max_water_urban_fraction': 0.1, 'modis_high': 80,
              'neighborhood': '5x5 samples spanning nominal pixel; conservative context, not footprint',
              'forest_codes': [3, 4, 5, 6], 'crop_codes': [35, 40],
              'mixed_codes': [21], 'pasture_codes': [15], 'plantation_codes': [9]}


def cover(code):
    if code in PARAMETERS['forest_codes']: return 'forest'
    if code in PARAMETERS['crop_codes']: return 'agriculture'
    if code == 21: return 'mixed'
    if code == 15: return 'pasture'
    if code == 9: return 'plantation'
    if code in (26, 31, 33): return 'water'
    if code == 24: return 'urban'
    if code in (0, 27): return 'unknown'
    return 'other'


def distance(a, b):
    lat1, lat2 = radians(a['latitude']), radians(b['latitude'])
    dl = radians(b['longitude'] - a['longitude'])
    x = sin((lat2-lat1)/2)**2 + cos(lat1)*cos(lat2)*sin(dl/2)**2
    return 6371000 * 2 * asin(sqrt(min(1, x)))


def high(row):
    if row['sensor'] == 'VIIRS': return str(row['confidence']).lower() == 'h'
    try: return 80 <= float(row['confidence']) <= 100
    except (TypeError, ValueError): return False


def assess(row, codes):
    category = cover(codes[len(codes)//2])
    evidence = {'samples': codes, 'category': category, 'high_confidence': high(row)}
    if str(row['fire_type']) in ('1', '2', '3'):
        return 'excluida', 'Tipo NASA no correspondiente a fuego de vegetación.', evidence
    if category in ('water', 'urban'):
        return 'excluida', 'Centro de la detección en agua o área urbana de referencia.', evidence
    missing_nrt_type = row['fire_type'] is None and row['sensor'] == 'VIIRS' and str(row['confidence']).lower() in ('n', 'h')
    if str(row['fire_type']) != '0' and not missing_nrt_type:
        return 'revision', 'Tipo de vegetación NASA no informado o no válido; se conserva para revisión.', evidence
    if missing_nrt_type:
        evidence['nrt_type_missing'] = True
    if category not in ('forest', 'agriculture', 'mixed'):
        return 'revision', 'Cobertura no forestal ni agrícola clara; se conserva para revisión.', evidence
    try:
        confidence_ok = str(row['confidence']).lower() in ('n','h') if row['sensor']=='VIIRS' else 30 <= float(row['confidence']) <= 100
    except (TypeError, ValueError): confidence_ok = False
    if not confidence_ok or row['frp'] is None or row['frp'] <= 0:
        return 'revision', 'Confianza insuficiente o potencia radiativa ausente/no positiva.', evidence
    valid_codes = [c for c in codes if c not in (0, 27)]
    target_codes = ('forest','agriculture','mixed') if category == 'mixed' else (category,)
    denominator = max(1, len(valid_codes))
    fraction = sum(cover(c) in target_codes for c in valid_codes)/denominator
    blocked = sum(cover(c) in ('water','urban') for c in valid_codes)/denominator
    threshold = 0.4 if category == 'mixed' else 0.55
    evidence.update(target_fraction=fraction, blocked_fraction=blocked, valid_neighbor_pixels=len(valid_codes))
    if fraction < threshold or blocked > 0.3:
        return 'revision', 'Cobertura vecina mixta o con presencia importante de agua/urbano; se conserva para revisar.', evidence
    return 'apta', 'Contexto y calidad aptos; falta comprobar evidencia temporal.', evidence


def event_type(category):
    return {'forest': 'incendio_forestal', 'agriculture': 'quema_agricola'}.get(category, 'fuego_sin_clasificar')


def corroborated(a, b):
    seconds = abs((a['acquired_at']-b['acquired_at']).total_seconds())
    independent = a['satellite'] != b['satellite'] or seconds >= PARAMETERS['independent_pass_minutes']*60
    return independent and seconds <= PARAMETERS['hours']*3600 and distance(a,b) <= PARAMETERS['distance_m']


def group_events(rows):
    """Deterministic bounded groups, preventing month-long transitive chains.

    A member must be within 500m of the anchor, no more than 36h from its start,
    and no more than 12h from the previous observation of the group.
    """
    groups = []
    for row in sorted(rows, key=lambda r:(r['acquired_at'],r['id'])):
        for group in reversed(groups):
            if row['cover_category'] != group[0]['cover_category']: continue
            span = (row['acquired_at']-group[0]['acquired_at']).total_seconds()
            gap = (row['acquired_at']-group[-1]['acquired_at']).total_seconds()
            if span <= PARAMETERS['max_event_hours']*3600 and gap <= PARAMETERS['hours']*3600 and distance(row,group[0]) <= PARAMETERS['distance_m']:
                group.append(row)
                break
        else: groups.append([row])
    return groups
