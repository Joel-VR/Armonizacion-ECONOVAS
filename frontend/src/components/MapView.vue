<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import * as maplibregl from 'maplibre-gl'
import type { GeoJSONSource } from 'maplibre-gl'
import mapWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import { MapPin, RotateCcw, X, Download, FileJson } from '@lucide/vue'
import { percent, type Analysis } from '../huanuco'

type Observation = {
  latitude: number
  longitude: number
  acq_date: string
  acq_time: string
  sensor: string
  satellite: string
  confidence: string
  fire_type: string | null
  frp: number | null
  brightness: number | null
  scan: number | null
  track: number | null
  daynight: string
  version: string
}

const props = withDefaults(
  defineProps<{
    refresh: number
    year: number
    analysis: Analysis | null
    departmentCode?: string
    departmentName?: string
    initialMonth?: number | string
  }>(),
  {
    departmentCode: 'PE-HUC',
    departmentName: 'Huánuco',
    initialMonth: 'all'
  }
)

const emit = defineEmits<{
  'update:year': [year: number]
}>()

maplibregl.setWorkerUrl(mapWorkerUrl)

const element = ref<HTMLDivElement>()
const month = ref(String(props.initialMonth))
const sensor = ref('all')
const confidence = ref('all')
const fireType = ref('all')
const mode = ref<'observations' | 'harmonized'>('observations')
const weekStart = ref('')

watch(() => props.initialMonth, (val) => {
  if (val) month.value = String(val)
})

const weeks = computed(() => (props.analysis?.year === props.year ? props.analysis.weekly : []))
const selectedWeek = computed(() => weeks.value.find((w) => w.start === weekStart.value))

watch(
  weeks,
  (items) => {
    weekStart.value = items.find((w) => w.combined !== null)?.start ?? items[0]?.start ?? ''
  },
  { immediate: true }
)

const indicatorColor = computed(() => {
  const n = selectedWeek.value?.combined
  return n == null ? '#9ca3a1' : n < 0.25 ? '#4c9f69' : n < 0.75 ? '#efcc51' : n < 0.9 ? '#ee963d' : '#d84442'
})

const data = ref<Observation[]>([])
const selected = ref<Observation | null>(null)
const busy = ref(false)
const error = ref('')
const total = ref(0)
const truncated = ref(false)

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

let map: maplibregl.Map | undefined
let controller: AbortController | undefined
let resizeObserver: ResizeObserver | undefined
let regionBounds: maplibregl.LngLatBounds | undefined
let allDepartmentsGeo: any = null

const range = computed(() => {
  if (month.value === 'all') return { start: props.year + '-01-01', end: props.year + '-12-31' }
  const n = Number(month.value),
    prefix = props.year + '-' + String(n).padStart(2, '0')
  return { start: prefix + '-01', end: prefix + '-' + new Date(Date.UTC(props.year, n, 0)).getUTCDate() }
})

function draw() {
  const source = map?.getSource('detections') as GeoJSONSource | undefined
  source?.setData({
    type: 'FeatureCollection',
    features: data.value.map((d, i) => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [d.longitude, d.latitude] },
      properties: { index: i, sensor: d.sensor, frp: d.frp },
    })),
  })
  if (map?.getLayer('region') && map.getLayer('points')) {
    map.setPaintProperty('region', 'fill-color', mode.value === 'harmonized' ? indicatorColor.value : '#c3e9c1')
    map.setPaintProperty('region', 'fill-opacity', mode.value === 'harmonized' ? 0.7 : 0.12)
    map.setLayoutProperty('points', 'visibility', mode.value === 'harmonized' ? 'none' : 'visible')
  }
}

watch([mode, indicatorColor], () => {
  selected.value = null
  draw()
})

watch(
  [range, sensor, confidence, fireType, mode, () => props.refresh, () => props.departmentCode],
  async () => {
    controller?.abort()
    const active = new AbortController()
    controller = active
    busy.value = true
    error.value = ''
    selected.value = null
    data.value = []
    draw()

    if (mode.value === 'harmonized') {
      busy.value = false
      return
    }

    try {
      const q = new URLSearchParams({
        ...range.value,
        sensor: sensor.value,
        confidence: confidence.value,
        fire_type: fireType.value,
      })

      // Query departmental endpoint
      const endpoint = props.departmentCode === 'PE-HUC'
        ? '/api/huanuco/observations?' + q
        : `/api/departments/${props.departmentCode}/points?${q}`

      const response = await fetch(endpoint, { signal: active.signal })
      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(body.detail || 'No se pudieron consultar las observaciones.')
      }
      const result = await response.json()
      if (active.signal.aborted) return
      data.value = result.data || []
      total.value = result.total ?? result.data?.length ?? 0
      truncated.value = result.truncated ?? false
      draw()
    } catch (e) {
      if (!active.signal.aborted) error.value = e instanceof Error ? e.message : 'Error de conexión.'
    } finally {
      if (!active.signal.aborted) busy.value = false
    }
  },
  { immediate: true }
)

