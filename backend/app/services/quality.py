"""Conservative screening, not a validated fire classifier.

MapBiomas is context at the observation centre, not the whole satellite footprint.
References: MapBiomas Peru Collection 4 legend and NASA FIRMS product attributes.
"""
RULE_VERSION = 'huanuco-context-v1'
CATEGORIES = {
    'forest': {'label': 'Bosque', 'color': '#298743', 'codes': [1, 3, 4, 5, 6]},
    'agriculture': {'label': 'Agropecuario', 'color': '#f2cf45', 'codes': [14, 21, 9, 35, 40, 15]},
    'water': {'label': 'Agua', 'color': '#348de5', 'codes': [26, 33, 31]},
    'urban': {'label': 'Urbano', 'color': '#d55b56', 'codes': [24]},
    'other': {'label': 'Otras coberturas', 'color': '#c4cbd2', 'codes': []},
}

def category(code):
    if not code or code == 27:
        return 'unknown'
    for name, item in CATEGORIES.items():
        if code in item['codes']:
            return name
    return 'other'

def evaluate(sensor, confidence, fire_type, cover, reference_year=2025):
    """Return an auditable decision. Unknown NRT type is never inferred as type 0."""
    if str(fire_type) in ('1', '2', '3'):
        return 'excluded', 'Tipo original NASA ajeno a vegetación (1, 2 o 3).'
    if sensor == 'VIIRS':
        valid_confidence = str(confidence).lower() in ('n', 'h')
    else:
        try:
            valid_confidence = 30 <= float(confidence) <= 100
        except (ValueError, TypeError):
            valid_confidence = False
    if not valid_confidence:
        return 'review', 'Confianza baja o no interpretable; umbral inicial por sensor.'
    if fire_type is None or str(fire_type) != '0':
        return 'review', 'Sin tipo original de vegetación; requiere evidencia adicional.'
    if cover not in ('forest', 'agriculture'):
        return 'review', 'Cobertura distinta de bosque/agropecuario o sin información.'
    return 'candidate', f'Tipo 0 y confianza aceptable sobre bosque/agropecuario de {reference_year}; no confirmado.'
