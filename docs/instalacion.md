# Instalación y ejecución

Requisitos: Python 3.10 o superior y Node.js compatible con Vite 6 (Node 18 o 20 o superior; consulte la documentación de Vite para versiones específicas). Desde PowerShell, en la raíz:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.txt -r data-pipeline/requirements.txt
Set-Location frontend
npm install
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

Verificación: `npm run build` dentro de `frontend`, `python -m compileall backend/app data-pipeline` y visita a `/api/health`. El pipeline no alimenta aún la API. Mantenga la clave FIRMS fuera del repositorio.
