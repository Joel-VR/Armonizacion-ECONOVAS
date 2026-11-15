"""Render local thematic legend using the strict event land-use categories."""
import json
from pathlib import Path
import sys
import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, transform_bounds
from rasterio.enums import Resampling
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.services.event_rules import cover


def main():
    public=ROOT/'frontend/public/geo/huanuco'
    meta=json.loads((public/'metadata.json').read_text(encoding='utf-8'))
    definitions=[('forest','Bosque','#298743'),('agriculture','Agrícola','#f2cf45'),
      ('mixed','Mosaico mixto','#e7d9b1'),('water','Agua','#348de5'),
      ('urban','Urbano','#d55b56'),('other','Otras coberturas','#c4cbd2')]
    with rasterio.open(ROOT/'data/processed'/f"huanuco-mapbiomas-{meta['year']}.tif") as source:
        affine,width,height=calculate_default_transform(source.crs,'EPSG:3857',source.width,source.height,*source.bounds,resolution=150)
        display=np.zeros((height,width),dtype='uint8')
        reproject(source=rasterio.band(source,1),destination=display,src_transform=source.transform,
          src_crs=source.crs,dst_transform=affine,dst_crs='EPSG:3857',resampling=Resampling.nearest)
        groups=np.zeros(display.shape,dtype='uint8')
        names=[d[0] for d in definitions]
        for code in np.unique(display):
            cat=cover(int(code))
            if cat=='unknown': continue
            cat=cat if cat in names else 'other'
            groups[display==code]=names.index(cat)+1
        layers=[]
        for index,(name,label,color) in enumerate(definitions,1):
            rgba=np.zeros((*display.shape,4),dtype='uint8')
            rgba[groups==index]=[int(color[i:i+2],16) for i in (1,3,5)]+[255]
            Image.fromarray(rgba).save(public/f'{name}.png',optimize=True)
            layers.append(dict(id=name,label=label,color=color,url=f'/geo/huanuco/{name}.png'))
        left,bottom,right,top=rasterio.transform.array_bounds(height,width,affine)
        w,s,e,n=transform_bounds('EPSG:3857','EPSG:4326',left,bottom,right,top)
        meta.update(layers=layers,coordinates=[[w,n],[e,n],[e,s],[w,s]],
          display_classification='Crop codes 35,40; mixed 21 separated; pastures/plantations in other.')
        (public/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Leyenda estricta preparada: agricultura y mosaico separados.')


if __name__=='__main__': main()
