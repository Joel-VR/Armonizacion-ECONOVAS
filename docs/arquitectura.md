# Arquitectura

El navegador consume la API FastAPI; en desarrollo Vite redirige `/api` al puerto 8000. El pipeline opera por separado sobre CSV locales, con salida en `data/processed`. La conexión entre salida y API aún no existe. PostgreSQL/PostGIS es opcional y no está configurado.

MapLibre, ECharts y Tailwind son tecnologías previstas, aún no integradas. El procesamiento histórico y reciente debe mantenerse separado, con metadatos de procedencia y versión. No se incluye descarga automática.
