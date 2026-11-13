# Instalación y ejecución

Requisitos: Python 3.10 o superior para la API y el pipeline; Node.js 22.13 o superior en la rama 22, o una LTS posterior compatible, para el frontend. La demostración del frontend funciona sin iniciar la API y no necesita Laragon.

Para mostrar solamente la web, desde la raíz:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Para preparar también el backend, desde la raíz:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.txt -r data-pipeline/requirements.txt
Set-Location frontend
npm ci
npm run dev
```

En otra terminal, desde la raíz:

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload
```

Abra la URL indicada por Vite y `http://127.0.0.1:8000/docs`. Para procesar un CSV descargado manualmente:

```powershell
.\.venv\Scripts\python data-pipeline/normalize.py data/raw/entrada.csv data/processed/salida.csv --sensor VIIRS
```

Verificación del frontend: `npm test` y `npm run build` dentro de `frontend`. `npm run preview` sirve la compilación de producción. Las pruebas requieren Node con soporte de eliminación de tipos (incluido en la versión indicada). Para backend y pipeline: `python -m compileall backend/app data-pipeline` y visita a `/api/health`. El pipeline no alimenta aún la API ni el frontend. Mantenga la clave FIRMS fuera del repositorio.