function updateRegionBoundary() {
  if (!allDepartmentsGeo || !map) return
  const code = props.departmentCode
  const filtered = allDepartmentsGeo.features.filter(
    (f: { properties: { shapeISO: string } }) => f.properties.shapeISO === code
  )
  if (!filtered.length) return
  const region = { type: 'FeatureCollection', features: filtered }

  regionBounds = new maplibregl.LngLatBounds()
  function includeCoordinates(value: unknown): void {
    if (!Array.isArray(value)) return
    if (typeof value[0] === 'number' && typeof value[1] === 'number') regionBounds?.extend([value[0], value[1]])
    else value.forEach(includeCoordinates)
  }
  region.features.forEach((feature: { geometry: { coordinates: unknown } }) =>
    includeCoordinates(feature.geometry.coordinates)
  )

  const regionSource = map.getSource('region') as GeoJSONSource | undefined
  regionSource?.setData(region as any)
  fitRegion(500)
}

watch(() => props.departmentCode, () => {
  updateRegionBoundary()
})

onMounted(async () => {
  try {
    const response = await fetch('/geo/peru-departments.geojson')
    if (!response.ok) throw new Error('No se pudo cargar el límite departamental.')
    allDepartmentsGeo = await response.json()

    const code = props.departmentCode
    const region = {
      type: 'FeatureCollection',
      features: allDepartmentsGeo.features.filter(
        (f: { properties: { shapeISO: string } }) => f.properties.shapeISO === code
      ),
    }
    regionBounds = new maplibregl.LngLatBounds()
    function includeCoordinates(value: unknown): void {
      if (!Array.isArray(value)) return
      if (typeof value[0] === 'number' && typeof value[1] === 'number') regionBounds?.extend([value[0], value[1]])
      else value.forEach(includeCoordinates)
    }
    region.features.forEach((feature: { geometry: { coordinates: unknown } }) =>
      includeCoordinates(feature.geometry.coordinates)
    )

    if (!element.value) return
    map = new maplibregl.Map({
      container: element.value,
      center: [-75.9, -9.4],
      zoom: 6,
      style: {
        version: 8,
        sources: {
          imagery: {
            type: 'raster',
            tiles: [
              'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            ],
            tileSize: 256,
            attribution: 'Imagery © Esri',
          },
          region: { type: 'geojson', data: region },
          detections: { type: 'geojson', data: { type: 'FeatureCollection', features: [] } },
        },
        layers: [
          { id: 'imagery', type: 'raster', source: 'imagery' },
          {
            id: 'region',
            type: 'fill',
            source: 'region',
            paint: { 'fill-color': '#c3e9c1', 'fill-opacity': 0.12 },
          },
          {
            id: 'border',
            type: 'line',
            source: 'region',
            paint: { 'line-color': '#ffffff', 'line-width': 2 },
          },
          {
            id: 'points',
            type: 'circle',
            source: 'detections',
            paint: {
              'circle-radius': 4.5,
              'circle-color': ['match', ['get', 'sensor'], 'MODIS', '#ffd65a', '#ef453e'],
              'circle-stroke-color': '#ffffff',
              'circle-stroke-width': 1,
            },
          },
        ],
      },
    })

    map.addControl(new maplibregl.NavigationControl(), 'top-right')
    map.on('load', () => {
      draw()
      fitRegion(0)
    })

    resizeObserver = new ResizeObserver(() => map?.resize())
    resizeObserver.observe(element.value)

    map.on('click', 'points', (e) => {
      selected.value = data.value[Number(e.features?.[0]?.properties?.index)] ?? null
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo iniciar el mapa.'
  }
})

onUnmounted(() => {
  controller?.abort()
  resizeObserver?.disconnect()
  map?.remove()
})

function fitRegion(duration = 450) {
  if (regionBounds && !regionBounds.isEmpty()) map?.fitBounds(regionBounds, { padding: 50, maxZoom: 9, duration })
}

function downloadFilteredCSV() {
  if (!data.value.length) return
  const headers = ['id', 'fecha_utc', 'hora_utc', 'latitud', 'longitud', 'sensor', 'satelite', 'confianza', 'frp_mw', 'brillo_k', 'tipo_fuego', 'departamento']
  const rows = data.value.map((d, i) => [
    i + 1,
    d.acq_date,
    d.acq_time,
    d.latitude,
    d.longitude,
    d.sensor,
    d.satellite,
    d.confidence,
    d.frp ?? '',
    d.brightness ?? '',
    d.fire_type ?? '',
    props.departmentName
  ])
  const csvContent = 'data:text/csv;charset=utf-8,\uFEFF' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
  const encodedUri = encodeURI(csvContent)
  const link = document.createElement('a')
  link.setAttribute('href', encodedUri)
  link.setAttribute('download', `detecciones_${props.departmentCode}_${range.value.start}_${range.value.end}.csv`)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

function downloadGeoJSON() {
  if (!data.value.length) return
  const geojson = {
    type: 'FeatureCollection',
    features: data.value.map((d) => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [d.longitude, d.latitude] },
      properties: {
        date: d.acq_date,
        time: d.acq_time,
        sensor: d.sensor,
        satellite: d.satellite,
        confidence: d.confidence,
        frp: d.frp,
        brightness: d.brightness,
        fire_type: d.fire_type,
        department: props.departmentName
      }
    }))
  }
  const blob = new Blob([JSON.stringify(geojson, null, 2)], { type: 'application/geo+json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `detecciones_${props.departmentCode}_${range.value.start}_${range.value.end}.geojson`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div class="map-panel">
    <div class="map-workspace with-detail right-filter-layout">
      <section class="map-stage thematic-stage" :aria-label="`Mapa de detecciones de ${departmentName}`">
        <div ref="element" class="map-canvas" aria-label="Mapa de detecciones satelitales" />
        <button class="reset-map icon-button" aria-label="Restablecer vista" @click="fitRegion()">
          <RotateCcw :size="16" />
        </button>

        <!-- Count Banner with Quick CSV Export -->
        <div v-if="mode === 'observations'" class="map-count-card">
          <span style="background: #ef453e" />
          <div class="count-inner">
            <small>Detecciones en {{ departmentName }}</small>
            <div class="count-row">
              <strong>{{ busy ? '…' : error ? '—' : total.toLocaleString('es-PE') }}</strong>
              <div class="quick-export-actions" v-if="data.length > 0">
                <button class="mini-btn" @click="downloadFilteredCSV" title="Descargar como CSV">
                  <Download :size="14" /> CSV
                </button>
                <button class="mini-btn" @click="downloadGeoJSON" title="Descargar como GeoJSON">
                  <FileJson :size="14" /> GeoJSON
                </button>
              </div>
            </div>
          </div>
          <small v-if="truncated">Se muestran las 20.000 más recientes.</small>
        </div>

        <div v-else class="map-count-card">
          <span :style="{ background: indicatorColor }" />
          <div>
            <small>Índice semanal de {{ departmentName }}</small>
            <strong>{{ percent(selectedWeek?.combined ?? null) }}</strong>
          </div>
          <small>{{ selectedWeek ? selectedWeek.start + ' a ' + selectedWeek.end : 'Semana no disponible' }}</small>
        </div>

        <div v-if="mode === 'observations'" class="thematic-bottom">
          <span>🟡 MODIS (1 km) &nbsp; 🔴 VIIRS Suomi (375 m)</span>
          <span>Una detección térmica no equivale necesariamente a un incendio forestal.</span>
        </div>
        <div v-else class="thematic-bottom">
          <span>Verde &lt;25% · amarillo 25–74% · naranja 75–89% · rojo ≥90%</span>
          <span>Índice departamental experimental armonizado</span>
        </div>
        <p v-if="error && mode === 'observations'" class="tile-notice" role="alert">{{ error }}</p>
      </section>

      <!-- Sidebar -->
      <aside class="detail-panel map-side-panel">
        <div class="map-side-heading">
          <h1>{{ mode === 'observations' ? `Detecciones en ${departmentName}` : `Actividad armonizada en ${departmentName}` }}</h1>
        </div>

        <div class="view-mode" role="group" aria-label="Visualización del mapa">
          <button :class="{ active: mode === 'observations' }" :aria-pressed="mode === 'observations'" @click="mode = 'observations'">
            Detecciones
          </button>
          <button :class="{ active: mode === 'harmonized' }" :aria-pressed="mode === 'harmonized'" @click="mode = 'harmonized'">
            Armonizado
          </button>
        </div>

        <div class="map-toolbar huanuco-toolbar">
          <label>
            Año
            <select :value="year" @change="emit('update:year', Number(($event.target as HTMLSelectElement).value))">
              <option v-for="y in 27" :key="y" :value="2027 - y">{{ 2027 - y }}</option>
            </select>
          </label>

          <template v-if="mode === 'observations'">
            <label>
              Mes
              <select v-model="month">
                <option value="all">Todo el año</option>
                <option v-for="(m, i) in months" :key="m" :value="String(i + 1)">{{ m }}</option>
              </select>
            </label>
            <label>
              Sensor
              <select v-model="sensor">
                <option value="all">(MODIS + VIIRS)</option>
                <option>MODIS</option>
                <option>VIIRS</option>
              </select>
            </label>
            <label>
              Confianza
              <select v-model="confidence">
                <option value="all">Todas</option>
                <option value="high">Alta por sensor</option>
              </select>
            </label>
            <label>
              Tipo NASA
              <select v-model="fireType">
                <option value="all">Todos</option>
                <option value="0">Vegetación</option>
                <option value="1">Volcán</option>
                <option value="2">Otra fuente terrestre</option>
                <option value="3">Fuente marina</option>
                <option value="unknown">No informado</option>
              </select>
            </label>
            <span class="toolbar-source"><MapPin :size="15" />{{ range.start }} a {{ range.end }} · UTC</span>
          </template>

          <label v-else>
            Semana
            <select v-model="weekStart" :disabled="!weeks.length">
              <option v-if="!weeks.length" value="">Sin datos disponibles</option>
              <option v-for="w in weeks" :key="w.start" :value="w.start">
                Semana {{ w.week }} · {{ w.start }} a {{ w.end }}
              </option>
            </select>
          </label>
        </div>

        <div v-if="mode === 'harmonized'" class="detail-body">
          <h3>Resultado semanal experimental</h3>
          <p>El color representa un único indicador para todo el departamento; no muestra puntos ni valores por celda.</p>
          <template v-if="selectedWeek">
            <p>MODIS: {{ selectedWeek.sensors.MODIS.cells ?? '—' }} celdas-día · percentil {{ percent(selectedWeek.sensors.MODIS.percentile) }}</p>
            <p>VIIRS Suomi: {{ selectedWeek.sensors.VIIRS.cells ?? '—' }} celdas-día · percentil {{ percent(selectedWeek.sensors.VIIRS.percentile) }}</p>
            <p>
              Índice combinado: <strong>{{ percent(selectedWeek.combined) }}</strong> · diferencia: {{ percent(selectedWeek.disagreement) }}
            </p>
            <p v-if="selectedWeek.combined === null">
              Sin comparación: semana incompleta, referencia insuficiente o demasiados empates.
            </p>
          </template>
          <p v-else>No hay datos semanales disponibles para este año.</p>
          <p class="inline-note">Cuadrícula de 5 km; sin filtros de confianza ni tipo. No representa probabilidad de incendio.</p>
        </div>

        <div v-else-if="!selected" class="map-selection-hint">
          <MapPin :size="24" />
          <h3>Explora el mapa</h3>
          <p>Selecciona un foco en el visor para consultar la observación satelital de origen.</p>
        </div>

        <div v-else class="detail-body">
          <div class="detail-header">
            <h2>Detección {{ selected.sensor }}</h2>
            <button class="icon-button" aria-label="Cerrar detalle" @click="selected = null"><X :size="18" /></button>
          </div>
          <dl class="data-list">
            <div><dt>Fecha y hora UTC</dt><dd>{{ selected.acq_date }} · {{ selected.acq_time.padStart(4, '0') }}</dd></div>
            <div><dt>Coordenadas</dt><dd>{{ selected.latitude.toFixed(4) }}, {{ selected.longitude.toFixed(4) }}</dd></div>
            <div><dt>Satélite</dt><dd>{{ selected.satellite }}</dd></div>
            <div><dt>Confianza</dt><dd>{{ selected.confidence }}</dd></div>
            <div><dt>Tipo NASA</dt><dd>{{ selected.fire_type ?? 'No informado' }}</dd></div>
            <div><dt>Potencia radiativa (FRP)</dt><dd>{{ selected.frp ?? '—' }} MW</dd></div>
            <div><dt>Temperatura de Brillo</dt><dd>{{ selected.brightness ?? '—' }} K</dd></div>
            <div><dt>Producto</dt><dd>{{ selected.version }}</dd></div>
          </dl>
          <p class="inline-note">Una detección es una anomalía térmica puntual registrada en el sobrevuelo.</p>
        </div>
      </aside>
    </div>

    <p class="map-source-note">
      {{ mode === 'harmonized' ? `${departmentName} · indicador semanal experimental a escala departamental.` : `${departmentName} · datos originales NASA FIRMS · Sistema Armonizado T'UKRI.` }}
    </p>
  </div>
</template>

<style scoped>
.count-inner {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  width: 100%;
}
.count-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}
.quick-export-actions {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}
.mini-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 0.72rem;
  font-weight: 700;
  color: #334155;
  cursor: pointer;
  transition: all 0.15s ease;
}
.mini-btn:hover {
  background: #e2e8f0;
  border-color: #94a3b8;
}
</style>
