# Uso de datos satelitales por departamento del Perú

## Estado actual

La carpeta local `data/modisViirs/` puede contener descargas de NASA FIRMS de MODIS y de VIIRS a bordo de Suomi NPP, NOAA-20 y NOAA-21. Estos archivos se excluyen de Git por su tamaño y deben descargarse por separado. **La interfaz anterior permitía seleccionar 25 ámbitos departamentales**, incluido Callao, pero actualmente requiere adaptarse a las tablas originales `modis` y `viirs`. Lima combina en una sola selección los límites de Lima y Lima Metropolitana de la fuente cartográfica. Las tablas originales incluyen los cuatro productos; NOAA-20 y NOAA-21 aún no se han integrado en el análisis departamental.

## Archivos de origen

Cada carpeta en `data/modisViirs/` contiene un JSON histórico (`fire_archive_…`), un JSON casi en tiempo real (`fire_nrt_…`) y un archivo de lectura que remite a NASA FIRMS. Los NRT son provisionales; al combinar descargas nuevas con existentes debe verificarse el posible solapamiento. El importador actual no reemplaza automáticamente los datos NRT cuando aparece un producto histórico.

| Carpeta | Instrumento y satélite | Uso actual |
| --- | --- | --- |
| `MODIS C6.1` | MODIS en Terra y Aqua | Cargado en tabla original; análisis pendiente de adaptación |
| `SUOMI VIIRS C2` | VIIRS en Suomi NPP | Cargado en tabla original; análisis pendiente de adaptación |
| `J1 VIIRS C2` | VIIRS en NOAA-20 | Cargado en tabla original; no integrado en el análisis |
| `J2 VIIRS C2` | VIIRS en NOAA-21 | Cargado en tabla original; no integrado en el análisis |

Los datos son observaciones de anomalías térmicas y pueden incluir otras fuentes de calor. Cada registro no equivale necesariamente a un incendio único. Las fechas mínimas y máximas de un archivo tampoco garantizan que todas las zonas se hayan observado todos los días.

## Del archivo al departamento

1. `data-pipeline/import_raw_firms.py` lee de forma incremental los JSON de MODIS y los tres productos VIIRS y guarda sus columnas originales en las tablas `modis` y `viirs`, sin armonizar. Los archivos NRT no contienen `type`; en la tabla ese campo es NULL. La interfaz y la API anteriores dependen de `fire_detections`, por lo que todavía deben adaptarse a las nuevas tablas. Los pasos siguientes describen la metodología anterior, pendiente de volver a conectarse.
2. Los límites provienen de `frontend/public/geo/peru-departments.geojson`; se seleccionan por `shapeISO`. Lima combina los polígonos `PE-LIM` y `PE-LMA*`. La API utiliza PostGIS para seleccionar los registros cuyo centro de píxel está dentro del polígono o sobre su límite. Esto es una aproximación: no intersecta la huella completa del píxel y no modifica los límites administrativos.
3. En las vistas se puede elegir el año de 2016 a 2026, el tamaño de cuadrícula y filtros de confianza y tipo. La confianza alta se define separadamente para cada instrumento: MODIS ≥ 80 y VIIRS `h`; no son escalas equivalentes. El filtro de vegetación conocida utiliza `type = 0` y excluye tipos desconocidos, incluidos los NRT que carecen de ese campo.
4. Para el análisis semanal, las coordenadas se proyectan a una zona UTM sur (17, 18 o 19) según la longitud central de la envolvente del departamento y se asignan a una cuadrícula fija de 2, 5 o 10 km. Para cada sensor se cuenta una celda como máximo una vez por día; la suma semanal produce **celdas-día con detección**, no área quemada ni número de incendios.
5. Cada semana se compara con una referencia estacional del mismo sensor de 2016–2024 mediante un percentil empírico. Si el año consultado está dentro de la referencia se excluyen las semanas que se solapan con ese año. Cuando existen ambos percentiles comparables se muestra su promedio como **indicador experimental**, acompañado de su diferencia. Las semanas incompletas, los datos fuera del periodo disponible y los casos con demasiados empates no se presentan como un combinado válido.

La metodología y sus fórmulas se describen en [armonizacion.md](armonizacion.md). La implementación está en `backend/app/services/huanuco.py`; los endpoints se describen en [api.md](api.md).

## Para incorporar otros departamentos

Los límites permiten consultar cada departamento, pero no prueban que el área solicitada en la descarga de FIRMS cubra todo el territorio nacional. La geometría del área original de descarga no se incluye en los JSON: la cobertura geográfica y temporal debe verificarse antes de sacar conclusiones. Cada departamento usa una zona UTM fija para todas sus fechas y tamaños de cuadrícula; los que cruzan zonas pueden tener distorsiones, por lo que las comparaciones y el índice siguen siendo experimentales. Las áreas sin detecciones registradas **no deben interpretarse como áreas sin fuego**: las descargas de puntos no permiten demostrar por sí solas que hubo una observación útil sin nubes o humo.

Las vistas y el indicador son exploratorios y no sustituyen información validada para respuesta táctica. Consulte las [instrucciones de NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/download/Readme.txt) y [fuentes y limitaciones](fuentes-limitaciones.md).

## Columna departamento en las tablas originales

Las tablas `modis` y `viirs` contienen `departamento`, calculado a partir de `latitude` y `longitude` y los límites locales de geoBoundaries. Se asigna el nombre únicamente si el punto central está cubierto por un solo departamento. Lima reúne Lima y Lima Metropolitana; Callao se conserva por separado. Los puntos fuera de los límites y los que coinciden con más de un departamento quedan en NULL. El valor no identifica necesariamente dónde se encuentra todo el píxel ni demuestra cobertura satelital.

En una base existente se aplica `backend/sql/migrations/001_agregar_departamento.sql` y luego se ejecuta `python data-pipeline/asignar_departamentos.py`. El proceso conserva las demás columnas, actualiza por lotes y puede reanudarse; si se importan observaciones nuevas debe ejecutarse nuevamente para completar sus departamentos.
