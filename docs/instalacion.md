# Instalación y ejecución

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

## Carga de datos

    python -m venv .venv
    .\.venv\Scripts\python -m pip install -r backend/requirements.txt
    .\.venv\Scripts\python data-pipeline/import_firms.py

El importador crea el esquema y lee de forma incremental los cuatro JSON de MODIS y Suomi en data/modisViirs. Cada archivo se importa en una transacción; repetirlo no inserta registros idénticos de la misma clase de fuente. No reemplaza automáticamente NRT al aparecer datos estándar; antes de cargar periodos solapados hay que reconciliarlos. J1 y J2 no se importan y los originales permanecen intactos.

## API y web

    .\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload

En otra terminal:

    cd frontend
    npm ci
    npm run dev

Vite redirige /api al puerto 8000. La API ofrece /api/status, /api/fires?start=AAAA-MM-DD&end=AAAA-MM-DD y /api/daily con los mismos parámetros. El rango máximo es de 367 días; /api/fires pagina con limit y offset. La interfaz muestra hasta 5.000 puntos más recientes, mientras que los totales y agregados diarios incluyen todo el intervalo.

El calendario muestra conteos de detecciones, no el índice de armonización propuesto, que aún no está implementado ni validado. Los datos descargados tienen cobertura geográfica y fechas limitadas; un día sin puntos no confirma ausencia de fuego.
