# T'UKRI · Monitoreo y Armonización Satelital del Territorio

[![Vue 3](https://img.shields.io/badge/Vue-3.5-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-6.0-646CFF?style=flat-square&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![NASA FIRMS](https://img.shields.io/badge/Datos-NASA%20FIRMS-0B3D91?style=flat-square)](https://firms.modaps.eosdis.nasa.gov/)
[![MapBiomas Perú](https://img.shields.io/badge/Cobertura-MapBiomas%20Col.%204-298743?style=flat-square)](https://peru.mapbiomas.org/)

**T'UKRI** es una plataforma científica y cartográfica desarrollada para el monitoreo, armonización y contextualización territorial de anomalías térmicas satelitales en los **25 departamentos del Perú**. 

Combina los sensores satelitales de la **NASA (MODIS y VIIRS)** con la serie histórica de cobertura de suelo de **MapBiomas Perú (Colección 4, 2025)** para resolver el problema crítico de la gestión del fuego: **diferenciar quemas agrícolas controladas de incendios forestales destructivos en masa boscosa continua**.

> **Principio de rigor científico:** Una anomalía térmica satelital indica radiación infrarroja en superficie al momento del sobrevuelo polar. T'UKRI no inventa alertas; cruza fuentes abiertas y oficiales de la NASA, INEI y MapBiomas para brindar contexto territorial procesable y auditable.

---

## 🌟 Características Principales

1. **Armonización Sensor-a-Sensor (NASA FIRMS):**
   * Cobertura nacional completa para los **25 departamentos del Perú** (más de 2.4 millones de registros históricos y NRT).
   * Normalización espacial a **celdas-día de 5 km** para neutralizar el sesgo de resolución entre VIIRS (375 m) y MODIS (1 km).
   * Detección de anomalías estadísticas y desacuerdo inter-sensor respecto a la línea base histórica (2016–2024).

2. **Diferenciación Territorial con MapBiomas Perú (Col. 4):**
   * Cruce espacial punto a punto con resolución nativa de 150 m (caso piloto de alta resolución en Huánuco).
   * Clasificación automatizada:
     * 🌲 **Bosque Natural:** Alerta crítica de incendio forestal o deforestación activa.
     * 🌾 **Zona Agropecuaria:** Quema de rastrojo y preparación de suelos para siembra.
     * 🏞️ **Mosaico Mixto:** Interfase agro-forestal de alta vulnerabilidad.
     * 🍂 **Otras Coberturas:** Pastizales andinos y pajonales de puna.

3. **Límites y Distritos Oficiales del Perú (INEI):**
   * Delimitación territorial de los 84 distritos de Huánuco con asignación exacta mediante algoritmo *Point-in-Polygon*.
   * Capa de referencia toponímica satelital (*Esri World Reference*) activa en los 25 departamentos.

4. **Calendario Departamental de Quemas:**
   * Análisis de estacionalidad histórica mensual y semanal para anticipar la temporada de fuego y orientar brigadas.

5. **Exportación Abierta y Reproducible:**
   * Descarga instantánea de los focos filtrados en formatos **CSV** y **GeoJSON** con atributos enriquecidos (sensores, confianza, FRP, distrito oficial y cobertura MapBiomas).

---

## 🏗️ Arquitectura y Tecnologías

| Componente | Tecnologías | Propósito |
| --- | --- | --- |
| **Frontend** | Vue 3, TypeScript 5.7, Vite 6, MapLibre GL, Lucide Icons, Canvas API | Visor cartográfico interactivo, clasificación en cliente y exportaciones. |
| **Backend** | Python 3.11+, FastAPI, Psycopg 3 | API REST de consulta de observaciones, agregaciones y cálculo de percentiles. |
| **Base de Datos** | PostgreSQL 16 + PostGIS | Almacén relacional espacial optimizado con índices GiST y B-Tree. |
| **Datos Geoespaciales** | NASA FIRMS (CSV/JSON), MapBiomas Perú GeoTIFF/PNG, INEI geoBoundaries | Fuentes primarias de calor, cobertura vegetal y límites políticos. |

---

## 📂 Estructura del Repositorio

* `frontend/`: Aplicación cliente (Vue 3, componentes cartográficos, visualizador MapLibre, estilos).
* `backend/`: API FastAPI con servicios de armonización, endpoints departamentales y calendario.
* `data-pipeline/`: Scripts para ingesta de datos NASA FIRMS, recorte de rásters MapBiomas y agregaciones.
* `docs/`: Documentación técnica, supuestos, limitaciones y justificación metodológica.
* `data/`: Insumos geoespaciales locales (GeoJSON distrital, metadatos y máscaras).

---

## 🚀 Inicio Rápido

### Requisitos
* **Node.js** 20.x o 22.x
* **Python** 3.10+
* **PostgreSQL** 15+ con extensión **PostGIS** (o conexión a base de datos remota Neon)

### 1. Levantar el Frontend
```bash
cd frontend
npm install
npm run dev
```
La interfaz estará disponible en `http://localhost:5173/`.

### 2. Levantar el Backend (Opcional para desarrollo local)
```bash
cd backend
python -m venv .venv
# En Windows:
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
La API interactiva (Swagger) estará disponible en `http://localhost:8000/docs`.

### 3. Pruebas y Verificación
```bash
# Frontend unit tests
npm test --prefix frontend

# Frontend production build
npm run build --prefix frontend
```

---

## 📚 Documentación Técnica Detallada

* [Metodología de Armonización Científica](./docs/armonizacion.md)
* [Evaluación Rápida y Reglas de Cobertura](./docs/evaluacion-rapida.md)
* [Fuentes, Supuestos y Limitaciones](./docs/fuentes-limitaciones.md)
* [Uso de Datos por Departamento](./docs/datos-departamentos-peru.md)
* [Especificación de la API REST](./docs/api.md)
* [Instalación y Configuración](./docs/instalacion.md)

---

## 📄 Licencia y Atribución

* **Código fuente:** MIT License.
* **Datos satelitales:** NASA FIRMS (Open Data Policy).
* **Cobertura de suelo:** MapBiomas Perú (Colección 4, CC BY 4.0).
* **Cartografía política:** INEI y geoBoundaries (Open License).
