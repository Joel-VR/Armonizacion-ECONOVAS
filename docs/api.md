# API

Consulte /docs para el contrato OpenAPI. GET /api/health comprueba que el proceso responde; no verifica la base. GET /api/status devuelve el total y las fechas extremas de registros cargados.

GET /api/fires requiere start y end (fechas inclusivas UTC), admite limit y offset y devuelve registros y total. GET /api/daily acepta el mismo intervalo y devuelve conteos por fecha y sensor. El intervalo no puede exceder 367 días. Una conexión no disponible o un esquema ausente devuelve 503.

Los conteos son detecciones y no incendios únicos. La API no implementa aún consultas espaciales ni armonización científica.

GET /api/huanuco/analysis acepta year (2016–2026), grid (2, 5 o 10), confidence (all o high) y fire_type (all o vegetation); devuelve conteos diarios y celdas-día semanales del año solicitado, percentiles por sensor y fecha límite de cada fuente. La referencia usa semanas completas 2016–2024; los ceros son ausencia de detecciones registradas, no cobertura confirmada. GET /api/huanuco/points acepta start y end del mismo año entre 2016 y 2026 y los filtros confidence y fire_type; devuelve hasta 20.000 puntos y marca truncamiento.

Para los años 2016–2024, la referencia estacional excluye todas las semanas que se solapan con el año consultado. Las semanas que cruzan el límite del año se marcan incompletas.

GET /api/huanuco/cells (compatibilidad con Huánuco) acepta start (lunes de una semana ISO completa dentro del año), grid (2, 5 o 10), confidence y fire_type. Devuelve geometrías recortadas a Huánuco para las celdas con detecciones en la semana y un índice experimental por celda, calculado con la referencia estacional de cada sensor; null significa no comparable. Las celdas sin detecciones no se muestran y no prueban ausencia de fuego o cobertura.

GET /api/departments devuelve los 25 ámbitos disponibles y la zona UTM de cada uno. GET /api/departments/{code}/analysis, /points y /cells aceptan los mismos parámetros que sus equivalentes /api/huanuco; estos se conservan por compatibilidad. Lima une Lima y Lima Metropolitana; Callao se consulta por separado. Los JSON originales no documentan el polígono de descarga, por lo que la cobertura de cada departamento es desconocida.
