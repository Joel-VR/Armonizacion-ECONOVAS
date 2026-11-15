<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch, nextTick } from 'vue'
import * as maplibregl from 'maplibre-gl'
import type { GeoJSONSource } from 'maplibre-gl'
import mapWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import { X, RotateCcw, Info, MapPin, ArrowRight, LocateFixed, MessageCircle, Heart, Newspaper } from '@lucide/vue'
import {
  coverLabels,
  type Decision,
  type EvaluatedPoint,
  type LandCover,
  type ScreenedAnalysis,
} from '../huanuco'
import { dateLabel } from '../data'
import { relatedReports, reportKinds } from '../reports'
import type { FeatureCollection } from 'geojson'
const props = defineProps<{
  decision: Decision
  cover: string
  confidence: string
  refresh: number
  analysis: ScreenedAnalysis | null
}>()
maplibregl.setWorkerUrl(mapWorkerUrl)
const selectedMonth = ref('all')
const months = [
  'Enero',
  'Febrero',
  'Marzo',
  'Abril',
  'Mayo',
  'Junio',
  'Julio',
  'Agosto',
  'Septiembre',
  'Octubre',
  'Noviembre',
  'Diciembre',
]
const mapElement = ref<HTMLDivElement>()
const kelvinToCelsius = (value: number | null) => value == null ? 'Sin dato' : `${(value - 273.15).toFixed(1)} °C (conversión aproximada)`
const fireTypeLabel = (value: string | null) => ({ '0': 'Fuego de vegetación', '1': 'Volcán', '2': 'Otra fuente terrestre', '3': 'Fuente marina' }[value ?? ''] || 'Sin clasificación informada')
const eventTitle = (d: EvaluatedPoint) =>
  d.event_type === 'incendio_forestal' ? 'Posible incendio forestal' : d.event_type === 'quema_agricola' ? 'Posible quema agrícola' : 'Posible fuego · causa por revisar'
const eventDetail = ref<{
  detecciones: {
    id: number
    sensor: string
    satellite: string
    acquired_at: string
    confidence: string
    frp: number
    motivo: string
  }[]
} | null>(null)
const detailError = ref('')
const communityAction = ref<'whatsapp' | 'yape' | null>(null)
const failedNewsImages = ref<Record<string, boolean>>({})
const news = computed(() => selected.value ? relatedReports(selected.value) : [])
const data = ref<EvaluatedPoint[]>([]),
  selected = ref<EvaluatedPoint | null>(null),
  hovered = ref<EvaluatedPoint | null>(null)
const error = ref(''),
  busy = ref(false),
  total = ref(0),
  truncated = ref(false),
  ready = ref(false),
  tileError = ref(false)
const landCover = ref<LandCover | null>(null)
const popupPosition = ref({ x: 0, y: 0 })
let map: maplibregl.Map | undefined,
  observer: ResizeObserver | undefined,
  request: AbortController | undefined,
  disposed = false
