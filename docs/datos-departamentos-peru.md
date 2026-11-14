# Uso de datos satelitales por departamento del Perú

## Estado actual

El repositorio contiene descargas de NASA FIRMS de MODIS y de VIIRS a bordo de Suomi NPP, NOAA-20 y NOAA-21. **Actualmente la aplicación solo procesa y muestra Huánuco**, con datos de MODIS y Suomi entre 2016 y 2026. Los demás departamentos aún no están conectados. Los archivos de NOAA-20 y NOAA-21 están incluidos como fuentes disponibles, pero no se han importado ni integrado en el análisis actual.

## Archivos de origen

Cada carpeta en `data/modisViirs/` contiene un JSON histórico (`fire_archive_…`), un JSON casi en tiempo real (`fire_nrt_…`) y un archivo de lectura que remite a NASA FIRMS. Los NRT son provisionales; al combinar descargas nuevas con existentes debe verificarse el posible solapamiento. El importador actual no reemplaza automáticamente los datos NRT cuando aparece un producto histórico.

| Carpeta | Instrumento y satélite | Uso actual |
| --- | --- | --- |
| `MODIS C6.1` | MODIS en Terra y Aqua | Importado y utilizado en Huánuco |
| `SUOMI VIIRS C2` | VIIRS en Suomi NPP | Importado y utilizado en Huánuco |
| `J1 VIIRS C2` | VIIRS en NOAA-20 | Conservado; no integrado |
| `J2 VIIRS C2` | VIIRS en NOAA-21 | Conservado; no integrado |

Los datos son observaciones de anomalías térmicas y pueden incluir otras fuentes de calor. Cada registro no equivale necesariamente a un incendio único. Las fechas mínimas y máximas de un archivo tampoco garantizan que todas las zonas se hayan observado todos los días.

## Del archivo al departamento

1. `data-pipeline/import_firms.py` lee de forma incremental los JSON de MODIS y Suomi, valida coordenadas y fechas, y guarda en PostgreSQL/PostGIS la posición, fecha UTC, sensor, satélite, confianza, FRP, versión y procedencia. Las observaciones originales permanecen en los archivos.
2. El límite de Huánuco proviene de `frontend/public/geo/peru-departments.geojson`, identificado por `shapeISO = PE-HUC`. La API utiliza PostGIS para seleccionar los registros cuyo centro de píxel está dentro del polígono o sobre su límite. Esto es una aproximación: no intersecta la huella completa del píxel y no modifica los límites administrativos.
3. En las vistas se puede elegir el año de 2016 a 2026, el tamaño de cuadrícula y filtros de confianza y tipo. La confianza alta se define separadamente para cada instrumento: MODIS ≥ 80 y VIIRS `h`; no son escalas equivalentes. El filtro de vegetación conocida utiliza `type = 0` y excluye tipos desconocidos, incluidos los NRT que carecen de ese campo.
4. Para el análisis semanal, las coordenadas se proyectan a UTM 18S (EPSG:32718) y se asignan a una cuadrícula fija de 2, 5 o 10 km. Para cada sensor se cuenta una celda como máximo una vez por día; la suma semanal produce **celdas-día con detección**, no área quemada ni número de incendios.
5. Cada semana se compara con una referencia estacional del mismo sensor de 2016–2024 mediante un percentil empírico. Si el año consultado está dentro de la referencia se excluyen las semanas que se solapan con ese año. Cuando existen ambos percentiles comparables se muestra su promedio como **indicador experimental**, acompañado de su diferencia. Las semanas incompletas, los datos fuera del periodo disponible y los casos con demasiados empates no se presentan como un combinado válido.

La metodología y sus fórmulas se describen en [armonizacion.md](armonizacion.md). La implementación está en `backend/app/services/huanuco.py`; los endpoints se describen en [api.md](api.md).

## Para incorporar otros departamentos

El GeoJSON también contiene límites de otros departamentos, pero su presencia no implica que ya se consulten ni que los datos de FIRMS descargados cubran todo el territorio nacional. Para habilitar uno debe seleccionarse su geometría, comprobar la cobertura espacial y temporal de los archivos, aplicar la selección espacial y validar la proyección, las cuadrículas y la línea base para ese territorio. Las áreas sin detecciones registradas **no deben interpretarse como áreas sin fuego**: las descargas de puntos no permiten demostrar por sí solas que hubo una observación útil sin nubes o humo.

Las vistas y el indicador son exploratorios y no sustituyen información validada para respuesta táctica. Consulte las [instrucciones de NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/download/Readme.txt) y [fuentes y limitaciones](fuentes-limitaciones.md).
