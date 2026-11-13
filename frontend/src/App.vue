<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as maplibregl from 'maplibre-gl'
import type { GeoJSONSource } from 'maplibre-gl'
import mapWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'

maplibregl.setWorkerUrl(mapWorkerUrl)
type Detection = { id: number; latitude: number; longitude: number; acquired_at: string; sensor: string; satellite: string; confidence: string; frp: number | null; version: string; source_kind: string }
type Daily = { day: string; sensor: string; count: number }
const today = new Date().toISOString().slice(0, 10)
const start = ref(today.slice(0, 8) + '01')
const end = ref(today)
const view = ref<'map' | 'calendar'>('map')
const loading = ref(false)
const error = ref('')
const total = ref<number | null>(null)
const records = ref<Detection[]>([])
const daily = ref<Daily[]>([])
const selected = ref<Detection | null>(null)
const status = ref('Consultando base de datos…')
const mapElement = ref<HTMLDivElement>()
let map: maplibregl.Map | undefined
let requestId = 0

async function load() {
  const request = ++requestId
  loading.value = true; error.value = ''; selected.value = null
  try {
    const query = new URLSearchParams({ start: start.value, end: end.value })
    const [pointsResponse, dailyResponse] = await Promise.all([fetch('/api/fires?' + query), fetch('/api/daily?' + query)])
    if (!pointsResponse.ok || !dailyResponse.ok) throw new Error('No fue posible consultar la API. Comprueba la base de datos y el intervalo (máximo 367 días).')
    const [points, counts] = await Promise.all([pointsResponse.json(), dailyResponse.json()])
    if (request !== requestId) return
    records.value = points.data; total.value = points.total; daily.value = counts.data
    updateMap()
  } catch (e) {
    if (request !== requestId) return
    error.value = e instanceof Error ? e.message : 'Error al consultar los datos.'
    records.value = []; daily.value = []; total.value = null; updateMap()
  } finally { if (request === requestId) loading.value = false }
}
function updateMap() {
  const source = map?.getSource('fires') as GeoJSONSource | undefined
  source?.setData({ type: 'FeatureCollection', features: records.value.map(d => ({ type: 'Feature', geometry: { type: 'Point', coordinates: [d.longitude, d.latitude] }, properties: { id: d.id, sensor: d.sensor } })) })
}
async function mountMap() {
  await nextTick()
  if (!mapElement.value || map) return
  map = new maplibregl.Map({ container: mapElement.value, center: [-75, -9], zoom: 4, style: { version: 8, sources: { imagery: { type: 'raster', tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'], tileSize: 256, attribution: 'Imagery © Esri, Maxar, Earthstar Geographics' }, fires: { type: 'geojson', data: { type: 'FeatureCollection', features: [] } } }, layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#dce6da' } }, { id: 'imagery', type: 'raster', source: 'imagery' }, { id: 'fires', type: 'circle', source: 'fires', paint: { 'circle-radius': 4, 'circle-color': ['match', ['get', 'sensor'], 'MODIS', '#ffcf3c', '#f04a35'], 'circle-stroke-color': '#fff', 'circle-stroke-width': 1 } }] } })
  map.addControl(new maplibregl.NavigationControl(), 'top-right')
  map.on('load', updateMap)
  map.on('click', 'fires', e => { const id = Number(e.features?.[0]?.properties?.id); selected.value = records.value.find(d => d.id === id) ?? null })
}
watch(view, async value => { if (value === 'map') { await mountMap(); map?.resize() } else { map?.remove(); map = undefined } })
onMounted(async () => {
  await mountMap()
  try {
    const response = await fetch('/api/status')
    if (!response.ok) throw new Error()
    const data = await response.json()
    status.value = data.total ? data.total.toLocaleString('es-PE') + ' observaciones cargadas · última: ' + data.last.slice(0, 10) : 'Base de datos vacía'
  } catch { status.value = 'Base de datos no disponible' }
  await load()
})
onUnmounted(() => map?.remove())
</script>
<template>
  <div class="app-shell">
    <header class="topbar"><a class="brand" href="#"><span class="brand-logo"><img src="/brand/brinco-alerta.png" alt="" /></span><span>BRINCO<span class="brand-alert">ALERTA</span><small>OBSERVAR PARA PROTEGER</small></span></a><nav aria-label="Vistas"><button :class="{active:view==='map'}" @click="view='map'">Mapa</button><button :class="{active:view==='calendar'}" @click="view='calendar'">Calendario e histórico</button></nav></header>
    <main id="main">
      <div class="page-heading"><div><span class="eyebrow">NASA FIRMS · MODIS + VIIRS SUOMI</span><h1>Observaciones de anomalías térmicas</h1><p>{{ status }}</p></div></div>
      <form class="map-toolbar" @submit.prevent="load"><label for="start">Desde (UTC)</label><input id="start" v-model="start" type="date" required /><label for="end">Hasta (UTC)</label><input id="end" v-model="end" type="date" required /><button class="button button-red" :disabled="loading">{{ loading ? 'Consultando…' : 'Consultar' }}</button></form>
      <p v-if="error" role="alert" class="context-banner">{{ error }}</p>
      <p v-else class="context-banner">{{ total === null ? 'Consultando…' : total.toLocaleString('es-PE') + ' detecciones en el intervalo.' }} La ausencia de detecciones no confirma ausencia de fuego; la cobertura es desconocida.</p>
      <template v-if="view==='map'"><div ref="mapElement" style="height: 65vh; min-height: 420px; border-radius: 12px" aria-label="Mapa de detecciones"></div><p class="fine-print">Rojo: VIIRS Suomi · amarillo: MODIS. Se muestran hasta 5.000 puntos más recientes; los totales y el calendario incluyen todo el intervalo.</p><section v-if="selected" class="surface calendar-card"><button class="button button-outline" @click="selected=null">Cerrar</button><h2>Observación {{ selected.id }}</h2><p>{{ selected.sensor }} · {{ selected.satellite }} · {{ selected.acquired_at }} · {{ selected.source_kind }} · versión {{ selected.version }}</p><p>{{ selected.latitude }}, {{ selected.longitude }} · Confianza: {{ selected.confidence }} · FRP: {{ selected.frp ?? 'sin dato' }} MW</p></section></template>
      <section v-else class="surface calendar-card"><h2>Detecciones diarias por sensor</h2><p>Conteos de puntos, no incendios únicos ni datos armonizados. Los días sin filas no prueban ausencia de actividad.</p><table><thead><tr><th>Fecha UTC</th><th>Sensor</th><th>Detecciones</th></tr></thead><tbody><tr v-for="row in daily" :key="row.day + row.sensor"><td>{{ row.day }}</td><td>{{ row.sensor }}</td><td>{{ row.count }}</td></tr></tbody></table><p v-if="!daily.length && !loading">Sin registros para el periodo consultado.</p></section>
    </main><footer class="app-footer"><p>Una detección no confirma por sí sola un incendio ni identifica su causa. Datos NRT sujetos a revisión.</p></footer>
  </div>
</template>
