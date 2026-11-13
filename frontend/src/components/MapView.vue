<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as maplibregl from 'maplibre-gl'
import type { GeoJSONSource, Map as MapInstance } from 'maplibre-gl'
import mapWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import union from '@turf/union'
import { featureCollection, polygon } from '@turf/helpers'
import type { FeatureCollection, Feature, Polygon, MultiPolygon, Position } from 'geojson'
import {
  MapPin,
  Globe2,
  Flame,
  Layers,
  RotateCcw,
  Info,
  ArrowRight,
  LocateFixed,
  LoaderCircle,
  AlertTriangle,
  MousePointer2,
  ChevronDown,
} from '@lucide/vue'
import DetailPanel from './DetailPanel.vue'
import {
  detections,
  inPeriod,
  frpColor,
  dateLabel,
  periodLabels,
  type Detection,
  type Period,
  type Scope,
} from '../data'
maplibregl.setWorkerUrl(mapWorkerUrl)
const props = defineProps<{ period: Period }>()
const scope = ref<Scope>('country')
const country = ref('PER')
const countries = ref<{ code: string; name: string }[]>([{ code: 'PER', name: 'Perú' }])
const countryName = computed(
  () => countries.value.find((c) => c.code === country.value)?.name ?? country.value,
)
const container = ref<HTMLDivElement>()
const ready = ref(false)
const error = ref('')
const tileError = ref(false)
const preview = ref<Detection>()
const selected = ref<Detection>()
const popupPosition = ref({ x: 0, y: 0 })
const visible = computed(() =>
  detections.filter(
    (d) => inPeriod(d, props.period) && (scope.value === 'world' || d.country === country.value),
  ),
)
const regionCount = computed(
  () => new Set(visible.value.map((d) => `${d.country}-${d.department}`)).size,
)
const areaCount = computed(() =>
  selected.value
    ? visible.value.filter(
        (d) => d.country === selected.value!.country && d.department === selected.value!.department,
      ).length
    : 0,
)
let map: MapInstance | undefined
let world: FeatureCollection<Polygon | MultiPolygon>
let departments: FeatureCollection<Polygon | MultiPolygon>
let observer: ResizeObserver | undefined
let disposed = false
const collection = () =>
  featureCollection(
    visible.value.map((d) => ({
      type: 'Feature' as const,
      geometry: { type: 'Point' as const, coordinates: [d.longitude, d.latitude] },
      properties: { id: d.id, frp: d.frp },
    })),
  )
