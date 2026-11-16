# Instalación y ejecución

> Estado actual: la tabla normalizada `fire_detections` fue reemplazada por las tablas `modis` y `viirs` con columnas originales. La importación normalizada anterior está deshabilitada y las vistas y consultas que dependen de `fire_detections` todavía requieren adaptación.

Requisitos: Python 3.10+, Node.js 22.13+ o LTS compatible y PostgreSQL local con PostGIS instalado.

## Base de datos local

Cree una base llamada `brinco` en su servidor PostgreSQL local y asegúrese de que PostGIS esté instalado. El usuario configurado necesita permisos para crear tablas y la extensión PostGIS; si no puede crearla, un administrador debe habilitarla previamente en esa base con `CREATE EXTENSION postgis;`.

Copie `.env.example` a `.env` en la raíz y complete las variables de su instalación:

    DB_HOST=127.0.0.1
    DB_PORT=5432
    DB_NAME=brinco
    DB_USER=postgres
    DB_PASSWORD=su_contraseña

La API y el importador leen el archivo `.env` automáticamente. Las variables ya definidas en el entorno tienen prioridad. El archivo `.env` está excluido de Git; no comparta credenciales. No se requiere Docker ni URL de conexión.

## Conexión a Neon con indicadores semanales

Para usar una base Neon que contiene únicamente `public.datos_armonizados`, configure en `.env` los valores separados del panel de Neon:

```dotenv
DB_HOST=host-de-neon
DB_PORT=5432
DB_NAME=nombre-de-base
DB_USER=usuario
DB_PASSWORD=contraseña
DB_SSLMODE=require
DB_DATA_SOURCE=armonizados
```

Reinicie la API después de cambiar el archivo. Las variables de entorno del sistema prevalecen sobre `.env`. Seleccione 5 km, todas las confianzas y todos los tipos: la tabla fue calculada con esos parámetros. El análisis histórico y el calendario en modo armonizado leen los resultados semanales experimentales. Esta tabla no contiene observaciones diarias, puntos ni geometrías por celda, por lo que esas vistas no se pueden reconstruir a partir de ella. Los endpoints antiguos que consultan `fire_detections` también requieren esa tabla y PostGIS. Para volver a PostgreSQL local, ajuste las credenciales y elimine `DB_DATA_SOURCE` y `DB_SSLMODE` si no los necesita.

También puede usar los nombres de variables de Neon: `PGHOST`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGSSLMODE` y `PGCHANNELBINDING`. Opcionalmente, use `PGPORT`; si se omite, el puerto es 5432. Añada `DB_DATA_SOURCE=armonizados`. Si `PGHOST` está definido en ese modo, se usa el grupo `PG*` completo: por ejemplo, `PGUSER` debe contener el usuario de Neon y no se sustituye con `DB_USER`. En el modo local se prioriza el grupo `DB_*`. Las variables distinguen mayúsculas de minúsculas en algunos sistemas.

Si la tabla de Neon solo tiene indicadores y existe otra base PostgreSQL local con las tablas de eventos ya preparadas, puede consultar ambas a la vez. Agregue al `.env`:

```dotenv
EVENTS_DB_HOST=127.0.0.1
EVENTS_DB_PORT=5432
EVENTS_DB_NAME=econovas
EVENTS_DB_USER=postgres
EVENTS_DB_PASSWORD=contraseña_local
```

La base de eventos debe contener las tablas y una ejecución activa descritas en [backend de eventos](backend-eventos.md); configurar la conexión no crea ni procesa los eventos. Los indicadores semanales de Neon son precalculados sin filtros de eventos: para obtener valores filtrados se necesitan datos originales y volver a calcularlos, no se pueden derivar de esa tabla.

### Subir observaciones originales a Neon

Con las variables `PG*` de Neon y las variables `EVENTS_DB_*` o `DB_*` de la base local configuradas en `.env`, ejecute desde la raíz. Si existen ambos grupos locales, se usa `EVENTS_DB_*`:

```powershell
.\.venv\Scripts\python data-pipeline/subir_observaciones_neon.py
```

El script copia todas las filas y columnas originales de `public.modis` y `public.viirs`, incluido `departamento`, mediante una sola transacción en Neon. Exige que ambas tablas locales tengan datos y que ambas tablas de destino estén vacías; si ocurre un error revierte la carga. No modifica `datos_armonizados`. `--crear-tablas` solo crea las dos tablas si faltan, sin copiar registros. Se necesita espacio suficiente en Neon. Esta copia no genera eventos ni sus evaluaciones, ni recalcula indicadores con filtros.

## Carga de datos

    python -m venv .venv
    .\.venv\Scripts\python -m pip install -r backend/requirements.txt
    .\.venv\Scripts\python data-pipeline/import_raw_firms.py

El importador de datos originales lee los ocho JSON de MODIS y los tres satélites VIIRS de manera incremental. Requiere que las tablas `modis` y `viirs` existan y estén vacías. Carga los ocho archivos en una sola transacción, que se revierte ante un error; conserva los campos originales y usa NULL cuando falta `type` en los NRT. No armoniza ni deduplica observaciones. Los datos originales permanecen intactos.

## API y web

    .\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload

En otra terminal:

    cd frontend
    npm ci
    npm run dev

Vite redirige /api al puerto 8000. La API ofrece /api/status, /api/fires?start=AAAA-MM-DD&end=AAAA-MM-DD y /api/daily con los mismos parámetros. El rango máximo es de 367 días; /api/fires pagina con limit y offset. El mapa departamental muestra hasta 20.000 puntos y avisa si se truncan; los agregados incluyen todo el intervalo.

El calendario muestra detecciones y un indicador relativo experimental calculado por sensor; la armonización no está validada. Los datos descargados tienen cobertura geográfica y fechas limitadas; un día sin puntos no confirma ausencia de fuego.
