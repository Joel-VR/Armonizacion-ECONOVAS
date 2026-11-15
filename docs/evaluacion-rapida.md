# Evaluación rápida de Huánuco 2026

## Alcance

Evaluar observaciones de MODIS y VIIRS Suomi NPP dentro de Huánuco para 2026. Los originales locales llegan al 13 de noviembre para MODIS y al 1 de noviembre para Suomi. Son fechas extremas de las descargas, no prueba de observabilidad diaria. Los datos recientes NRT son provisionales y los tipos desconocidos quedan pendientes de revisión.

No se llaman incendios confirmados a los puntos, ni se calcula área quemada, causa, emisiones o número de eventos únicos. Tampoco se presenta el promedio de percentiles históricos como una armonización validada. Las rutas antiguas mantienen su carácter experimental; la interfaz rápida consulta solamente `/api/huanuco/screened/*`.

## Referencia territorial

- Fuente: MapBiomas Perú, Colección 4, cobertura anual 2025, exportada desde la plataforma oficial para Huánuco.
- Licencia: CC BY 4.0. Atribución: Proyecto MapBiomas Perú, Colección 4 de la serie anual de mapas de cobertura y uso del suelo, consultada el 14 de noviembre de 2026.
- Exportación original: `data/raw/mapbiomas-huanuco-2025-col4.tif`; recorte al límite de geoBoundaries en `data/processed/huanuco-mapbiomas-2025.tif`.
- El checksum SHA-256 del recorte se registra en `reference_layers`. No se conserva un enlace temporal firmado en el código.
- La clasificación utiliza el valor original en el centro de cada observación. No determina la cobertura de toda la huella MODIS/VIIRS, ni la situación real en 2026. Las mezclas de cobertura y cambios entre años requieren verificación.
- Para el navegador se reproyecta a EPSG:3857 y se simplifica con vecino más próximo a 150 m. Esa representación visual no se utiliza para decidir la clasificación.
- Sin observación cartográfica (código 27 o nodata) se marca como desconocido; no se representa como agua o bosque.

## Reglas v1 y su prioridad

1. `type` original 1, 2 o 3: `excluded`, con motivo. Es una exclusión del objetivo, no una declaración de dato falso.
2. Confianza no interpretable o baja: `review`. Regla inicial: MODIS numérico 30–100; VIIRS categorías n/h. No son probabilidades equivalentes ni umbrales validados para Huánuco.
3. Tipo ausente o distinto de 0: `review`, incluidos NRT. Nunca se imputa tipo 0 por defecto.
4. Cobertura distinta de bosque/agropecuario: `review`, no se borra. Agua, urbano, vegetación natural no boscosa y límites de píxel requieren contexto adicional.
5. Tipo 0 + confianza aceptable + centro en bosque/agropecuario: `candidate`. No confirma un incendio ni una quema agrícola.

Se conserva un motivo principal según esta prioridad y la versión de regla. Un cambio de parámetros exige reevaluación y una versión nueva. No se ha descargado ni aplicado la máscara externa STA de FIRMS; afirmar lo contrario sería incorrecto.

Agropecuario agrupa mosaico agropecuario, plantación forestal, palma, arroz y pasto de la leyenda oficial. No equivale a cultivos exclusivamente ni demuestra una quema intencional. Las formaciones naturales herbáceas/arbustivas permanecen en otras coberturas y pueden contener fuegos reales; se consultan en revisión.

## Base y rutas

`reference_layers` es un catálogo de fuentes territoriales. `observation_evaluations` tiene clave compuesta observación/capa/versión y claves foráneas; almacena categoría, código original, decisión, motivo y fecha. No modifica ni duplica físicamente las observaciones NASA. La API selecciona una capa activa explícita, evitando doble conteo cuando existan varias referencias.

- `/api/huanuco/land-cover`: disponibilidad y metadatos.
- `/api/huanuco/screened/analysis?decision=candidate&cover=all&confidence=all`: totales 2026 y distribución diaria UTC. Los totales por estado no se reducen al filtro de cobertura; `total_selected` y `daily` sí.
- `/api/huanuco/screened/points?start=2026-01-01&end=2026-11-13&decision=candidate&cover=all&confidence=all`: máximo 20.000 observaciones, con total real y aviso de truncamiento.

`decision`: candidate/review/excluded. `cover`: all/forest/agriculture/water/urban/other/unknown. `confidence`: all/high; high añade MODIS ≥80 o VIIRS h a la evaluación inicial.

Activar o desactivar una capa del dibujo no filtra observaciones. El selector superior de cobertura filtra mapa, calendario e histórico. El fondo satelital solo se solicita cuando se activa; el mapa predeterminado sirve cinco imágenes locales pequeñas.

## Referencias

- [MapBiomas Perú, leyenda de la Colección 4](https://peru.mapbiomas.org/iniciativas-y-productos/cobertura-y-uso-del-suelo/cobertura/).
- [Plataforma de exportación](https://plataforma.mapbiomas.org/projects/mapbiomas/peru).
- [FIRMS MODIS: atributos y tipos](https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_MODIS_Firehotspots.html).
- [FIRMS VIIRS: atributos y tipos](https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html).

Pendiente de una segunda etapa: verificación independiente con imágenes fechadas/reportes, fuentes estáticas externas, revisión manual persistente, historial de importaciones normalizado, episodios candidatos y su validación, y calibración/armonización científica.
