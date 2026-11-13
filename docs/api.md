# API

Consulte /docs para el contrato OpenAPI. GET /api/health comprueba que el proceso responde; no verifica la base. GET /api/status devuelve el total y las fechas extremas de registros cargados.

GET /api/fires requiere start y end (fechas inclusivas UTC), admite limit y offset y devuelve registros y total. GET /api/daily acepta el mismo intervalo y devuelve conteos por fecha y sensor. El intervalo no puede exceder 367 días. Una conexión no disponible o un esquema ausente devuelve 503.

Los conteos son detecciones y no incendios únicos. La API no implementa aún consultas espaciales ni armonización científica.
