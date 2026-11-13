# Brinco Alerta

Brinco Alerta es un proyecto para explorar observaciones satelitales relacionadas con el estudio de incendios forestales y quemas agrícolas, con un enfoque inicial en Huánuco y Perú. Reúne una interfaz web, una API y un pipeline para validar y normalizar archivos CSV de NASA FIRMS. Su identidad visual utiliza un conejo bombero como símbolo de protección de la vida silvestre.

> Una detección de anomalía térmica no confirma por sí sola un incendio forestal ni una quema agrícola. La interfaz utiliza observaciones **ficticias y etiquetadas** para demostrar sus funciones. No incluye datos reales cargados, alertas operativas ni armonización científica validada.

![Vue](https://img.shields.io/badge/Vue-3-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-6-646CFF?style=flat-square&logo=vite&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![NASA FIRMS](https://img.shields.io/badge/Datos-NASA%20FIRMS-0B3D91?style=flat-square)

## Tecnologías

| Área | Tecnología |
| --- | --- |
| Frontend | Vue 3, TypeScript y Vite 6 |
| Mapas y visualización | MapLibre GL JS 6, ECharts 6 |
| Interfaz | Tailwind CSS 4, estilos propios y Lucide para Vue |
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

El frontend es un prototipo funcional con:

- Identidad Brinco Alerta, logo e icono de pestaña, navegación y diseño adaptable a móvil.
- Una sola superficie para alternar entre globo interactivo y país. Perú incluye límites departamentales; los otros países muestran su contorno nacional. El exterior del país seleccionado se oculta sobre blanco.
- Periodos Hoy, Últimos 7 días y Este mes, con conteos por territorio calculados sobre los mismos registros mostrados en el mapa.
- Ventana de observación y panel de detalle con metadatos por instrumento. La leyenda representa rangos visuales de FRP en MW, no gravedad ni área quemada.
- Calendario seleccionable y gráfico histórico por día o mes, con filtro departamental y tabla accesible.
- Búsqueda externa de noticias por zona, sin atribuir artículos no verificados a una detección.

La demostración está anclada al **13 de noviembre de 2026 (UTC)** y reúne 91 observaciones sintéticas, 56 en Perú. La etiqueta Hoy se refiere a esa fecha de demostración. Los días o países sin registros de ejemplo no implican ausencia de incendios.

El pipeline todavía no alimenta la API ni el frontend. Siguen pendientes la ingesta de observaciones reales, la armonización y deduplicación validadas, los indicadores científicos, la vinculación verificada de noticias y las alertas. Los conteos no representan incendios únicos.

## Ejecutar el frontend

Requiere Node.js 22.13 o superior en la rama 22, o una versión LTS posterior compatible con las dependencias.

```powershell
cd frontend
npm ci
npm run dev
```

Abra la dirección indicada por Vite. Para comprobar el frontend antes de hacer push:

```powershell
npm test
npm run build
```

La cartografía administrativa se incluye localmente. Las imágenes satelitales de Esri, las fuentes tipográficas y los glifos del mapa requieren conexión. Si las imágenes fallan, se conserva una base cartográfica alternativa con límites y puntos. Consulte [fuentes y limitaciones](docs/fuentes-limitaciones.md) y [arquitectura](docs/arquitectura.md).
