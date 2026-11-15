> **Actualización: backend de eventos.** El mapa ya usa agrupaciones probables con filtro estricto y separa agrícola de mosaico mixto/pasto. El modelo agrega ubicaciones, fuentes, reglas, ejecuciones, evaluaciones y eventos con sus detecciones. Consulte [modelo, reproducción y límites](docs/backend-eventos.md). La sección de evaluación rápida de abajo describe la fase anterior; sus 414 candidatos ya no son los puntos publicados por el mapa.

# Brinco Alerta

Brinco Alerta es un proyecto para explorar observaciones satelitales relacionadas con el estudio de incendios forestales y quemas agrícolas, con un enfoque inicial en Huánuco y Perú. Reúne una interfaz web, una API y un pipeline para importar observaciones JSON de NASA FIRMS. Su identidad visual utiliza un conejo bombero como símbolo de protección de la vida silvestre.

> Una detección de anomalía térmica no confirma por sí sola un incendio ni su causa. La interfaz rápida trabaja exclusivamente con Huánuco en 2026 y utiliza cobertura MapBiomas 2025 como referencia anterior. Separa posibles fuegos, casos por revisar y exclusiones por tipo original NASA, sin borrar observaciones.

## Versión rápida: Huánuco 2026

- Mapa temático local de bosque, agropecuario, agua, urbano y otras coberturas; cinco capas de unos 700 KB en total, recortadas a Huánuco. No carga imágenes satelitales por defecto. El fondo Esri es opcional.
- MapBiomas Perú, Colección 4, año 2025. El recorte oficial se obtuvo mediante la exportación personalizada de la plataforma; la URL nacional anunciada devolvía HTTP 403 al preparar esta versión.
- `reference_layers` conserva procedencia, año, licencia, CRS, checksum y metadatos; `observation_evaluations` relaciona cada observación con la capa, versión de regla, cobertura, decisión y motivo. Migración aditiva: `backend/sql/context.sql`.
- Los candidatos requieren tipo original 0, confianza inicial MODIS ≥30 o VIIRS n/h y centro de píxel en bosque/agropecuario. Los tipos 1/2/3 se excluyen de la vista principal. Los desconocidos/NRT, baja confianza, agua, urbano y otras coberturas pasan a revisión. No se infiere causa o confirmación del incendio.
- Mapa, calendario y gráfico consultan la misma evaluación. Los totales de las pestañas describen todo 2026; el gráfico y mapa aplican cobertura y confianza seleccionadas.
- La máscara externa de anomalías térmicas estáticas de FIRMS (STA) **no está integrada** en esta entrega. Se utiliza el tipo original de NASA; no se promete eliminar todas las fuentes térmicas ajenas a vegetación.
- La cobertura 2025 no demuestra el uso del suelo en 2026. La clasificación consulta el raster original en el centro del píxel, no su huella completa. El dibujo del navegador está simplificado a 150 m y no se utiliza para evaluar observaciones.
- Esta entrega normaliza contexto y evaluación, conservando MODIS/VIIRS. No agrupa incendios únicos, no valida una calibración entre sensores y no calcula el índice histórico anterior en la interfaz rápida. Los endpoints departamentales antiguos siguen disponibles como experimentales.

### Preparar las capas y la base en otra PC

Después de importar los JSON FIRMS, descargue en la plataforma MapBiomas un GeoTIFF de **Huánuco → Cobertura → 2025** y guárdelo en `data/raw/mapbiomas-huanuco-2025-col4.tif`. No basta copiar las capas PNG: la evaluación de la base debe generarse también.

```powershell
.\.venv\Scripts\python -m pip install -r data-pipeline/requirements-map.txt
.\.venv\Scripts\python data-pipeline/prepare_huanuco.py --source data/raw/mapbiomas-huanuco-2025-col4.tif --year 2025 --collection 4
```

El script conserva los JSON y `fire_detections`; crea dos tablas adicionales y las evaluaciones. El recorte original y el respaldo no se versionan. Las cinco capas ligeras y sus metadatos sí se incluyen para que el dibujo esté disponible. Se preparó un respaldo local anterior a la migración en `data/backups/`, excluido de Git.

Verificación del backend: `.\.venv\Scripts\python -m unittest discover -s backend/tests -v`. La metodología y los límites de esta entrega están en [evaluación rápida](docs/evaluacion-rapida.md).

Consulte [instalación y carga de datos](docs/instalacion.md), [arquitectura](docs/arquitectura.md) y [metodología propuesta](docs/armonizacion.md) y [uso de datos por departamento](docs/datos-departamentos-peru.md).

## Ejecutar el frontend

Requiere Node.js 22.13 o superior en la rama 22, o una versión LTS posterior compatible con las dependencias.

```powershell
cd frontend
npm ci
npm run dev
```

Abra la dirección indicada por Vite. Para comprobar el frontend antes de hacer push:

```powershell
npm test
npm run build
```

Las imágenes satelitales de Esri requieren conexión. Consulte [fuentes y limitaciones](docs/fuentes-limitaciones.md) y [arquitectura](docs/arquitectura.md).
