"""Fast, auditable Huanuco 2026 views. No inferred confirmed fires or causal labels."""
import json
from pathlib import Path
from .quality import RULE_VERSION, CATEGORIES

META = Path(__file__).resolve().parents[3] / 'frontend/public/geo/huanuco/metadata.json'

def metadata():
    if not META.exists():
        return {'ready': False, 'layers': [], 'message': 'Cobertura pendiente de preparación; no se inventan categorías.'}
    return json.loads(META.read_text(encoding='utf-8'))

def parameters(decision='candidate', cover='all', confidence='all'):
    meta = metadata()
    if not meta.get('ready'):
        raise ValueError('La capa de referencia y sus evaluaciones todavía no están preparadas.')
    if decision not in ('candidate', 'review', 'excluded') or cover not in ('all', *CATEGORIES, 'unknown') or confidence not in ('all','high'):
        raise ValueError('Filtros de evaluación no válidos.')
    return {'layer': meta['layer_id'], 'rules': RULE_VERSION, 'decision': decision,
            'cover': cover, 'confidence': confidence}

FROM = ' FROM fire_detections d JOIN observation_evaluations e ON e.observation_id=d.id '
FILTER = """ WHERE e.layer_id=%(layer)s AND e.rule_version=%(rules)s
 AND e.decision=%(decision)s
 AND (%(cover)s='all' OR e.cover_category=%(cover)s)
 AND (%(confidence)s='all' OR (d.sensor='MODIS' AND CASE WHEN d.confidence SIMILAR TO '[0-9]+' THEN d.confidence::integer>=80 ELSE false END) OR (d.sensor='VIIRS' AND d.confidence='h'))
 AND d.acquired_at >= '2026-01-01T00:00:00Z'::timestamptz
 AND d.acquired_at < '2027-01-01T00:00:00Z'::timestamptz """

def summary(conn, decision='candidate', cover='all', confidence='all'):
    p = parameters(decision, cover, confidence)
    # All decisions are counted so hidden/rejected observations remain accountable.
    counts = conn.execute("SELECT e.decision,count(*) AS count" + FROM +
        " WHERE e.layer_id=%(layer)s AND e.rule_version=%(rules)s AND d.acquired_at>='2026-01-01T00:00:00Z'::timestamptz AND d.acquired_at<'2027-01-01T00:00:00Z'::timestamptz GROUP BY e.decision", p).fetchall()
    daily = conn.execute("SELECT (d.acquired_at AT TIME ZONE 'UTC')::date AS day,d.sensor,count(*) AS detections" + FROM + FILTER + ' GROUP BY day,d.sensor ORDER BY day', p).fetchall()
    bounds = conn.execute("SELECT sensor,min(acquired_at AT TIME ZONE 'UTC')::date AS first,max(acquired_at AT TIME ZONE 'UTC')::date AS last FROM fire_detections GROUP BY sensor").fetchall()
    return {'year': 2026, 'department': {'code':'PE-HUC','name':'Huánuco'},
            'daily': daily, 'weekly': [], 'grid_km': None,
            'starts': {r['sensor']:r['first'] for r in bounds},
            'ends': {r['sensor']:r['last'] for r in bounds},
            'counts': {r['decision']:r['count'] for r in counts},
            'total_selected': sum(r['detections'] for r in daily),
            'reference': metadata(), 'decision': decision, 'cover':cover,
            'limitations': ['Candidatos, no incendios confirmados.',
                'Cobertura anterior usada como contexto del centro del píxel.',
                'Máscara externa STA de FIRMS no integrada; se utiliza el tipo original NASA.',
                'No se calcula un índice armonizado validado ni un número de incendios únicos.']}

def points(conn, start, end, decision='candidate', cover='all', confidence='all', limit=20000):
    from datetime import timedelta
    p = {**parameters(decision, cover, confidence), 'start':start, 'end':end+timedelta(days=1), 'limit':limit+1}
    query = """SELECT d.id,d.latitude,d.longitude,d.acquired_at,d.sensor,d.satellite,
      d.confidence,d.frp,d.version,d.source_kind,d.fire_type,d.brightness,d.scan,d.track,d.daynight,
      e.cover_category,e.cover_code,e.decision,e.reason,e.rule_version""" + FROM + FILTER + " AND d.acquired_at>=%(start)s::date AND d.acquired_at<%(end)s::date ORDER BY d.acquired_at DESC,d.id DESC LIMIT %(limit)s"
    rows = conn.execute(query,p).fetchall()
    total = conn.execute('SELECT count(*) AS n' + FROM + FILTER + ' AND d.acquired_at>=%(start)s::date AND d.acquired_at<%(end)s::date',p).fetchone()['n']
    return {'data':rows[:limit], 'total':total, 'truncated':len(rows)>limit,
            'reference_year':metadata()['year'], 'decision':decision}
