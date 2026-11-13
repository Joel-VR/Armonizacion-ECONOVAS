# Diccionario de datos inicial

| Campo | Significado | Unidad/formato |
|---|---|---|
| latitude | Latitud de detección | grados decimales, -90 a 90 |
| longitude | Longitud de detección | grados decimales, -180 a 180 |
| acq_date | Fecha original de adquisición | AAAA-MM-DD |
| acq_time | Hora original UTC | HHMM; se rellena con ceros |
| acquired_at_utc | Fecha y hora derivadas | ISO 8601 UTC |
| sensor | Familia declarada por quien ejecuta el pipeline | MODIS o VIIRS |

El pipeline conserva las demás columnas originales; sus significados y unidades dependen del producto FIRMS. El sensor es declarado, no se infiere ni verifica. No se realiza deduplicación, filtrado geográfico ni control de confianza.

## Campos previstos en el detalle del frontend

El frontend muestra ejemplos sintéticos, no el resultado del pipeline. La estructura de `Detection` es una propuesta de presentación y no un contrato de API implementado. Se consultaron los diccionarios de [MODIS](https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_MODIS_Firehotspots.html) y [VIIRS](https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html).

| Campo de presentación | Origen / interpretación prevista |
| --- | --- |
| `acquiredAt` | Fecha y hora de adquisición en UTC; no fecha de inicio del incendio |
| `sensor`, `satellite` | Instrumento y plataforma; conservar procedencia individual |
| `confidence` | MODIS: escala original porcentual; VIIRS: baja, nominal o alta. No comparar como una misma variable |
| `frp` | Potencia radiativa del fuego, MW; no superficie quemada ni gravedad |
| `brightness` | MODIS: canal 21/22; VIIRS: I-4, temperatura de brillo en kelvin. La etiqueta cambia por sensor |
| `scan`, `track` | Dimensiones del píxel, km; no dimensiones de la zona quemada |
| `daynight` | Observación diurna o nocturna, D / N |
| `latitude`, `longitude` | Centro del píxel, no perímetro ni ubicación exacta del fuego |
| `department`, `country` | Contexto geográfico del ejemplo; la asignación administrativa real requerirá cruce espacial |

No se infieren provincia, distrito, tipo de quema, víctimas, área afectada o tiempo activo. La versión de producto y del método de armonización deberán llegar desde el backend al conectar observaciones reales.
