<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { apiUrl } from '../api'
import { tr, language } from '../language'

function getLandCoverMeta(type: string | null | undefined, locale = language.value) {
  return getLandCoverMetaForLanguage(type, locale)
}

function updateMapControlLabels() {
  const labels: [string, string][] = [
    ['.maplibregl-canvas', tr('Mapa', 'Map')],
    ['.maplibregl-ctrl-zoom-in', tr('Acercar', 'Zoom in')],
    ['.maplibregl-ctrl-zoom-out', tr('Alejar', 'Zoom out')],
    ['.maplibregl-ctrl-compass', tr('Arrastra para girar el mapa; haz clic para volver al norte', 'Drag to rotate map, click to reset north')],
    ['.maplibregl-ctrl-attrib-button', tr('Mostrar u ocultar atribuciones', 'Toggle attribution')],
  ]
  for (const [selector, label] of labels) {
    const control = element.value?.querySelector<HTMLElement>(selector)
    if (!control) continue
    control.setAttribute('aria-label', label)
    if (selector !== '.maplibregl-canvas') control.setAttribute('title', label)
  }
}
watch(language, updateMapControlLabels)
import * as maplibregl from 'maplibre-gl'
import type { GeoJSONSource } from 'maplibre-gl'
import mapWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import { MapPin, RotateCcw, X, Download, FileJson } from '@lucide/vue'
import { percent, type Analysis } from '../huanuco'
import {
  loadMapBiomasMask,
  classifyPoint,
  getLandCoverMeta as getLandCoverMetaForLanguage,
  type LandCoverType,
} from '../utils/mapbiomasClassifier'

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
  land_cover?: LandCoverType
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
const landCoverFilter = ref<string>('all')
const mode = ref<'observations' | 'harmonized'>('observations')
const weekStart = ref('')

// MapBiomas visual layer states (overlay over satellite)
const showForestLayer = ref(false)
const showAgriLayer = ref(false)
const showMixedLayer = ref(false)

const HUANUCO_MB_COORDS: [[number, number], [number, number], [number, number], [number, number]] = [
  [-77.32203892294574, -8.313907954526185],
  [-74.51929523649284, -8.313907954526185],
  [-74.51929523649284, -10.483326896373557],
  [-77.32203892294574, -10.483326896373557],
]

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

let districtPolygonsGeo: any = null
let districtLabelsGeo: any = null

function pointInPolygon(pt: [number, number], vs: number[][]): boolean {
  const [x, y] = pt
  let inside = false
  for (let i = 0, j = vs.length - 1; i < vs.length; j = i++) {
    const [xi, yi] = vs[i]
    const [xj, yj] = vs[j]
    const intersect = ((yi > y) !== (yj > y)) && (x < ((xj - xi) * (y - yi)) / (yj - yi) + xi)
    if (intersect) inside = !inside
  }
  return inside
}

function getExactDistrictName(lon: number, lat: number): string | null {
  if (districtPolygonsGeo?.features) {
    for (const f of districtPolygonsGeo.features) {
      const geom = f.geometry
      if (geom.type === 'Polygon') {
        if (pointInPolygon([lon, lat], geom.coordinates[0])) {
          return f.properties.nombre
        }
      } else if (geom.type === 'MultiPolygon') {
        for (const poly of geom.coordinates) {
          if (pointInPolygon([lon, lat], poly[0])) {
            return f.properties.nombre
          }
        }
      }
    }
  }

  // Fallback al centroide más cercano en bordes
  if (!districtLabelsGeo?.features) return null
  let closest: string | null = null
  let minDist = Infinity
  for (const f of districtLabelsGeo.features) {
    const [dlon, dlat] = f.geometry.coordinates
    const dist = (lon - dlon) ** 2 + (lat - dlat) ** 2
    if (dist < minDist) {
      minDist = dist
      closest = f.properties.nombre
    }
  }
  return closest
}

const selectedDistrictName = computed(() => {
  if (!selected.value || props.departmentCode !== 'PE-HUC') return null
  return getExactDistrictName(selected.value.longitude, selected.value.latitude)
})

