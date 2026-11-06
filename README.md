# IgnisTerra

IgnisTerra es un proyecto para explorar detecciones de anomalías térmicas de NASA FIRMS, con un enfoque inicial en Huánuco y Perú. Su MVP reúne una interfaz web, una API y un pipeline para validar y normalizar archivos CSV de FIRMS.

> Una detección de anomalía térmica no confirma por sí sola un incendio forestal. El proyecto no incluye observaciones reales ni métricas inventadas.

![Vue](https://img.shields.io/badge/Vue-3-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-6-646CFF?style=flat-square&logo=vite&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![NASA FIRMS](https://img.shields.io/badge/Datos-NASA%20FIRMS-0B3D91?style=flat-square)

## Tecnologías

| Área | Tecnología |
| --- | --- |
| Frontend | Vue 3, TypeScript 5.7 y Vite 6 |
| Backend | Python 3.10+ y FastAPI |
| Procesamiento de datos | Python y archivos CSV de NASA FIRMS |
| Herramientas | Node.js, npm y entornos virtuales de Python |

## Estructura del proyecto

- `frontend/`: interfaz web.
- `backend/`: API inicial.
- `data-pipeline/`: validación y normalización de CSV FIRMS.
- `data/`: datos locales sin versionar.
- `docs/`: documentación técnica y metodología.
- `scripts/`: utilidades del proyecto.

## Documentación

- [Instalación y ejecución](./docs/instalacion.md)
- [Arquitectura](./docs/arquitectura.md)
- [API](./docs/api.md)
- [Metodología de armonización](./docs/armonizacion.md)
- [Diccionario de datos](./docs/diccionario-datos.md)
- [Fuentes y limitaciones](./docs/fuentes-limitaciones.md)

## Estado del proyecto

El proyecto es un esqueleto de MVP. El mapa, los gráficos, los filtros geográficos, las estadísticas, las alertas y la armonización científica están pendientes. El pipeline todavía no alimenta la API.