let bounds: maplibregl.LngLatBounds | undefined
const range = computed(() => {
  if (selectedMonth.value === 'all') return { start: '2026-01-01', end: '2026-12-31' }
  const m = Number(selectedMonth.value)
  const last = new Date(Date.UTC(2026, m, 0)).getUTCDate()
  const prefix = '2026-' + String(m).padStart(2, '0')
  return { start: prefix + '-01', end: prefix + '-' + last }
})
const pointColor = computed(() => '#e13443')
const collection = (): FeatureCollection => ({
  type: 'FeatureCollection',
  features: data.value.map((d) => ({
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [d.longitude, d.latitude] },
    properties: { id: d.id },
  })),
})
function draw() {
  if (!map || !ready.value) return
  ;(map.getSource('detections') as GeoJSONSource).setData(collection())
  map.setPaintProperty('points', 'circle-color', pointColor.value)
}
function fit() {
  if (!map || !bounds) return
  const width = mapElement.value?.clientWidth ?? 900
  map.fitBounds(bounds, {
    padding: {
      top: 40,
      bottom: width > 650 ? 45 : 60,
      left: width > 800 ? 200 : 35,
      right: 50,
    },
    maxZoom: 9,
    duration: 450,
  })
}
function positionPopup() {
  if (!map || !hovered.value) return
  const p = map.project([hovered.value.longitude, hovered.value.latitude])
  const width = mapElement.value?.clientWidth ?? 900
  popupPosition.value = {
    x: Math.max(12, Math.min(width - 300, p.x - 135)),
    y: Math.max(16, Math.min((mapElement.value?.clientHeight ?? 650) - 240, p.y - 205)),
  }
}
function selectPoint(d: EvaluatedPoint) {
  selected.value = d
  hovered.value = null
}
watch(
  () => [
    range.value.start,
    range.value.end,
    props.decision,
    props.cover,
    props.confidence,
    props.refresh,
  ],
  async () => {
    request?.abort()
    const active = new AbortController()
    request = active
    busy.value = true
    error.value = ''
    selected.value = null
    hovered.value = null
    data.value = []
    total.value = 0
    draw()
    try {
      const q = new URLSearchParams({
        ...range.value,
        decision: 'candidate',
        cover: 'all',
        confidence: 'all',
      })
      if (selectedMonth.value !== 'all') q.set('month', selectedMonth.value)
      const r = await fetch('/api/huanuco/events?' + q, { signal: active.signal })
      if (!r.ok) {
        const e = await r.json().catch(() => ({}))
        throw new Error(e.detail || 'No se pudieron consultar las observaciones.')
      }
      const result = await r.json()
      if (active.signal.aborted) return
      data.value = result.data
      total.value = result.total
      truncated.value = result.truncated
      draw()
    } catch (e) {
      if (!active.signal.aborted) error.value = e instanceof Error ? e.message : 'Error de conexión'
    } finally {
      if (!active.signal.aborted) busy.value = false
    }
  },
  { immediate: true },
)
let detailRequest: AbortController | undefined
watch(selected, async (value) => {
  communityAction.value = null
  detailRequest?.abort()
  eventDetail.value = null
  detailError.value = ''
  await nextTick()
  map?.resize()
  if (!value) return
  const active = new AbortController()
  detailRequest = active
  try {
    const response = await fetch('/api/huanuco/events/' + value.id, { signal: active.signal })
    if (!response.ok) throw new Error('No se pudo cargar la evidencia del evento.')
    const body = await response.json()
    if (!active.signal.aborted) eventDetail.value = body
  } catch (e) {
    if (!active.signal.aborted)
      detailError.value = e instanceof Error ? e.message : 'Error de conexión'
  }
})
onMounted(async () => {
  try {
    const [geoResponse, metaResponse] = await Promise.all([
      fetch('/geo/peru-departments.geojson'),
      fetch('/geo/huanuco/metadata.json'),
    ])
    if (!geoResponse.ok || !metaResponse.ok)
      throw new Error('Prepara primero el recorte local de Huánuco.')
    const geo = await geoResponse.json()
    const meta: LandCover = await metaResponse.json()
    if (disposed || !mapElement.value) return
    landCover.value = meta
    const region: FeatureCollection = {
      type: 'FeatureCollection',
      features: geo.features.filter(
        (f: { properties: { shapeISO: string } }) => f.properties.shapeISO === 'PE-HUC',
      ),
    }
    bounds = new maplibregl.LngLatBounds()
    function walk(v: unknown) {
      if (!Array.isArray(v)) return
      if (typeof v[0] === 'number') bounds!.extend([v[0], v[1]])
      else v.forEach(walk)
    }
    region.features.forEach((f) => walk((f.geometry as { coordinates: unknown }).coordinates))
    map = new maplibregl.Map({
      container: mapElement.value,
      center: [-75.9, -9.4],
      zoom: 6,
      attributionControl: false,
      renderWorldCopies: false,
      style: {
        version: 8,
        glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
        sources: {
          region: { type: 'geojson', data: region },
          detections: { type: 'geojson', data: collection() },
        },
        layers: [
          { id: 'background', type: 'background', paint: { 'background-color': '#ffffff' } },
          { id: 'region-base', type: 'fill', source: 'region', paint: { 'fill-color': '#edf0ed' } },
          {
            id: 'border',
            type: 'line',
            source: 'region',
            paint: { 'line-color': '#365d49', 'line-width': 1.5 },
          },
          {
            id: 'point-halo',
            type: 'circle',
            source: 'detections',
            paint: { 'circle-color': '#ffffff', 'circle-radius': 8, 'circle-opacity': 0.45 },
          },
          {
            id: 'points',
            type: 'circle',
            source: 'detections',
            paint: {
              'circle-radius': ['interpolate', ['linear'], ['zoom'], 5, 3.5, 10, 6.5],
              'circle-color': pointColor.value,
              'circle-stroke-color': '#fff',
              'circle-stroke-width': 1.3,
            },
          },
        ],
      },
    })
    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right')
    map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-left')
    map.addControl(new maplibregl.FullscreenControl(), 'top-right')
    map.addControl(
      new maplibregl.AttributionControl({
        compact: true,
        customAttribution: '© MapBiomas Perú · CC BY 4.0 | geoBoundaries',
      }),
      'bottom-right',
    )
    map.on('load', () => {
      if (!map) return
      for (const l of meta.layers) {
        map.addSource('cover-' + l.id, {
          type: 'image',
          url: l.url,
          coordinates: meta.coordinates as [
            [number, number],
            [number, number],
            [number, number],
            [number, number],
          ],
        })
        map.addLayer(
          {
            id: 'cover-' + l.id,
            type: 'raster',
            source: 'cover-' + l.id,
            paint: { 'raster-resampling': 'nearest', 'raster-fade-duration': 0, 'raster-opacity': 0.68, 'raster-saturation': -0.2 },
          },
          'border',
        )
      }
      map.addSource('districts', { type: 'geojson', data: '/geo/huanuco/distritos.geojson' })
      map.addSource('district-names', { type: 'geojson', data: '/geo/huanuco/distritos-labels.geojson' })
      map.addLayer({ id: 'district-lines', type: 'line', source: 'districts', paint: { 'line-color': '#202521', 'line-width': ['interpolate',['linear'],['zoom'],6,0.45,10,1.1], 'line-opacity': 0.65 } }, 'point-halo')
      map.addLayer({ id: 'district-labels', type: 'symbol', source: 'district-names', minzoom: 6,
        layout: { 'text-field': ['get','nombre'], 'text-font': ['Open Sans Semibold'], 'text-size': ['interpolate',['linear'],['zoom'],6,10,10,14], 'text-max-width': 8, 'text-padding': 8 },
        paint: { 'text-color': '#171c19', 'text-halo-color': '#ffffff', 'text-halo-width': 1.5 } })
      ready.value = true
      draw()
      fit()
    })
    map.on('mousemove', 'points', (e) => {
      const id = Number(e.features?.[0]?.properties?.id)
      hovered.value = data.value.find((d) => d.id === id) ?? null
      positionPopup()
    })
    map.on('mouseenter', 'points', () => {
      if (map) map.getCanvas().style.cursor = 'pointer'
    })
    map.on('mouseleave', 'points', () => {
      if (map) map.getCanvas().style.cursor = ''
    })
    map.on('click', 'points', (e) => {
      const d = data.value.find((d) => d.id === Number(e.features?.[0]?.properties?.id))
      if (d) selectPoint(d)
    })
    map.on('click', (e) => {
      if (!map?.queryRenderedFeatures(e.point, { layers: ['points'] }).length) hovered.value = null
    })
    map.on('move', () => {
      if (hovered.value) positionPopup()
    })
    map.on('error', () => {
      tileError.value = true
    })
    observer = new ResizeObserver(() => {
      map?.resize()
      positionPopup()
    })
    observer.observe(mapElement.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo iniciar el mapa.'
  }
})
onUnmounted(() => {
  disposed = true
  request?.abort()
  detailRequest?.abort()
  observer?.disconnect()
  map?.remove()
})
</script>
<template>
  <div class="map-panel">
    <div class="map-workspace with-detail right-filter-layout">
      <section class="map-stage thematic-stage" aria-label="Mapa temático de Huánuco">
        <div ref="mapElement" class="map-canvas" aria-label="Huánuco y sus coberturas del suelo" />
        <div class="compact-map-legend" aria-label="Leyenda del mapa"><strong>Territorio de Huánuco</strong><span v-for="l in landCover?.layers ?? []" :key="l.id"><i :style="{background:l.color}" />{{ l.id === 'forest' ? 'Área de bosque' : l.id === 'agriculture' ? 'Área agrícola' : l.id === 'urban' ? 'Área urbana' : l.id === 'mixed' ? 'Mosaico de usos' : l.label }}</span><small>Colores de referencia · {{ landCover?.year }}</small></div>
        <button
          class="reset-map icon-button"
          aria-label="Restablecer vista de Huánuco"
          @click="fit"
        >
          <RotateCcw :size="16" />
        </button>
        <div class="map-count-card">
          <span :style="{ background: pointColor }" />
          <div>
            <small>Eventos probables</small><strong>{{
              busy ? '…' : error ? '—' : total.toLocaleString('es-PE')
            }}</strong>
          </div>
          <small v-if="truncated"
            >Solo {{ data.length.toLocaleString('es-PE') }} más recientes</small
          >
        </div>
        <div
          v-if="hovered"
          class="observation-popup"
          :style="{ left: popupPosition.x + 'px', top: popupPosition.y + 'px' }"
        >
          <span class="eyebrow">EVENTO · {{ hovered.observation_count }} DETECCIONES</span>
          <h3 class="popup-district">{{ hovered.district || hovered.department }}</h3>
          <p>
            {{ hovered.province || hovered.department }}, Huánuco, Perú · {{ dateLabel(hovered.acquired_at) }}
          </p>
          <dl>
            <div>
              <dt>Estado</dt>
              <dd>{{ eventTitle(hovered) }}</dd>
            </div>
            <div>
              <dt>Ubicación</dt>
              <dd>{{ hovered.department }}, Perú</dd>
            </div>
            <div>
              <dt>Detecciones agrupadas</dt>
              <dd>{{ hovered.observation_count }}</dd>
            </div>
          </dl>
          <button @click="selectPoint(hovered)">
            Consultar evidencia y motivos<ArrowRight :size="15" />
          </button>
        </div>
        <div class="thematic-bottom">
          <span
            ><i :style="{ background: pointColor }" />Eventos probables · No son
            incendios confirmados</span
          ><button v-if="data.length" @click="selectPoint(data[0])">
            <LocateFixed :size="14" />Explorar evento</button
          ><span v-else-if="!busy && !error"
            >Sin detecciones que cumplan los criterios en este periodo.</span
          >
        </div>
        <p v-if="error" class="tile-notice" role="alert">{{ error }}</p>
        <p v-else-if="tileError" class="tile-notice">
          Alguna capa no se pudo cargar; prueba actualizar la vista.
        </p>
      </section>
      <aside
        class="detail-panel map-side-panel"
        aria-label="Filtros y detalle del mapa"
        @keydown.esc="selected = null"
      >
        <div class="map-side-heading"><h1>Detección de incendios forestales y quemas agrícolas</h1></div>
    <div class="map-toolbar huanuco-toolbar">
      <label
        >Año<select aria-label="Año">
          <option disabled>2024 · Sin datos habilitados</option>
          <option disabled>2025 · Sin datos habilitados</option>
          <option selected>2026</option>
          <option disabled>2027 · No disponible</option>
        </select></label
      >
      <label
        >Mes<select v-model="selectedMonth" aria-label="Mes">
          <option value="all">Todo el año</option>
          <option
            v-for="(month, i) in months"
            :key="month"
            :value="String(i + 1)"
            :disabled="i === 11"
          >
            {{ month }}{{ i === 11 ? ' · Sin datos todavía' : '' }}
          </option>
        </select></label
      ><span class="toolbar-source"
        ><MapPin :size="15" />{{ range.start }} a {{ range.end }} · UTC</span
      >
    </div>
        <div v-if="!selected" class="map-selection-hint"><MapPin :size="24" /><h3>Explora el mapa</h3><p>Selecciona un punto para consultar su ubicación, las detecciones y los reportes relacionados.</p></div>
        <template v-if="selected">
        <div class="detail-header">
          <div>
            <span class="eyebrow">HUÁNUCO · EVENTO AGRUPADO</span>
            <h2 id="selected-observation">{{ selected.event_type === 'incendio_forestal' ? 'Detalles del posible incendio forestal' : selected.event_type === 'quema_agricola' ? 'Detalles de la posible quema agrícola' : 'Detalles del posible fuego' }}</h2>
            <p>{{ selected.department }}, Perú</p>
          </div>
          <button class="icon-button" aria-label="Cerrar detalle" @click="selected = null">
            <X :size="18" />
          </button>
        </div>
        <div class="detail-body">
          <section class="event-location-card">
            <h3>Ubicación del evento</h3>
            <p class="event-location-name">{{ selected.district || 'Ubicación geográfica' }}</p>
            <p>{{ selected.province ? selected.province + ', ' : '' }}{{ selected.department }}, Perú</p>
            <p class="event-coordinate">{{ selected.latitude.toFixed(4) }}, {{ selected.longitude.toFixed(4) }}</p>
          </section>
          <section>
            <h3>Periodo observado</h3>
            <p>{{ dateLabel(selected.acquired_at) }} — {{ dateLabel(selected.ultima_deteccion) }}</p>
            <p>{{ selected.observation_count }} detecciones satelitales agrupadas. El área afectada no se calcula con estos puntos.</p>
          </section>
          <section>
            <h3>Por qué aparece aquí</h3>
            <p class="evaluation-reason">{{ selected.reason }}</p>
          </section>
          <details class="biome-context"><summary>Referencia territorial utilizada</summary>

            <p><strong>Tipo de cobertura:</strong> {{ coverLabels[selected.cover_category] }} según MapBiomas {{ landCover?.year }}.</p>
            <p class="inline-note"><Info :size="15" />Es la cobertura registrada en el píxel y año de referencia; no identifica la causa ni demuestra pérdida de bosque.</p>
          </details>
          <section class="reference-news">
            <h3 class="news-heading"><Newspaper :size="21" /> Noticias y reportes</h3>
            <p>Referencias documentadas para contrastar la ubicación y la fecha. No confirman automáticamente este evento satelital.</p>
            <a v-for="report in news" :key="report.url" :href="report.url" target="_blank" rel="noopener noreferrer" class="report-card" :class="'report-' + report.kind">
              <img v-if="report.image && !failedNewsImages[report.url]" :src="report.image" :alt="report.title" class="report-image" loading="lazy" referrerpolicy="no-referrer" @error="failedNewsImages[report.url] = true" />
              <span class="report-kind">{{ reportKinds[report.kind] }}</span>
              <small>{{ report.context }} · {{ report.date }}</small>
              <strong>{{ report.title }} ↗</strong>
              <span>{{ report.source }}</span>
            </a>
            <p class="inline-note"><Info :size="15" />La ausencia de noticias no descarta un incendio. La coincidencia de distrito tampoco basta para confirmarlo.</p>
          </section>
          <section class="community-actions">
            <h3>Comunidad y apoyo</h3>
            <p>Conectemos para cuidar nuestro territorio.</p>
            <button type="button" class="community-whatsapp" @click="communityAction = communityAction === 'whatsapp' ? null : 'whatsapp'" :aria-expanded="communityAction === 'whatsapp'" aria-controls="community-preview"><MessageCircle :size="20" /> Unirme a WhatsApp <ArrowRight :size="16" /></button>
            <button type="button" class="community-yape" @click="communityAction = communityAction === 'yape' ? null : 'yape'" :aria-expanded="communityAction === 'yape'" aria-controls="community-preview"><Heart :size="20" /> Donar con Yape <ArrowRight :size="16" /></button>
            <div v-if="communityAction" id="community-preview" class="community-preview" role="status">
              <strong v-if="communityAction === 'whatsapp'">Comunidad T'UKRI</strong><strong v-else>Apoya con Yape</strong>
              <p>{{ communityAction === 'whatsapp' ? 'Vista de demostración. Aún no hay un enlace de invitación configurado.' : 'Vista de demostración. No se realizan cobros ni hay una cuenta receptora configurada.' }}</p>
              <button type="button" @click="communityAction = null">Cerrar</button>
            </div>
            <small>Demostración · Sin invitaciones ni pagos activos.</small>
          </section>
          <details class="technical-evidence">
            <summary>Datos satelitales y explicación sencilla</summary>
            <p>Los satélites observan calor en la superficie. Esto sirve como señal para revisar, pero también puede tener otras causas.</p>
            <dl class="data-list">
              <div><dt>Sensor y satélite</dt><dd>{{ selected.sensor }} · {{ selected.satellite }}</dd></div>
              <div><dt>Confianza informada por NASA</dt><dd>{{ selected.confidence }} · calidad de detección, no probabilidad de incendio</dd></div>
              <div><dt>Potencia del foco de calor</dt><dd>{{ selected.frp ?? '—' }} MW · energía radiada estimada, no temperatura</dd></div>
              <div><dt>Temperatura de brillo</dt><dd>{{ kelvinToCelsius(selected.brightness) }}</dd></div>
              <div><dt>Tipo informado por NASA</dt><dd>{{ fireTypeLabel(selected.fire_type) }}</dd></div>
              <div><dt>Tamaño aproximado del píxel observado</dt><dd>{{ selected.scan ?? '—' }} × {{ selected.track ?? '—' }} km; no es el tamaño del fuego</dd></div>
              <div><dt>Momento</dt><dd>{{ selected.daynight === 'D' ? 'Día' : 'Noche' }}</dd></div>
              <div><dt>Producto de origen</dt><dd>{{ selected.version }} · {{ selected.source_kind }}</dd></div>
              <div><dt>Código de cobertura</dt><dd>{{ selected.cover_code }} · regla {{ selected.rule_version }}</dd></div>
            </dl>
            <p class="inline-note"><Info :size="15" />La temperatura de brillo es una medición del sensor y no equivale a la temperatura exacta de las llamas.</p>
          </details>
          <section v-if="detailError" class="event-detections"><p role="alert">{{ detailError }}</p></section>
          <section v-else-if="eventDetail" class="event-detections">
            <h3>Observaciones que forman el grupo</h3>
            <p v-for="d in eventDetail.detecciones" :key="d.id">{{ d.sensor }} ({{ d.satellite }}) · {{ dateLabel(d.acquired_at) }} · confianza {{ d.confidence }} · foco {{ d.frp ?? '—' }} MW</p>
          </section>
          <p class="fine-print">
            La máscara externa STA de FIRMS aún no está integrada. Este filtro utiliza el tipo
            original NASA, la confianza y MapBiomas. No confirma eventos ni superficie quemada.
          </p>
        </div>
        </template>
      </aside>
    </div>
    <p class="map-source-note">
      Solo Huánuco · Un punto por agrupación probable · Filtro territorial sobre el raster original
      · MODIS hasta {{ analysis?.ends.MODIS ?? '—' }}, Suomi hasta
      {{ analysis?.ends.VIIRS ?? '—' }}.
    </p>
  </div>
</template>
