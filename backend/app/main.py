from fastapi import FastAPI

app = FastAPI(title="IGNISTERRA API", version="0.1.0")

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/fires")
def fires():
    return {"data": [], "status": "not_loaded", "message": "No hay datos cargados; los filtros aún no están implementados."}
