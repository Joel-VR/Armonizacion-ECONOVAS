# API

Con el servidor activo, consulte `/docs` para el contrato OpenAPI. `GET /api/health` devuelve `{"status":"ok"}`. `GET /api/fires` devuelve una lista vacía y `status: not_loaded`: no consulta archivos ni admite filtros todavía. `/api/calendar`, `/api/statistics` y `/api/alerts` son objetivos futuros, no endpoints disponibles. No interprete una lista vacía como ausencia de focos.
