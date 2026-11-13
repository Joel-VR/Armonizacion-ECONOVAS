# Arquitectura

El navegador consume la API FastAPI; en desarrollo Vite redirige `/api` al puerto 8000. El pipeline opera por separado sobre CSV locales, con salida en `data/processed`. La conexión entre salida y API aún no existe. PostgreSQL/PostGIS es opcional y no está configurado.

El frontend utiliza Vue 3 y TypeScript con Vite 6. MapLibre GL JS 6 implementa las proyecciones globo y Mercator sobre una misma superficie. ECharts 6 se carga bajo demanda en el histórico; Tailwind CSS 4 y estilos propios definen la interfaz, y Lucide para Vue aporta iconos. Se retiraron Leaflet y el puente React/Recharts para mantener una sola arquitectura Vue.

`frontend/src/data.ts` contiene únicamente fixtures sintéticos, con una fecha de referencia fija (13 de noviembre de 2026 UTC). El mapa, el calendario y los gráficos consultan esos mismos registros. Los periodos y las estadísticas son filtros locales de demostración; todavía no consumen `/api/fires` ni implementan un contrato de observaciones reales.

Componentes: `MapView.vue` gestiona el mapa y la selección geográfica; `DetailPanel.vue` presenta metadatos y la búsqueda externa de noticias; `CalendarView.vue` agrupa por fecha UTC; `HistoryView.vue` agrega por fecha e instrumento. Los mapas, gráficos y observadores se liberan al desmontar las vistas.

Los GeoJSON locales de geoBoundaries y Natural Earth definen los límites. Turf disuelve los departamentos antes de construir la máscara exterior blanca. Las imágenes Esri se solicitan desde el navegador y conservan su atribución. El worker de MapLibre se empaqueta explícitamente mediante Vite para servirlo tanto en desarrollo como en producción.

El procesamiento histórico y reciente debe mantenerse separado cuando se conecten datos reales, con metadatos de procedencia y versión. No se incluye descarga automática de FIRMS, calibración entre sensores ni claves en el frontend.
