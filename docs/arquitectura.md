# Arquitectura

El frontend Vue consulta la API FastAPI a través de /api. PostgreSQL con PostGIS almacena las detecciones normalizadas e indexa geometría y fecha. El importador Python lee en streaming los JSON históricos y NRT de MODIS y VIIRS Suomi, conserva satélite, versión y archivo de origen y evita duplicados exactos por fuente. El esquema está en backend/sql/schema.sql.

La interfaz consulta puntos del mapa (hasta 20.000 por intervalo, con aviso de truncamiento), conteos diarios y agregados semanales. La API incluye un análisis experimental para departamentos del Perú entre 2016 y 2026 con filtro espacial PostGIS, agregación por celda-día y línea base estacional 2016–2024. La ausencia de detecciones no demuestra ausencia de fuego ni cobertura adecuada. El reemplazo de datos NRT por estándar aún no está automatizado.

El proyecto usa PostgreSQL local con PostGIS. La API y el importador comparten la configuración DB_HOST, DB_PORT, DB_NAME, DB_USER y DB_PASSWORD desde el entorno o el archivo .env local. Consulte instalación.md.

La interfaz permite seleccionar 25 ámbitos departamentales y años 2016–2026. Usa celdas de 2, 5 o 10 km en la zona UTM sur 17, 18 o 19 elegida por el centro de la envolvente del departamento, coordenadas centradas en el píxel y semanas UTC completas. Los datos sin tipo quedan excluidos al seleccionar vegetación conocida; este filtro restringe el final utilizable al producto histórico. Los percentiles no corrigen cobertura desconocida y el combinado es experimental.
