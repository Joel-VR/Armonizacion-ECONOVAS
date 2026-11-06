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