function currentGeometry(): FeatureCollection<Polygon | MultiPolygon> {
  return country.value === 'PER'
    ? departments
    : featureCollection(world.features.filter((f) => f.properties?.ADM0_A3 === country.value))
}
function fitCountry() {
  if (!map || !ready.value) return
  const points: Position[] = []
  function walk(value: unknown) {
    if (!Array.isArray(value)) return
    if (typeof value[0] === 'number') points.push(value as Position)
    else value.forEach(walk)
  }
  currentGeometry().features.forEach((f) => walk(f.geometry.coordinates))
  if (!points.length) return
  const bounds = new maplibregl.LngLatBounds()
  points.forEach((p) => bounds.extend([p[0], p[1]]))
  const width = container.value?.clientWidth ?? 900
  map.fitBounds(bounds, {
    padding: {
      top: width > 600 ? 55 : 235,
      bottom: width > 600 ? 80 : 145,
      left: width > 600 ? 220 : 25,
      right: 45,
    },
    duration: 650,
    maxZoom: 7,
  })
}
function resetView() {
  preview.value = undefined
  if (scope.value === 'world')
    map?.flyTo({ center: [-65, -10], zoom: 1.4, bearing: 0, pitch: 0, duration: 650 })
  else fitCountry()
}
function updateGeography() {
  if (!map || !ready.value) return
  map.setProjection({ type: scope.value === 'world' ? 'globe' : 'mercator' })
  const geography = currentGeometry()
  ;(map.getSource('area') as GeoJSONSource).setData(geography)
  if (scope.value === 'country') {
    // Dissolve shared administrative edges before making the white outside-country mask.
    const merged = geography.features.length > 1 ? union(geography) : geography.features[0]
    const rings =
      merged?.geometry.type === 'MultiPolygon'
        ? merged.geometry.coordinates.map((p) => p[0])
        : merged
          ? [merged.geometry.coordinates[0]]
          : []
    // Use a local rectangle: a 360-degree polygon collapses at the antimeridian.
    const positions = rings.flat()
    const west = Math.max(-179.99, Math.min(...positions.map((p) => p[0])) - 35)
    const east = Math.min(179.99, Math.max(...positions.map((p) => p[0])) + 35)
    const south = Math.max(-84.99, Math.min(...positions.map((p) => p[1])) - 35)
    const north = Math.min(84.99, Math.max(...positions.map((p) => p[1])) + 35)
    const outer = [
      [west, south],
      [east, south],
      [east, north],
      [west, north],
      [west, south],
    ]
    ;(map.getSource('mask') as GeoJSONSource).setData(polygon([outer, ...rings]))
    map.setMaxBounds([
      [west + 2, south + 2],
      [east - 2, north - 2],
    ])
  } else {
    map.setMaxBounds(null)
  }
  map.setLayoutProperty(
    'outside-mask',
    'visibility',
    scope.value === 'country' ? 'visible' : 'none',
  )
  map.setLayoutProperty('world-borders', 'visibility', scope.value === 'world' ? 'visible' : 'none')
  map.setLayoutProperty('area-fill', 'visibility', scope.value === 'country' ? 'visible' : 'none')
  map.setLayoutProperty('area-lines', 'visibility', scope.value === 'country' ? 'visible' : 'none')
  map.setLayoutProperty(
    'area-labels',
    'visibility',
    scope.value === 'country' && country.value === 'PER' ? 'visible' : 'none',
  )
  resetView()
}
function updatePoints() {
  if (map && ready.value) (map.getSource('observations') as GeoJSONSource).setData(collection())
}
function updatePopupPosition() {
  if (!map || !preview.value) return
  const point = map.project([preview.value.longitude, preview.value.latitude])
  const width = container.value?.clientWidth ?? 900
  popupPosition.value = {
    x: Math.max(12, Math.min(width - Math.min(310, width - 24) - 12, point.x - 145)),
    y: Math.max(110, Math.min((container.value?.clientHeight ?? 700) - 250, point.y - 215)),
  }
}
function showDetails(d: Detection) {
  selected.value = d
  preview.value = undefined
}
function selectExample() {
  const first = visible.value[0]
  if (first) showDetails(first)
}
watch([scope, country], () => {
  selected.value = undefined
  preview.value = undefined
  updateGeography()
  updatePoints()
})
watch(
  () => props.period,
  () => {
    preview.value = undefined
    selected.value = undefined
    updatePoints()
  },
)
watch(selected, async () => {
  await nextTick()
  map?.resize()
  if (scope.value === 'country') fitCountry()
})
onMounted(async () => {
  try {
    const results = await Promise.all([
      fetch('/geo/world.geojson'),
      fetch('/geo/peru-departments.geojson'),
    ])
    if (results.some((r) => !r.ok)) throw new Error('No se pudo cargar la cartografía local.')
    ;[world, departments] = await Promise.all(results.map((r) => r.json()))
    if (disposed || !container.value) return
    countries.value = world.features
      .map((f) => ({
        code: String(f.properties?.ADM0_A3),
        name: String(f.properties?.NAME_ES ?? f.properties?.NAME),
      }))
      .sort((a, b) => a.name.localeCompare(b.name, 'es'))
    map = new maplibregl.Map({
      container: container.value,
      center: [-75, -9],
      zoom: 4,
      attributionControl: false,
      renderWorldCopies: false,
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
            maxzoom: 17,
            attribution: 'Imagery © Esri, Maxar, Earthstar Geographics',
          },
          world: { type: 'geojson', data: world },
          area: { type: 'geojson', data: departments },
          mask: { type: 'geojson', data: featureCollection([]) },
          observations: { type: 'geojson', data: collection() },
        },
        layers: [
          { id: 'background', type: 'background', paint: { 'background-color': '#fff' } },
          {
            id: 'land-fallback',
            type: 'fill',
            source: 'world',
            paint: { 'fill-color': '#9cae88' },
          },
          {
            id: 'imagery',
            type: 'raster',
            source: 'imagery',
            paint: { 'raster-saturation': -0.3, 'raster-opacity': 0.94 },
          },
          {
            id: 'outside-mask',
            type: 'fill',
            source: 'mask',
            paint: { 'fill-color': '#ffffff', 'fill-opacity': 1 },
          },
          {
            id: 'area-fill',
            type: 'fill',
            source: 'area',
            paint: { 'fill-color': '#173c24', 'fill-opacity': 0.04 },
          },
          {
            id: 'area-lines',
            type: 'line',
            source: 'area',
            paint: { 'line-color': '#ffffff', 'line-width': 1.2, 'line-opacity': 0.9 },
          },
          {
            id: 'area-labels',
            type: 'symbol',
            source: 'area',
            layout: {
              'text-field': ['get', 'shapeName'],
              'text-font': ['Open Sans Regular'],
              'text-size': 11,
              'text-transform': 'uppercase',
              'text-letter-spacing': 0.08,
              'text-max-width': 8,
            },
            paint: { 'text-color': '#fff', 'text-halo-color': '#23452a', 'text-halo-width': 1.5 },
          },
          {
            id: 'world-borders',
            type: 'line',
            source: 'world',
            layout: { visibility: 'none' },
            paint: { 'line-color': '#ffffff', 'line-width': 0.6, 'line-opacity': 0.5 },
          },
          {
            id: 'point-halo',
            type: 'circle',
            source: 'observations',
            paint: { 'circle-radius': 12, 'circle-color': '#ed373f', 'circle-opacity': 0.14 },
          },
          {
            id: 'points',
            type: 'circle',
            source: 'observations',
            paint: {
              'circle-radius': ['interpolate', ['linear'], ['zoom'], 1, 3, 5, 5.5, 10, 8],
              'circle-color': ['step', ['get', 'frp'], '#f5c928', 10, '#f58a26', 30, '#e3323b'],
              'circle-stroke-color': '#fff',
              'circle-stroke-width': 1,
            },
          },
        ],
      },
    })
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    map.addControl(
      new maplibregl.AttributionControl({
        compact: true,
        customAttribution:
          '<a href="https://www.geoboundaries.org/" target="_blank" rel="noopener">geoBoundaries</a> · <a href="https://www.naturalearthdata.com/" target="_blank" rel="noopener">Natural Earth</a>',
      }),
      'bottom-right',
    )
    map.on('error', (e) => {
      if (e.error.message.includes('WebGL'))
        error.value =
          'El navegador no pudo iniciar el mapa. Activa la aceleración gráfica o prueba otro navegador.'
      else tileError.value = true
    })
    map.on('load', () => {
      ready.value = true
      updateGeography()
      updatePoints()
    })
    map.on('move', () => {
      if (preview.value) updatePopupPosition()
    })
    map.on('mouseenter', 'points', () => {
      if (map) map.getCanvas().style.cursor = 'pointer'
    })
    map.on('mouseleave', 'points', () => {
      if (map) map.getCanvas().style.cursor = ''
    })
    map.on('mousemove', 'points', (e) => {
      const id = e.features?.[0]?.properties?.id
      const d = visible.value.find((v) => v.id === id)
      if (d) {
        preview.value = d
        updatePopupPosition()
      }
    })
    map.on('click', 'points', (e) => {
      const d = visible.value.find((v) => v.id === e.features?.[0]?.properties?.id)
      if (d) showDetails(d)
    })
    map.on('click', (e) => {
      if (!map?.queryRenderedFeatures(e.point, { layers: ['points'] }).length)
        preview.value = undefined
    })
    observer = new ResizeObserver(() => {
      map?.resize()
      updatePopupPosition()
    })
    observer.observe(container.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo iniciar el mapa.'
  }
})
onUnmounted(() => {
  disposed = true
  observer?.disconnect()
  map?.remove()
})
</script>
<template>
  <div class="map-workspace" :class="{ 'with-detail': selected }">
    <section
      class="map-stage"
      :class="{ 'world-view': scope === 'world' }"
      aria-label="Explorador geográfico"
    >
      <div
        ref="container"
        class="map-canvas"
        aria-label="Mapa interactivo; usa los botones para explorar los ejemplos"
      />
      <div class="map-top-left">
        <div class="geography-controls">
          <div class="scope-switch" aria-label="Vista del mapa">
            <button
              :class="{ active: scope === 'country' }"
              :aria-pressed="scope === 'country'"
              @click="scope = 'country'"
            >
              <MapPin :size="16" /> País</button
            ><button
              :class="{ active: scope === 'world' }"
              :aria-pressed="scope === 'world'"
              @click="scope = 'world'"
            >
              <Globe2 :size="16" /> Mundo
            </button>
          </div>
          <label v-if="scope === 'country'" class="country-select"
            ><span class="sr-only">País seleccionado</span
            ><select v-model="country">
              <option v-for="c in countries" :key="c.code" :value="c.code">
                {{ c.name }}
              </option></select
            ><ChevronDown :size="15"
          /></label>
        </div>
        <div class="scope-summary">
          <div class="summary-title">
            <span class="status-dot" />{{ scope === 'world' ? 'Mundo' : countryName }}
            <span>· {{ periodLabels[period] }}</span>
          </div>
          <dl>
            <div>
              <dt><Flame :size="16" />Detecciones</dt>
              <dd>{{ visible.length }}</dd>
            </div>
            <div>
              <dt>
                <Layers :size="16" />{{
                  scope === 'world'
                    ? 'Regiones representadas'
                    : country === 'PER'
                      ? 'Departamentos con detecciones'
                      : 'Regiones con detecciones'
                }}
              </dt>
              <dd>{{ regionCount }}</dd>
            </div>
          </dl>
          <p><Info :size="13" /> Conteos de ejemplo · 13 nov. 2026</p>
        </div>
      </div>
      <button
        class="reset-map icon-button"
        aria-label="Restablecer vista del mapa"
        title="Restablecer vista"
        @click="resetView"
      >
        <RotateCcw :size="17" />
      </button>
      <div v-if="!ready && !error" class="map-loading" role="status">
        <LoaderCircle class="spin" /> Preparando el mapa…
      </div>
      <div v-if="error" class="map-error" role="alert">
        <AlertTriangle />
        <h3>No se pudo mostrar el mapa</h3>
        <p>{{ error }}</p>
        <button class="button button-red" @click="selectExample">Consultar datos de ejemplo</button>
      </div>
      <div
        v-if="preview && !error"
        class="observation-popup"
        :style="{ left: popupPosition.x + 'px', top: popupPosition.y + 'px' }"
        @keydown.esc="preview = undefined"
      >
        <span class="eyebrow">OBSERVACIÓN DE EJEMPLO</span>
        <h3><MapPin :size="18" />{{ preview.department }}</h3>
        <p>
          {{ countries.find((c) => c.code === preview!.country)?.name }} ·
          {{ dateLabel(preview.acquiredAt) }}
        </p>
        <dl>
          <div>
            <dt>Instrumento</dt>
            <dd>{{ preview.sensor }} · {{ preview.satellite }}</dd>
          </div>
          <div>
            <dt>Potencia radiativa</dt>
            <dd>{{ preview.frp.toFixed(1) }} MW</dd>
          </div>
          <div>
            <dt>Confianza original</dt>
            <dd>{{ preview.confidence }}</dd>
          </div>
        </dl>
        <button @click="showDetails(preview)">Explorar detalles <ArrowRight :size="16" /></button>
      </div>
      <div class="map-bottom-left">
        <div class="map-legend">
          <h4>Potencia radiativa <span>FRP · MW</span></h4>
          <div>
            <span
              v-for="[value, label] in [
                [5, '< 10'],
                [15, '10–<30'],
                [35, '≥ 30'],
              ]"
              :key="label"
              ><i :style="{ background: frpColor(Number(value)) }" />{{ label }}</span
            >
          </div>
          <small>Rangos visuales; no indican gravedad.</small>
        </div>
        <button v-if="visible.length" class="explore-example" @click="selectExample">
          <LocateFixed :size="15" />Explorar una observación<ArrowRight :size="15" /></button
        ><span v-else class="empty-map-message">No hay ejemplos para este país y periodo.</span>
      </div>
      <span class="map-hint"
        ><MousePointer2 :size="13" />{{
          scope === 'world'
            ? 'Arrastra para girar · Acerca para explorar'
            : 'Arrastra para mover · Selecciona un punto'
        }}</span
      >
      <div v-if="tileError && !error" class="tile-notice">
        Algunas imágenes no se pudieron cargar. Los límites y puntos siguen disponibles.
      </div>
    </section>
    <DetailPanel
      v-if="selected"
      :key="selected.id"
      :detection="selected"
      :period="period"
      :count="areaCount"
      :country-name="countries.find((c) => c.code === selected!.country)?.name ?? selected.country"
      @close="selected = undefined"
    />
  </div>
</template>
