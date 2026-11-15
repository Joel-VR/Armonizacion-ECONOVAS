<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import * as maplibregl from 'maplibre-gl'
import type { GeoJSONSource } from 'maplibre-gl'
import mapWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import { MapPin, RotateCcw, X } from '@lucide/vue'
import { percent, type Analysis } from '../huanuco'
type Observation = { latitude: number; longitude: number; acq_date: string; acq_time: string; sensor: string; satellite: string; confidence: string; fire_type: string | null; frp: number | null; brightness: number | null; scan: number | null; track: number | null; daynight: string; version: string }
const props = defineProps<{ refresh: number; year: number; analysis: Analysis | null }>()
const emit = defineEmits<{ 'update:year': [year: number] }>()
maplibregl.setWorkerUrl(mapWorkerUrl)
const element = ref<HTMLDivElement>(), month = ref('all'), sensor = ref('all'), confidence = ref('all'), fireType = ref('all')
const mode = ref<'observations' | 'harmonized'>('observations'), weekStart = ref('')
const weeks = computed(() => props.analysis?.year === props.year ? props.analysis.weekly : [])
const selectedWeek = computed(() => weeks.value.find(w => w.start === weekStart.value))
watch(weeks, items => { weekStart.value = items.find(w => w.combined !== null)?.start ?? items[0]?.start ?? '' }, { immediate: true })
const indicatorColor = computed(() => {
  const n = selectedWeek.value?.combined
  return n == null ? '#9ca3a1' : n < .25 ? '#4c9f69' : n < .75 ? '#efcc51' : n < .9 ? '#ee963d' : '#d84442'
})
const data = ref<Observation[]>([]), selected = ref<Observation | null>(null), busy = ref(false), error = ref(''), total = ref(0), truncated = ref(false)
const months = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
let map: maplibregl.Map | undefined, controller: AbortController | undefined, resizeObserver: ResizeObserver | undefined, regionBounds: maplibregl.LngLatBounds | undefined
const range = computed(() => {
  if (month.value === 'all') return { start: props.year + '-01-01', end: props.year + '-12-31' }
  const n = Number(month.value), prefix = props.year + '-' + String(n).padStart(2,'0')
  return { start: prefix + '-01', end: prefix + '-' + new Date(Date.UTC(props.year,n,0)).getUTCDate() }
})
function draw() {
  const source = map?.getSource('detections') as GeoJSONSource | undefined
  source?.setData({type:'FeatureCollection',features:data.value.map((d,i)=>({type:'Feature',geometry:{type:'Point',coordinates:[d.longitude,d.latitude]},properties:{index:i,sensor:d.sensor}}))})
  if (map?.getLayer('region') && map.getLayer('points')) {
    map.setPaintProperty('region', 'fill-color', mode.value === 'harmonized' ? indicatorColor.value : '#c3e9c1')
    map.setPaintProperty('region', 'fill-opacity', mode.value === 'harmonized' ? 0.7 : 0.12)
    map.setLayoutProperty('points', 'visibility', mode.value === 'harmonized' ? 'none' : 'visible')
  }
}
watch([mode, indicatorColor], () => { selected.value = null; draw() })
watch([range, sensor, confidence, fireType, mode, () => props.refresh], async () => {
  controller?.abort(); const active = new AbortController(); controller = active
  busy.value = true; error.value = ''; selected.value = null; data.value = []; draw()
  if (mode.value === 'harmonized') { busy.value = false; return }
  try {
    const q = new URLSearchParams({...range.value,sensor:sensor.value,confidence:confidence.value,fire_type:fireType.value})
    const response = await fetch('/api/huanuco/observations?' + q, {signal:active.signal})
    if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail || 'No se pudieron consultar las observaciones.') }
    const result = await response.json(); if (active.signal.aborted) return
    data.value = result.data; total.value = result.total; truncated.value = result.truncated; draw()
  } catch (e) { if (!active.signal.aborted) error.value = e instanceof Error ? e.message : 'Error de conexión.' }
  finally { if (!active.signal.aborted) busy.value = false }
}, {immediate:true})
onMounted(async () => {
  try {
    const response = await fetch('/geo/peru-departments.geojson'); if (!response.ok) throw new Error('No se pudo cargar el límite departamental.')
    const geo = await response.json(); const region = {type:'FeatureCollection',features:geo.features.filter((f:{properties:{shapeISO:string}})=>f.properties.shapeISO==='PE-HUC')}
    regionBounds = new maplibregl.LngLatBounds()
    function includeCoordinates(value: unknown): void {
      if (!Array.isArray(value)) return
      if (typeof value[0] === 'number' && typeof value[1] === 'number') regionBounds?.extend([value[0], value[1]])
      else value.forEach(includeCoordinates)
    }
    region.features.forEach((feature: {geometry: {coordinates: unknown}}) => includeCoordinates(feature.geometry.coordinates))
    if (!element.value) return
    map = new maplibregl.Map({container:element.value,center:[-75.9,-9.4],zoom:6,style:{version:8,sources:{imagery:{type:'raster',tiles:['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],tileSize:256,attribution:'Imagery © Esri'},region:{type:'geojson',data:region},detections:{type:'geojson',data:{type:'FeatureCollection',features:[]}}},layers:[{id:'imagery',type:'raster',source:'imagery'},{id:'region',type:'fill',source:'region',paint:{'fill-color':'#c3e9c1','fill-opacity':0.12}},{id:'border',type:'line',source:'region',paint:{'line-color':'#fff','line-width':2}},{id:'points',type:'circle',source:'detections',paint:{'circle-radius':4,'circle-color':['match',['get','sensor'],'MODIS','#ffd65a','#ef453e'],'circle-stroke-color':'#fff','circle-stroke-width':1}}]}})
    map.addControl(new maplibregl.NavigationControl(),'top-right'); map.on('load',()=>{ draw(); fitRegion(0) })
    resizeObserver = new ResizeObserver(() => map?.resize())
    resizeObserver.observe(element.value)
    map.on('click','points',e=>{ selected.value=data.value[Number(e.features?.[0]?.properties?.index)] ?? null })
  } catch(e) { error.value = e instanceof Error ? e.message : 'No se pudo iniciar el mapa.' }
})
onUnmounted(()=>{controller?.abort();resizeObserver?.disconnect();map?.remove()})
function fitRegion(duration = 450) { if (regionBounds && !regionBounds.isEmpty()) map?.fitBounds(regionBounds, {padding: 50, maxZoom: 9, duration}) }
</script>
<template>
  <div class="map-panel"><div class="map-workspace with-detail right-filter-layout">
    <section class="map-stage thematic-stage" aria-label="Mapa de detecciones de Huánuco">
      <div ref="element" class="map-canvas" aria-label="Mapa de detecciones satelitales" />
      <button class="reset-map icon-button" aria-label="Restablecer vista" @click="fitRegion()"><RotateCcw :size="16" /></button>
      <div v-if="mode === 'observations'" class="map-count-card"><span style="background:#ef453e" /><div><small>Detecciones registradas</small><strong>{{ busy ? '…' : error ? '—' : total.toLocaleString('es-PE') }}</strong></div><small v-if="truncated">Se muestran las 20.000 más recientes.</small></div>
      <div v-else class="map-count-card"><span :style="{background:indicatorColor}" /><div><small>Índice semanal de Huánuco</small><strong>{{ percent(selectedWeek?.combined ?? null) }}</strong></div><small>{{ selectedWeek ? selectedWeek.start + ' a ' + selectedWeek.end : 'Semana no disponible' }}</small></div>
      <div v-if="mode === 'observations'" class="thematic-bottom"><span>MODIS · amarillo &nbsp; VIIRS Suomi · rojo</span><span>Una detección no confirma un incendio.</span></div>
      <div v-else class="thematic-bottom"><span>Verde &lt;25% · amarillo 25–74% · naranja 75–89% · rojo ≥90% · gris sin comparación</span><span>Índice departamental experimental</span></div>
      <p v-if="error && mode === 'observations'" class="tile-notice" role="alert">{{ error }}</p>
    </section>
    <aside class="detail-panel map-side-panel"><div class="map-side-heading"><h1>{{ mode === 'observations' ? 'Detecciones satelitales en Huánuco' : 'Actividad armonizada en Huánuco' }}</h1></div>
      <div class="view-mode" role="group" aria-label="Visualización del mapa"><button :class="{active:mode === 'observations'}" :aria-pressed="mode === 'observations'" @click="mode = 'observations'">Detecciones</button><button :class="{active:mode === 'harmonized'}" :aria-pressed="mode === 'harmonized'" @click="mode = 'harmonized'">Armonizado</button></div>
      <div class="map-toolbar huanuco-toolbar">
        <label>Año<select :value="year" @change="emit('update:year', Number(($event.target as HTMLSelectElement).value))"><option v-for="y in 11" :key="y" :value="2027-y">{{ 2027-y }}</option></select></label>
        <template v-if="mode === 'observations'"><label>Mes<select v-model="month"><option value="all">Todo el año</option><option v-for="(m,i) in months" :key="m" :value="String(i+1)">{{ m }}</option></select></label>
        <label>Sensor<select v-model="sensor"><option value="all">Ambos</option><option>MODIS</option><option>VIIRS</option></select></label>
        <label>Confianza<select v-model="confidence"><option value="all">Todas</option><option value="high">Alta por sensor</option></select></label>
        <label>Tipo NASA<select v-model="fireType"><option value="all">Todos</option><option value="0">Vegetación</option><option value="1">Volcán</option><option value="2">Otra fuente terrestre</option><option value="3">Fuente marina</option><option value="unknown">No informado</option></select></label>
        <span class="toolbar-source"><MapPin :size="15" />{{ range.start }} a {{ range.end }} · UTC</span>
        </template>
        <label v-else>Semana<select v-model="weekStart" :disabled="!weeks.length"><option v-if="!weeks.length" value="">Sin datos disponibles</option><option v-for="w in weeks" :key="w.start" :value="w.start">Semana {{ w.week }} · {{ w.start }} a {{ w.end }}</option></select></label>
      </div>
      <div v-if="mode === 'harmonized'" class="detail-body"><h3>Resultado semanal experimental</h3><p>El color representa un único indicador para todo el departamento; no muestra puntos ni valores por celda.</p><template v-if="selectedWeek"><p>MODIS: {{ selectedWeek.sensors.MODIS.cells ?? '—' }} celdas-día · percentil {{ percent(selectedWeek.sensors.MODIS.percentile) }}</p><p>VIIRS Suomi: {{ selectedWeek.sensors.VIIRS.cells ?? '—' }} celdas-día · percentil {{ percent(selectedWeek.sensors.VIIRS.percentile) }}</p><p>Índice combinado: <strong>{{ percent(selectedWeek.combined) }}</strong> · diferencia: {{ percent(selectedWeek.disagreement) }}</p><p v-if="selectedWeek.combined === null">Sin comparación: semana incompleta, referencia insuficiente o demasiados empates.</p></template><p v-else>No hay datos semanales disponibles para este año.</p><p class="inline-note">Cuadrícula de 5 km; sin filtros de confianza ni tipo. No representa probabilidad de incendio.</p></div>
      <div v-else-if="!selected" class="map-selection-hint"><MapPin :size="24"/><h3>Explora el mapa</h3><p>Selecciona un punto para consultar la observación original.</p></div>
      <div v-else class="detail-body"><div class="detail-header"><h2>Detección {{ selected.sensor }}</h2><button class="icon-button" aria-label="Cerrar detalle" @click="selected=null"><X :size="18" /></button></div>
        <dl class="data-list"><div><dt>Fecha y hora UTC</dt><dd>{{ selected.acq_date }} · {{ selected.acq_time.padStart(4,'0') }}</dd></div><div><dt>Coordenadas</dt><dd>{{ selected.latitude.toFixed(4) }}, {{ selected.longitude.toFixed(4) }}</dd></div><div><dt>Satélite</dt><dd>{{ selected.satellite }}</dd></div><div><dt>Confianza</dt><dd>{{ selected.confidence }}</dd></div><div><dt>Tipo NASA</dt><dd>{{ selected.fire_type ?? 'No informado' }}</dd></div><div><dt>Potencia radiativa</dt><dd>{{ selected.frp ?? '—' }} MW</dd></div><div><dt>Brillo</dt><dd>{{ selected.brightness ?? '—' }} K</dd></div><div><dt>Producto</dt><dd>{{ selected.version }}</dd></div></dl>
        <p class="inline-note">Una detección es una anomalía térmica; no demuestra su causa ni identifica un incendio único.</p></div>
    </aside></div><p class="map-source-note">{{ mode === 'harmonized' ? 'Huánuco · indicador semanal experimental a escala departamental.' : 'Huánuco · datos originales NASA FIRMS · Los filtros no modifican los indicadores semanales.' }}</p></div>
</template>