const landCoverCounts = computed(() => {
  let forest = 0
  let agriculture = 0
  let mixed = 0
  let other = 0
  for (const d of data.value) {
    if (d.land_cover === 'forest') forest++
    else if (d.land_cover === 'agriculture') agriculture++
    else if (d.land_cover === 'mixed') mixed++
    else other++
  }
  return { forest, agriculture, mixed, other }
})

const displayedObservations = computed(() => {
  if (props.departmentCode !== 'PE-HUC' || landCoverFilter.value === 'all') {
    return data.value
  }
  return data.value.filter((d) => d.land_cover === landCoverFilter.value)
})

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
    features: displayedObservations.value.map((d, i) => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [d.longitude, d.latitude] },
      properties: {
        index: i,
        sensor: d.sensor,
        frp: d.frp,
        land_cover: d.land_cover ?? 'other',
      },
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

watch(landCoverFilter, () => {
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

      const response = await fetch(apiUrl(endpoint), { signal: active.signal })
      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(language.value === 'en' ? 'Could not load observations.' : body.detail || 'No se pudieron consultar las observaciones.')
      }
      const result = await response.json()
      if (active.signal.aborted) return

      const rawPoints: Observation[] = result.data || []

      // In Huánuco, classify points with MapBiomas Peru Col. 4 mask
      if (props.departmentCode === 'PE-HUC') {
        await loadMapBiomasMask()
        rawPoints.forEach((d) => {
          d.land_cover = classifyPoint(d.longitude, d.latitude)
        })
      }

      data.value = rawPoints
      total.value = result.total ?? rawPoints.length
      truncated.value = result.truncated ?? false
      draw()
    } catch (e) {
      if (!active.signal.aborted) error.value = e instanceof Error ? e.message : tr('Error de conexión.', 'Connection error.')
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

function registerDistrictLayers() {
  if (!map) return

  if (!map.getSource('districts')) {
    map.addSource('districts', {
      type: 'geojson',
      data: '/geo/huanuco/distritos.geojson',
    })
    map.addLayer(
      {
        id: 'district-lines',
        type: 'line',
        source: 'districts',
        paint: {
          'line-color': '#ffffff',
          'line-width': ['interpolate', ['linear'], ['zoom'], 6, 0.6, 10, 1.2],
          'line-opacity': 0.55,
        },
      },
      map.getLayer('border') ? 'border' : undefined
    )
  }

  if (!map.getSource('district-names')) {
    map.addSource('district-names', {
      type: 'geojson',
      data: '/geo/huanuco/distritos-labels.geojson',
    })
    map.addLayer(
      {
        id: 'district-labels',
        type: 'symbol',
        source: 'district-names',
        minzoom: 6.8,
        layout: {
          'text-field': ['get', 'nombre'],
          'text-font': ['Open Sans Semibold'],
          'text-size': ['interpolate', ['linear'], ['zoom'], 6.8, 9, 10, 13],
          'text-max-width': 8,
          'text-padding': 6,
          'text-allow-overlap': false,
        },
        paint: {
          'text-color': '#ffffff',
          'text-halo-color': '#0f172a',
          'text-halo-width': 2,
        },
      },
      map.getLayer('points') ? 'points' : undefined
    )
  }
}

function registerMapBiomasLayers() {
  if (!map) return

  if (!map.getSource('mb-forest-source')) {
    map.addSource('mb-forest-source', {
      type: 'image',
      url: '/geo/huanuco/forest.png',
      coordinates: HUANUCO_MB_COORDS,
    })
    map.addLayer(
      {
        id: 'mb-forest-layer',
        type: 'raster',
        source: 'mb-forest-source',
        paint: { 'raster-opacity': 0.65 },
        layout: { visibility: showForestLayer.value && props.departmentCode === 'PE-HUC' ? 'visible' : 'none' },
      },
      map.getLayer('region') ? 'region' : undefined
    )
  }

  if (!map.getSource('mb-agri-source')) {
    map.addSource('mb-agri-source', {
      type: 'image',
      url: '/geo/huanuco/agriculture.png',
      coordinates: HUANUCO_MB_COORDS,
    })
    map.addLayer(
      {
        id: 'mb-agri-layer',
        type: 'raster',
        source: 'mb-agri-source',
        paint: { 'raster-opacity': 0.75 },
        layout: { visibility: showAgriLayer.value && props.departmentCode === 'PE-HUC' ? 'visible' : 'none' },
      },
      map.getLayer('region') ? 'region' : undefined
    )
  }

  if (!map.getSource('mb-mixed-source')) {
    map.addSource('mb-mixed-source', {
      type: 'image',
      url: '/geo/huanuco/mixed.png',
      coordinates: HUANUCO_MB_COORDS,
    })
    map.addLayer(
      {
        id: 'mb-mixed-layer',
        type: 'raster',
        source: 'mb-mixed-source',
        paint: { 'raster-opacity': 0.65 },
        layout: { visibility: showMixedLayer.value && props.departmentCode === 'PE-HUC' ? 'visible' : 'none' },
      },
      map.getLayer('region') ? 'region' : undefined
    )
  }
}

function updateHuanucoLayerVisibility() {
  if (!map || !map.isStyleLoaded()) return
  const isHuanuco = props.departmentCode === 'PE-HUC'

  // MapBiomas Layers
  if (map.getLayer('mb-forest-layer')) {
    map.setLayoutProperty('mb-forest-layer', 'visibility', isHuanuco && showForestLayer.value ? 'visible' : 'none')
  }
  if (map.getLayer('mb-agri-layer')) {
    map.setLayoutProperty('mb-agri-layer', 'visibility', isHuanuco && showAgriLayer.value ? 'visible' : 'none')
  }
  if (map.getLayer('mb-mixed-layer')) {
    map.setLayoutProperty('mb-mixed-layer', 'visibility', isHuanuco && showMixedLayer.value ? 'visible' : 'none')
  }

  // District lines and labels for Huánuco
  if (map.getLayer('district-lines')) {
    map.setLayoutProperty('district-lines', 'visibility', isHuanuco ? 'visible' : 'none')
  }
  if (map.getLayer('district-labels')) {
    map.setLayoutProperty('district-labels', 'visibility', isHuanuco ? 'visible' : 'none')
  }
}

watch([showForestLayer, showAgriLayer, showMixedLayer], () => {
  updateHuanucoLayerVisibility()
})

watch(() => props.departmentCode, (newCode) => {
  if (newCode !== 'PE-HUC') {
    landCoverFilter.value = 'all'
  }
  updateRegionBoundary()
  updateHuanucoLayerVisibility()
})

onMounted(async () => {
  try {
    const [depResp, labelsResp, distResp] = await Promise.all([
      fetch('/geo/peru-departments.geojson'),
      fetch('/geo/huanuco/distritos-labels.geojson').catch(() => null),
      fetch('/geo/huanuco/distritos.geojson').catch(() => null),
    ])

    if (!depResp.ok) throw new Error(tr('No se pudo cargar el límite departamental.', 'Could not load the department boundary.'))
    allDepartmentsGeo = await depResp.json()

    if (labelsResp && labelsResp.ok) {
      districtLabelsGeo = await labelsResp.json()
    }
    if (distResp && distResp.ok) {
      districtPolygonsGeo = await distResp.json()
    }

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
        glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
        sources: {
          imagery: {
            type: 'raster',
            tiles: [
              'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            ],
            tileSize: 256,
            attribution: 'Imagery © Esri',
          },
          places: {
            type: 'raster',
            tiles: [
              'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
            ],
            tileSize: 256,
            attribution: 'Labels © Esri',
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
            id: 'places',
            type: 'raster',
            source: 'places',
            paint: { 'raster-opacity': 0.85 },
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
    updateMapControlLabels()
    map.on('load', () => {
      registerMapBiomasLayers()
      registerDistrictLayers()
      updateHuanucoLayerVisibility()
      draw()
      fitRegion(0)
    })

    resizeObserver = new ResizeObserver(() => map?.resize())
    resizeObserver.observe(element.value)

    map.on('click', 'points', (e) => {
      const idx = Number(e.features?.[0]?.properties?.index)
      selected.value = displayedObservations.value[idx] ?? null
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : tr('No se pudo iniciar el mapa.', 'Could not initialize the map.')
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
  if (!displayedObservations.value.length) return
  const isHuanuco = props.departmentCode === 'PE-HUC'
  const headers = [
    'id',
    'fecha_utc',
    'hora_utc',
    'latitud',
    'longitud',
    'sensor',
    'satelite',
    'confianza',
    'frp_mw',
    'brillo_k',
    'tipo_fuego',
    ...(isHuanuco ? ['cobertura_mapbiomas', 'alerta_territorial', 'distrito_oficial'] : []),
    'departamento',
  ]
  const rows = displayedObservations.value.map((d, i) => [
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
    ...(isHuanuco
      ? [
          d.land_cover ? getLandCoverMeta(d.land_cover, 'es').label : 'Otras coberturas',
          d.land_cover ? getLandCoverMeta(d.land_cover, 'es').badge : 'Sin clasificar',
          getExactDistrictName(d.longitude, d.latitude) ?? 'No determinado',
        ]
      : []),
    props.departmentName,
  ])
  const csvContent =
    'data:text/csv;charset=utf-8,\uFEFF' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
  const encodedUri = encodeURI(csvContent)
  const link = document.createElement('a')
  link.setAttribute('href', encodedUri)
  link.setAttribute('download', `detecciones_${props.departmentCode}_${range.value.start}_${range.value.end}.csv`)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

function downloadGeoJSON() {
  if (!displayedObservations.value.length) return
  const isHuanuco = props.departmentCode === 'PE-HUC'
  const geojson = {
    type: 'FeatureCollection',
    features: displayedObservations.value.map((d) => ({
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
        ...(isHuanuco
          ? {
              land_cover_code: d.land_cover,
              land_cover_label: d.land_cover ? getLandCoverMeta(d.land_cover, 'es').label : undefined,
              territorial_alert: d.land_cover ? getLandCoverMeta(d.land_cover, 'es').badge : undefined,
              district: getExactDistrictName(d.longitude, d.latitude),
            }
          : {}),
        department: props.departmentName,
      },
    })),
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
      <section class="map-stage thematic-stage" :aria-label="`${tr('Mapa de detecciones de', 'Detection map of')} ${departmentName}`">
        <div ref="element" class="map-canvas" :aria-label="tr('Mapa de detecciones satelitales', 'Satellite detection map')" />
        
        <!-- Reset View Button -->
        <button class="reset-map icon-button" :aria-label="tr('Restablecer vista', 'Reset view')" @click="fitRegion()">
          <RotateCcw :size="16" />
        </button>

        <!-- Floating MapBiomas Layer Switcher (Huánuco) -->
        <div v-if="departmentCode === 'PE-HUC' && mode === 'observations'" class="mapbiomas-floating-card">
          <div class="mb-card-header">
            <span class="mb-icon">🌿</span>
            <div class="mb-title-col">
              <strong>{{ tr('Capas MapBiomas 2025', 'MapBiomas 2025 layers') }}</strong>
              <small>{{ tr('Colección', 'Collection') }} 4 · Huánuco (150 m)</small>
            </div>
          </div>
          <div class="mb-card-toggles">
            <label class="mb-toggle-item" :class="{ active: showForestLayer }">
              <input type="checkbox" v-model="showForestLayer" />
              <span class="mb-color-dot" style="background: #298743;" />
              <span class="mb-item-label">🌲 {{ tr('Bosque natural', 'Natural forest') }}</span>
            </label>
            <label class="mb-toggle-item" :class="{ active: showAgriLayer }">
              <input type="checkbox" v-model="showAgriLayer" />
              <span class="mb-color-dot" style="background: #f2cf45;" />
              <span class="mb-item-label">🌾 {{ tr('Agropecuario', 'Agriculture') }}</span>
            </label>
            <label class="mb-toggle-item" :class="{ active: showMixedLayer }">
              <input type="checkbox" v-model="showMixedLayer" />
              <span class="mb-color-dot" style="background: #e7d9b1;" />
              <span class="mb-item-label">🏞️ {{ tr('Mosaico mixto', 'Mixed mosaic') }}</span>
            </label>
          </div>
        </div>

        <!-- Count Banner with Quick CSV/GeoJSON Export -->
        <div v-if="mode === 'observations'" class="map-count-card">
          <span style="background: #ef453e" />
          <div class="count-inner">
            <small>
              {{ tr('Detecciones en', 'Detections in') }} {{ departmentName }}
              <template v-if="departmentCode === 'PE-HUC' && landCoverFilter !== 'all'">
                · {{ getLandCoverMeta(landCoverFilter).label }}
              </template>
            </small>
            <div class="count-row">
              <strong>{{ busy ? '…' : error ? '—' : displayedObservations.length.toLocaleString(language === 'en' ? 'en-US' : 'es-PE') }}</strong>
              <div class="quick-export-actions" v-if="displayedObservations.length > 0">
                <button class="mini-btn" @click="downloadFilteredCSV" :title="tr('Descargar como CSV', 'Download as CSV')">
                  <Download :size="14" /> CSV
                </button>
                <button class="mini-btn" @click="downloadGeoJSON" :title="tr('Descargar como GeoJSON', 'Download as GeoJSON')">
                  <FileJson :size="14" /> GeoJSON
                </button>
              </div>
            </div>
            <small v-if="departmentCode === 'PE-HUC' && landCoverFilter !== 'all'" class="filter-subtext">
              {{ tr('Mostrando', 'Showing') }} {{ displayedObservations.length }} {{ tr('de', 'of') }} {{ total.toLocaleString(language === 'en' ? 'en-US' : 'es-PE') }} {{ tr('detecciones', 'detections') }}
            </small>
            <small v-else-if="truncated">{{ tr('Se muestran las 20.000 más recientes.', 'Showing the 20,000 most recent.') }}</small>
          </div>
        </div>

        <div v-else class="map-count-card">
          <span :style="{ background: indicatorColor }" />
          <div>
            <small>{{ tr('Índice semanal de', 'Weekly index for') }} {{ departmentName }}</small>
            <strong>{{ percent(selectedWeek?.combined ?? null) }}</strong>
          </div>
          <small>{{ selectedWeek ? selectedWeek.start + ' – ' + selectedWeek.end : tr('Semana no disponible', 'Week unavailable') }}</small>
        </div>

        <div v-if="mode === 'observations'" class="thematic-bottom">
          <span>🟡 MODIS (1 km) &nbsp; 🔴 VIIRS Suomi (375 m)</span>
          <span v-if="departmentCode === 'PE-HUC'">{{ tr('Límites distritales y lugares', 'District boundaries and places') }} &nbsp;·&nbsp; MapBiomas 2025</span>
          <span v-else>{{ tr('Lugares y límites territoriales activos · Satélite Esri', 'Places and territorial boundaries · Esri satellite') }}</span>
        </div>
        <div v-else class="thematic-bottom">
          <span>{{ tr('Verde &lt;25% · amarillo 25–74% · naranja 75–89% · rojo ≥90%', 'Green &lt;25% · yellow 25–74% · orange 75–89% · red ≥90%') }}</span>
          <span>{{ tr('Índice departamental experimental armonizado', 'Experimental harmonized departmental index') }}</span>
        </div>
        <p v-if="error && mode === 'observations'" class="tile-notice" role="alert">{{ error }}</p>
      </section>

      <!-- Sidebar -->
      <aside class="detail-panel map-side-panel">
        <div class="map-side-heading">
          <h1>{{ mode === 'observations' ? tr('Detección de incendios y quemas agrícolas', 'Fire and agricultural burning detections') : `${tr('Actividad armonizada en', 'Harmonized activity in')} ${departmentName}` }}</h1>
        </div>

        <div class="view-mode" role="group" :aria-label="tr('Visualización del mapa', 'Map view')">
          <button :class="{ active: mode === 'observations' }" :aria-pressed="mode === 'observations'" @click="mode = 'observations'">
            {{ tr('Detecciones', 'Detections') }}
          </button>
          <button :class="{ active: mode === 'harmonized' }" :aria-pressed="mode === 'harmonized'" @click="mode = 'harmonized'">
            {{ tr('Armonizado', 'Harmonized') }}
          </button>
        </div>

        <div class="map-toolbar huanuco-toolbar">
          <label>
            {{ tr('Año', 'Year') }}
            <select :value="year" @change="emit('update:year', Number(($event.target as HTMLSelectElement).value))">
              <option v-for="y in 27" :key="y" :value="2027 - y">{{ 2027 - y }}</option>
            </select>
          </label>

          <template v-if="mode === 'observations'">
            <label>
              {{ tr('Mes', 'Month') }}
              <select v-model="month">
                <option value="all">{{ tr('Todo el año', 'All year') }}</option>
                <option v-for="(m, i) in months" :key="m" :value="String(i + 1)">{{ language === 'en' ? new Intl.DateTimeFormat('en', { month: 'long', timeZone: 'UTC' }).format(new Date(Date.UTC(2020, i, 1))) : m }}</option>
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
              {{ tr('Confianza', 'Confidence') }}
              <select v-model="confidence">
                <option value="all">{{ tr('Todas', 'All') }}</option>
                <option value="high">{{ tr('Alta por sensor', 'High by sensor') }}</option>
              </select>
            </label>
            <label>
              {{ tr('Tipo NASA', 'NASA type') }}
              <select v-model="fireType">
                <option value="all">{{ tr('Todos', 'All') }}</option>
                <option value="0">{{ tr('Vegetación', 'Vegetation') }}</option>
                <option value="1">{{ tr('Volcán', 'Volcano') }}</option>
                <option value="2">{{ tr('Otra fuente terrestre', 'Other land source') }}</option>
                <option value="3">{{ tr('Fuente marina', 'Offshore source') }}</option>
                <option value="unknown">{{ tr('No informado', 'Not reported') }}</option>
              </select>
            </label>

            <!-- MapBiomas Land Cover Filter (Huánuco) -->
            <label v-if="departmentCode === 'PE-HUC'">
              {{ tr('Cobertura (MapBiomas)', 'Land cover (MapBiomas)') }}
              <select v-model="landCoverFilter">
                <option value="all">{{ tr('Todas', 'All') }} ({{ data.length }})</option>
                <option value="forest">🌲 {{ tr('Bosque Natural', 'Natural forest') }} ({{ landCoverCounts.forest }})</option>
                <option value="agriculture">🌾 {{ tr('Agropecuario', 'Agriculture') }} ({{ landCoverCounts.agriculture }})</option>
                <option value="mixed">🏞️ {{ tr('Mosaico Mixto', 'Mixed mosaic') }} ({{ landCoverCounts.mixed }})</option>
                <option value="other">🍂 {{ tr('Otras', 'Other') }} ({{ landCoverCounts.other }})</option>
              </select>
            </label>

            <span class="toolbar-source"><MapPin :size="15" />{{ range.start }} – {{ range.end }} · UTC</span>
          </template>

          <label v-else>
            {{ tr('Semana', 'Week') }}
            <select v-model="weekStart" :disabled="!weeks.length">
              <option v-if="!weeks.length" value="">{{ tr('Sin datos disponibles', 'No data available') }}</option>
              <option v-for="w in weeks" :key="w.start" :value="w.start">
                {{ tr('Semana', 'Week') }} {{ w.week }} · {{ w.start }} – {{ w.end }}
              </option>
            </select>
          </label>
        </div>

        <div v-if="mode === 'harmonized'" class="detail-body">
          <h3>{{ tr('Resultado semanal experimental', 'Experimental weekly result') }}</h3>
          <p>{{ tr('El color representa un único indicador para todo el departamento; no muestra puntos ni valores por celda.', 'The color represents one indicator for the entire department; it does not show points or values by cell.') }}</p>
          <template v-if="selectedWeek">
            <p>MODIS: {{ selectedWeek.sensors.MODIS.cells ?? '—' }} {{ tr('celdas-día · percentil', 'cell-days · percentile') }} {{ percent(selectedWeek.sensors.MODIS.percentile) }}</p>
            <p>VIIRS Suomi: {{ selectedWeek.sensors.VIIRS.cells ?? '—' }} {{ tr('celdas-día · percentil', 'cell-days · percentile') }} {{ percent(selectedWeek.sensors.VIIRS.percentile) }}</p>
            <p>
              {{ tr('Índice combinado:', 'Combined index:') }} <strong>{{ percent(selectedWeek.combined) }}</strong> · {{ tr('diferencia:', 'difference:') }} {{ percent(selectedWeek.disagreement) }}
            </p>
            <p v-if="selectedWeek.combined === null">
              {{ tr('Sin comparación: semana incompleta, referencia insuficiente o demasiados empates.', 'No comparison: incomplete week, insufficient baseline or too many ties.') }}
            </p>
          </template>
          <p v-else>{{ tr('No hay datos semanales disponibles para este año.', 'No weekly data is available for this year.') }}</p>
          <p class="inline-note">{{ tr('Cuadrícula de 5 km; sin filtros de confianza ni tipo. No representa probabilidad de incendio.', '5 km grid; no confidence or type filters. This is not a fire probability.') }}</p>
        </div>

        <div v-else-if="!selected" class="map-selection-hint">
          <MapPin :size="24" />
          <h3>{{ tr('Explora el mapa', 'Explore the map') }}</h3>
          <p>{{ tr('Selecciona un foco en el visor para consultar su ubicación distrital, coordenadas y cobertura del suelo.', 'Select a hotspot to see its district, coordinates and land cover.') }}</p>
        </div>

        <div v-else class="detail-body">
          <div class="detail-header">
            <h2>{{ tr('Detección', 'Detection') }} {{ selected.sensor }}</h2>
            <button class="icon-button" :aria-label="tr('Cerrar detalle', 'Close details')" @click="selected = null"><X :size="18" /></button>
          </div>

          <!-- MapBiomas Contextual Badge -->
          <div v-if="selected.land_cover && selected.land_cover !== 'outside'" class="landcover-badge-card" :class="selected.land_cover">
            <div class="badge-title">
              <span class="badge-icon">{{ getLandCoverMeta(selected.land_cover).icon }}</span>
              <strong>{{ getLandCoverMeta(selected.land_cover).label }}</strong>
              <span class="badge-pill">{{ getLandCoverMeta(selected.land_cover).badge }}</span>
            </div>
            <p class="badge-desc">{{ getLandCoverMeta(selected.land_cover).description }}</p>
            <div class="badge-footer">
              <span>MapBiomas Perú Col. 4 (2025) · {{ tr('Resolución nativa', 'Native resolution') }} 150 m</span>
            </div>
          </div>

          <dl class="data-list">
            <div v-if="selectedDistrictName && departmentCode === 'PE-HUC'">
              <dt>{{ tr('Distrito oficial (INEI)', 'Official district (INEI)') }}</dt>
              <dd><strong>{{ selectedDistrictName }}</strong></dd>
            </div>
            <div><dt>{{ tr('Fecha y hora UTC', 'UTC date and time') }}</dt><dd>{{ selected.acq_date }} · {{ selected.acq_time.padStart(4, '0') }}</dd></div>
            <div><dt>{{ tr('Coordenadas', 'Coordinates') }}</dt><dd>{{ selected.latitude.toFixed(4) }}, {{ selected.longitude.toFixed(4) }}</dd></div>
            <div><dt>{{ tr('Satélite', 'Satellite') }}</dt><dd>{{ selected.satellite }}</dd></div>
            <div><dt>{{ tr('Confianza', 'Confidence') }}</dt><dd>{{ selected.confidence }}</dd></div>
            <div><dt>{{ tr('Tipo NASA', 'NASA type') }}</dt><dd>{{ selected.fire_type ?? tr('No informado', 'Not reported') }}</dd></div>
            <div v-if="selected.land_cover && departmentCode === 'PE-HUC'">
              <dt>{{ tr('Cobertura MapBiomas', 'MapBiomas land cover') }}</dt>
              <dd>{{ getLandCoverMeta(selected.land_cover).label }}</dd>
            </div>
            <div><dt>{{ tr('Potencia radiativa (FRP)', 'Fire radiative power (FRP)') }}</dt><dd>{{ selected.frp ?? '—' }} MW</dd></div>
            <div><dt>{{ tr('Temperatura de Brillo', 'Brightness temperature') }}</dt><dd>{{ selected.brightness ?? '—' }} K</dd></div>
            <div><dt>{{ tr('Producto', 'Product') }}</dt><dd>{{ selected.version }}</dd></div>
          </dl>
          <p class="inline-note">{{ tr('Una detección es una anomalía térmica puntual registrada en el sobrevuelo satelital.', 'A detection is a localized thermal anomaly recorded during a satellite overpass.') }}</p>
        </div>
      </aside>
    </div>

    <p class="map-source-note">
      {{ mode === 'harmonized' ? `${departmentName} · ${tr('indicador semanal experimental a escala departamental.', 'experimental weekly indicator at departmental scale.')}` : `${departmentName} · ${tr('datos originales NASA FIRMS · Nombres y límites territoriales oficiales.', 'original NASA FIRMS data · Official place names and boundaries.')}` }}
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
.filter-subtext {
  color: #b81d24 !important;
  font-weight: 700 !important;
}

/* Floating MapBiomas Layer Card */
.mapbiomas-floating-card {
  position: absolute;
  top: 18px;
  left: 20px;
  z-index: 5;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.08);
  padding: 10px 12px;
  width: 205px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-family: inherit;
}

.mb-card-header {
  display: flex;
  align-items: center;
  gap: 7px;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 6px;
}

.mb-icon {
  font-size: 15px;
}

.mb-title-col {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}

.mb-title-col strong {
  font-size: 11.5px;
  font-weight: 700;
  color: #1e293b;
}

.mb-title-col small {
  font-size: 9.5px;
  color: #64748b;
}

.mb-card-toggles {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.mb-toggle-item {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 11px;
  color: #334155;
  font-weight: 500;
  cursor: pointer;
  padding: 3px 5px;
  border-radius: 5px;
  transition: background 0.15s ease;
  user-select: none;
}

.mb-toggle-item:hover {
  background: #f8fafc;
}

.mb-toggle-item.active {
  background: #f1f5f9;
  font-weight: 600;
}

.mb-toggle-item input[type="checkbox"] {
  cursor: pointer;
  accent-color: #b81d24;
  margin: 0;
  width: 13px;
  height: 13px;
}

.mb-color-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
  border: 1px solid rgba(0, 0, 0, 0.15);
}

.mb-item-label {
  flex: 1;
}

/* Detail panel Land Cover badge */
.landcover-badge-card {
  margin: 10px 0 14px 0;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
}

.landcover-badge-card.forest {
  border-color: #86efac;
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
}

.landcover-badge-card.agriculture {
  border-color: #fde047;
  background: linear-gradient(135deg, #fefce8 0%, #fef9c3 100%);
}

.landcover-badge-card.mixed {
  border-color: #fed7aa;
  background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
}

.landcover-badge-card.other {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.badge-title {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 5px;
}

.badge-icon {
  font-size: 16px;
}

.badge-title strong {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.badge-pill {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 12px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.landcover-badge-card.forest .badge-pill {
  background: #166534;
  color: #ffffff;
}

.landcover-badge-card.agriculture .badge-pill {
  background: #854d0e;
  color: #ffffff;
}

.landcover-badge-card.mixed .badge-pill {
  background: #9a3412;
  color: #ffffff;
}

.landcover-badge-card.other .badge-pill {
  background: #475569;
  color: #ffffff;
}

.badge-desc {
  font-size: 11.5px;
  line-height: 1.4;
  color: #334155;
  margin: 0 0 6px 0;
}

.badge-footer {
  font-size: 9.5px;
  color: #64748b;
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
