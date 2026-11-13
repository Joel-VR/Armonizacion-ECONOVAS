# Fuentes y limitaciones

- [NASA FIRMS: API de área](https://firms.modaps.eosdis.nasa.gov/api/area/).
- [FIRMS: datos de incendios activos](https://firms.modaps.eosdis.nasa.gov/active_fire/).
- [FIRMS: descarga histórica](https://firms.modaps.eosdis.nasa.gov/download/).

Consulte la documentación del producto y sus condiciones antes de descargar o reutilizar datos. La API puede requerir MAP_KEY y tiene restricciones de cobertura y uso. Las detecciones son anomalías térmicas, no confirmaciones de incendios forestales; existen omisiones y falsas detecciones y la cobertura varía según sensor, nubes, horario y producto. La ausencia de datos cargados no demuestra ausencia de detecciones. Los históricos y los datos recientes pueden diferir en latencia y procesamiento. No hay validación de campo ni cifras reales incluidas.

## Cartografía y presentación

- Departamentos de Perú: [geoBoundaries gbOpen PER ADM1](https://www.geoboundaries.org/api/current/gbOpen/PER/ADM1/), versión `PER-ADM1-1875124`, geometría simplificada del commit `90a1d52`. El proveedor declara dominio público y fuente Wikimedia Commons. Contiene 26 unidades administrativas porque distingue Lima Metropolitana y la región Lima; no se utiliza este número como cantidad de departamentos monitoreados.
- Países: [Natural Earth, Admin 0, escala 1:110m](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson), [dominio público](https://www.naturalearthdata.com/about/terms-of-use/). Se conservaron geometrías y nombres para la interfaz. Los límites son aproximados y no expresan una posición sobre territorios disputados.
- Fondo satelital: [Esri World Imagery](https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer), servido externamente con atribución visible. Los límites y ejemplos están disponibles localmente; la imagen, las fuentes de Google Fonts y los glifos de MapLibre requieren red.
- Logo del conejo bombero: imagen proporcionada por el usuario, conservada en `frontend/public/brand/brinco-alerta.png`.

## Demostración y lectura de datos

Los puntos, fechas y valores son fixtures sintéticos del frontend y están etiquetados como tales. Los colores usan rangos de FRP menores a 10 MW, de 10 a menos de 30 MW y desde 30 MW, únicamente para mostrar diferencias en el mapa. No son umbrales oficiales de gravedad, riesgo o clasificación de incendios. FRP no equivale al tamaño del incendio ni al área quemada.

Las búsquedas en Google Noticias son enlaces contextuales externos; no hay noticias verificadas asociadas a registros ni artículos inventados. La armonización, clasificación de evento, alertas y conexión operativa con FIRMS siguen pendientes.
