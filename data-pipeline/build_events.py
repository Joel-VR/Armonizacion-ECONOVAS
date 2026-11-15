"""Transactional, repeatable Huanuco 2026 event derivation; no raw deletes."""
import json
import math
import sys
from pathlib import Path

import rasterio
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
from app.main import connection
from app.services.huanuco import geometry
from app.services.screening import metadata
from app.services.event_rules import VERSION, PARAMETERS, assess, cover, high, corroborated, group_events, event_type, event_type


def main():
    meta = metadata()
    with connection() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(72841026)")
        conn.execute((ROOT/'backend/sql/events.sql').read_text(encoding='utf-8'))
        conn.execute("INSERT INTO paises VALUES ('PE','Perú') ON CONFLICT DO NOTHING")
        conn.execute("INSERT INTO departamentos VALUES ('PE-HUC','PE','Huánuco',ST_SetSRID(ST_GeomFromGeoJSON(%s),4326)) ON CONFLICT DO NOTHING", (geometry(),))
        conn.execute('INSERT INTO reglas_procesamiento(version,parametros) VALUES(%s,%s) ON CONFLICT DO NOTHING', (VERSION,Jsonb(PARAMETERS)))
        stored=conn.execute('SELECT parametros FROM reglas_procesamiento WHERE version=%s',(VERSION,)).fetchone()['parametros']
        if stored != PARAMETERS:
            raise ValueError('Los parámetros cambiaron. Incremente la versión para conservar trazabilidad.')
        run = conn.execute("INSERT INTO ejecuciones_procesamiento(regla_version,capa_id,departamento_codigo) VALUES(%s,%s,'PE-HUC') RETURNING id", (VERSION,meta['layer_id'])).fetchone()['id']
        rows = conn.execute("""SELECT d.* FROM fire_detections d, departamentos a
          WHERE a.codigo='PE-HUC' AND ST_Covers(a.limite,d.geom)
          AND d.acquired_at>='2026-01-01' AND d.acquired_at<'2027-01-01' ORDER BY d.acquired_at,d.id""").fetchall()
        conn.execute("""INSERT INTO fuentes_datos(archivo,sensor,satelite,producto,modalidad)
          SELECT DISTINCT source_file,sensor,satellite,version,source_kind FROM fire_detections d,departamentos a
          WHERE a.codigo='PE-HUC' AND ST_Covers(a.limite,d.geom) AND d.acquired_at>='2026-01-01' AND d.acquired_at<'2027-01-01' ON CONFLICT DO NOTHING""")
        sources = {(r['archivo'],r['sensor'],r['satelite'],r['producto'],r['modalidad']):r['id'] for r in conn.execute('SELECT * FROM fuentes_datos').fetchall()}
        evaluations = {}
        raster = ROOT/'data/processed'/f"huanuco-mapbiomas-{meta['year']}.tif"
        with rasterio.open(raster) as src:
            if src.crs.to_epsg() != 4326: raise ValueError('El muestreo requiere EPSG:4326; transforme antes el recorte.')
            pixels = src.read(1)
            for row in rows:
                # Nominal-width context only, not an inferred burned perimeter.
                radius = 500 if row['sensor']=='MODIS' else 187.5
                dx = radius/(111320*math.cos(math.radians(row['latitude'])))
                dy = radius/111320
                codes=[]
                offsets=(-1,-0.5,0,0.5,1)
                for oy in offsets:
                    for ox in offsets:
                        rr,cc = src.index(row['longitude']+ox*dx,row['latitude']+oy*dy)
                        codes.append(int(pixels[rr,cc]) if 0<=rr<src.height and 0<=cc<src.width else 0)
                row['cover_code']=codes[12]
                row['cover_category']=cover(codes[12])
                evaluations[row['id']]=list(assess(row,codes))
        eligible = [r for r in rows if evaluations[r['id']][0]=='apta']
        accepted=[]
        for row in eligible:
            result = evaluations[row['id']]
            peers = [r['id'] for r in eligible if r['id']!=row['id'] and corroborated(row,r)]
            result[2]['corroborating_ids']=peers
            if not high(row) and not peers:
                result[0]='revision'
                result[1]='Señal sin confianza alta ni corroboración independiente dentro del radio temporal y espacial; queda para revisión.'
            else:
                result[1]=('Tipo NASA 0; ' if row['fire_type']=='0' else 'Tipo NRT omitido; ') + ('cobertura forestal.' if row['cover_category']=='forest' else 'cobertura agrícola.' if row['cover_category']=='agriculture' else 'mosaico mixto; causa por confirmar.') + (' confianza alta.' if high(row) else ' corroboración cercana.')
                accepted.append(row)
        with conn.cursor().copy('COPY evaluaciones_fuego(ejecucion_id,deteccion_id,fuente_id,cobertura_codigo,cobertura,resultado,motivo,evidencia) FROM STDIN') as cp:
            for row in rows:
                result,reason,evidence=evaluations[row['id']]
                source=sources[(row['source_file'],row['sensor'],row['satellite'],row['version'],row['source_kind'])]
                cp.write_row((run,row['id'],source,row['cover_code'],row['cover_category'],result,reason,Jsonb(evidence)))
        groups=group_events(accepted)
        for group in groups:
            representative=max(group,key=lambda r:(high(r),r['frp'], -r['id']))
            kind=event_type(representative['cover_category'])
            reason='Agrupación de detecciones cercanas en tiempo y espacio; posible causa sugerida por cobertura, pendiente de verificación.'
            event=conn.execute("""INSERT INTO eventos_fuego(ejecucion_id,departamento_codigo,tipo,inicio,ultima_deteccion,representante_id,motivo)
               VALUES(%s,'PE-HUC',%s,%s,%s,%s,%s) RETURNING id""",(run,kind,group[0]['acquired_at'],group[-1]['acquired_at'],representative['id'],reason)).fetchone()['id']
            for row in group:
                conn.execute('INSERT INTO evento_detecciones VALUES(%s,%s,%s)',(event,run,row['id']))
        conn.execute("UPDATE eventos_fuego f SET distrito_codigo=(SELECT t.codigo FROM distritos t JOIN fire_detections d ON d.id=f.representante_id WHERE ST_Covers(t.limite,d.geom) ORDER BY t.codigo LIMIT 1) WHERE f.ejecucion_id=%s", (run,))
        summary={'observations':len(rows),'accepted_observations':len(accepted),'events':len(groups),
                 'excluded':sum(v[0]=='excluida' for v in evaluations.values()),
                 'review':sum(v[0]=='revision' for v in evaluations.values())}
        conn.execute("UPDATE ejecuciones_procesamiento SET activa=false WHERE departamento_codigo='PE-HUC' AND activa")
        conn.execute('UPDATE ejecuciones_procesamiento SET activa=true, finalizada_en=now(),resumen=%s WHERE id=%s',(Jsonb(summary),run))
        print(json.dumps({'run':run,**summary}))


if __name__=='__main__': main()
