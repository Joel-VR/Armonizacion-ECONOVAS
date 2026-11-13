# Arquitectura

El frontend Vue consulta la API FastAPI a través de /api. PostgreSQL con PostGIS almacena las detecciones normalizadas e indexa geometría y fecha. El importador Python lee en streaming los JSON históricos y NRT de MODIS y VIIRS Suomi, conserva satélite, versión y archivo de origen y evita duplicados exactos por fuente. El esquema está en backend/sql/schema.sql.

La interfaz consulta puntos paginados para el mapa y conteos diarios para el calendario. Se dibujan como máximo 5.000 puntos; el total incluye todos los resultados. La API no aplica aún filtros espaciales ni calcula el índice de armonización. La ausencia de detecciones no demuestra ausencia de fuego ni cobertura adecuada. El reemplazo de datos NRT por estándar aún no está automatizado.

El proyecto usa PostgreSQL local con PostGIS. La API y el importador comparten la configuración DB_HOST, DB_PORT, DB_NAME, DB_USER y DB_PASSWORD desde el entorno o el archivo .env local. Consulte instalación.md.
