"""Read-only, parameterized event API, restricted to the active processing run."""
from datetime import timedelta
from .screening import metadata

ACTIVE = """ FROM eventos_fuego f
 JOIN ejecuciones_procesamiento r ON r.id=f.ejecucion_id AND r.activa
 JOIN departamentos a ON a.codigo=f.departamento_codigo
 JOIN paises p ON p.codigo=a.pais_codigo
 LEFT JOIN distritos dt ON dt.codigo=f.distrito_codigo
 LEFT JOIN provincias pv ON pv.codigo=dt.provincia_codigo
 JOIN fire_detections d ON d.id=f.representante_id
 JOIN evaluaciones_fuego e ON e.ejecucion_id=r.id AND e.deteccion_id=d.id
 WHERE a.codigo='PE-HUC' AND f.estado='probable' """


def current(conn):
    row=conn.execute("SELECT id,regla_version,resumen,finalizada_en FROM ejecuciones_procesamiento WHERE activa AND departamento_codigo='PE-HUC'").fetchone()
    if not row: raise ValueError('Los eventos aún no han sido preparados.')
    return row


def points(conn,start,end):
    current(conn)
    rows=conn.execute("""SELECT f.id,d.latitude,d.longitude,f.inicio AS acquired_at,
       f.ultima_deteccion,f.tipo AS event_type,f.estado AS verification_status,
       a.nombre AS department,p.nombre AS country,
       d.sensor,d.satellite,d.confidence,d.frp,d.version,d.source_kind,d.fire_type,
       d.brightness,d.scan,d.track,d.daynight,e.cobertura AS cover_category,
       e.cobertura_codigo AS cover_code,'candidate' AS decision,e.motivo AS reason,
       r.regla_version AS rule_version,
       (SELECT count(*) FROM evento_detecciones m WHERE m.evento_id=f.id) AS observation_count,
       d.id AS representative_id, pv.nombre AS province, dt.nombre AS district""" + ACTIVE + """ AND f.inicio < %s AND f.ultima_deteccion >= %s AND f.tipo IN ('incendio_forestal','quema_agricola','fuego_sin_clasificar')
       ORDER BY f.inicio DESC,f.id DESC""",(end+timedelta(days=1),start)).fetchall()
    return {'data':rows,'total':len(rows),'truncated':False,'unit':'probable_events',
            'reference_year':metadata()['year']}


def detail(conn,event_id):
    event=conn.execute('SELECT f.id,f.tipo,f.estado,f.inicio,f.ultima_deteccion,f.motivo,r.regla_version,a.nombre AS departamento,p.nombre AS pais'+ACTIVE+' AND f.id=%s',(event_id,)).fetchone()
    if not event: return None
    event['detecciones']=conn.execute("""SELECT d.id,d.latitude,d.longitude,d.acquired_at,d.sensor,
      d.satellite,d.confidence,d.frp,d.brightness,d.fire_type,d.source_file,
      e.cobertura_codigo,e.cobertura,e.motivo,e.evidencia
      FROM evento_detecciones m JOIN fire_detections d ON d.id=m.deteccion_id
      JOIN evaluaciones_fuego e ON e.ejecucion_id=m.ejecucion_id AND e.deteccion_id=m.deteccion_id
      WHERE m.evento_id=%s ORDER BY d.acquired_at,d.id""",(event_id,)).fetchall()
    return event


def summary(conn):
    run=current(conn)
    daily=conn.execute("""SELECT (d.acquired_at AT TIME ZONE 'UTC')::date AS day,d.sensor,count(*) AS detections
      FROM evento_detecciones m JOIN fire_detections d ON d.id=m.deteccion_id
      WHERE m.ejecucion_id=%s GROUP BY 1,2 ORDER BY 1,2""",(run['id'],)).fetchall()
    events_daily=conn.execute("""SELECT (inicio AT TIME ZONE 'UTC')::date AS day,tipo,count(*) AS events
      FROM eventos_fuego WHERE ejecucion_id=%s GROUP BY 1,2 ORDER BY 1,2""",(run['id'],)).fetchall()
    bounds=conn.execute("""SELECT d.sensor,min(d.acquired_at)::date AS first,max(d.acquired_at)::date AS last
      FROM evaluaciones_fuego e JOIN fire_detections d ON d.id=e.deteccion_id
      WHERE e.ejecucion_id=%s GROUP BY d.sensor""",(run['id'],)).fetchall()
    return {'year':2026,'daily':daily,'event_daily':events_daily,'weekly':[],'grid_km':None,
      'starts':{r['sensor']:r['first'] for r in bounds},'ends':{r['sensor']:r['last'] for r in bounds},
      'reference':metadata(),'total_selected':run['resumen']['accepted_observations'],
      'event_count':run['resumen']['events'],'processing':run,
      'counts':{'candidate':run['resumen']['events'],'review':run['resumen']['review'],'excluded':run['resumen']['excluded']},
      'limitations':['Agrupaciones probables, no confirmación en campo ni área quemada.',
       'Umbrales conservadores de aplicación, no un clasificador validado.',
       'Los mosaicos mixtos no permiten identificar cultivos y se mantienen en revisión.',
       'Sin máscara STA externa ni perímetros oficiales de incendios.',
       'Provincia y distrito pendientes de límites oficiales; no se inventan ubicaciones.']}
