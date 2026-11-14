<script setup lang="ts">
import { computed, ref, watch, defineAsyncComponent } from 'vue'
import { Map, CalendarDays, ChartNoAxesCombined, Satellite, Info, SlidersHorizontal } from '@lucide/vue'
import MapView from './components/MapView.vue'
import type { Analysis } from './huanuco'
const CalendarView = defineAsyncComponent(() => import('./components/CalendarView.vue'))
const HistoryView = defineAsyncComponent(() => import('./components/HistoryView.vue'))
const view = ref('map')
const mode = ref<'sensor' | 'harmonized'>('sensor')
const nav = [{ id:'map', title:'Mapa principal', icon:Map }, { id:'calendar', title:'Calendario', icon:CalendarDays }, { id:'history', title:'Análisis histórico', icon:ChartNoAxesCombined }]
const year = ref(2026)
const grid = ref(5), confidence = ref('all'), fireType = ref('all')
const analysis = ref<Analysis | null>(null), loading = ref(false), error = ref('')
let requestId = 0
const query = computed(() => new URLSearchParams({year:String(year.value),grid:String(grid.value),confidence:confidence.value,fire_type:fireType.value}).toString())
watch(query, async q => {
  const id = ++requestId; loading.value = true; error.value = ''; analysis.value = null
  try { const response = await fetch('/api/huanuco/analysis?' + q); if(!response.ok) throw new Error('No se pudo consultar PostgreSQL. Revisa que la API esté iniciada.')
    const data = await response.json(); if(id === requestId) analysis.value = data
  } catch(e) { if(id === requestId) error.value = e instanceof Error ? e.message : 'Error de conexión' }
  finally { if(id === requestId) loading.value = false }
}, {immediate:true})
</script>
<template>
<a href="#main" class="skip-link">Saltar al contenido</a><div class="app-shell huanuco-app">
<header class="topbar"><a class="brand" href="#" @click.prevent="view='map'"><span class="brand-logo"><img src="/brand/brinco-alerta.png" alt="" /></span><span>BRINCO<span class="brand-alert">ALERTA</span><small>OBSERVAR PARA PROTEGER</small></span></a>
<nav aria-label="Navegación principal"><button v-for="item in nav" :key="item.id" :class="{active:view===item.id}" :aria-current="view===item.id?'page':undefined" @click="view=item.id"><component :is="item.icon" :size="19" />{{ item.title }}</button></nav><span class="demo-indicator"><Satellite :size="16"/><span>HUÁNUCO<small>Exploración · {{ year }}</small></span></span></header>
<main id="main"><div class="page-heading"><div><span class="eyebrow"><span class="tiny-line"/>HUÁNUCO · PERÚ · {{ year }}</span><h1>{{ view==='map'?'El territorio, de cerca.':view==='calendar'?'Cada día cuenta.':'Una mirada a lo largo del tiempo.' }}</h1><p>Observaciones satelitales de actividad térmica · MODIS y VIIRS Suomi</p></div><div class="update-status"><Satellite :size="20"/><div><strong>Fuentes disponibles hasta</strong><span v-if="analysis">MODIS {{ analysis.ends.MODIS }} · VIIRS {{ analysis.ends.VIIRS }}</span><span v-else>Consultando fuentes…</span></div></div></div>
<section class="filter-panel" aria-label="Filtros de análisis"><div class="filter-heading"><SlidersHorizontal :size="19"/><span>Explorar el análisis</span><small>Los filtros se aplican a las tres vistas</small></div><label>Año<select v-model.number="year"><option v-for="y in 11" :key="y" :value="2027-y">{{ 2027-y }}</option></select></label><label>Cuadrícula<select v-model.number="grid"><option :value="2">2 × 2 km</option><option :value="5">5 × 5 km</option><option :value="10">10 × 10 km</option></select></label><label>Confianza<select v-model="confidence"><option value="all">Todas</option><option value="high">Alta por sensor</option></select></label><label>Tipo de anomalía<select v-model="fireType"><option value="all">Todos, incluidos desconocidos</option><option value="vegetation">Vegetación conocida (tipo 0)</option></select></label></section>
<div class="view-mode" role="group" aria-label="Modo de visualización"><span>Visualización</span><button :class="{active:mode==='sensor'}" :aria-pressed="mode==='sensor'" @click="mode='sensor'">Por sensor</button><button :class="{active:mode==='harmonized'}" :aria-pressed="mode==='harmonized'" @click="mode='harmonized'">Armonizado <small>experimental</small></button></div>
<p class="filter-explanation">{{ confidence==='high'?'Alta: MODIS ≥ 80 / VIIRS h. ':'' }}{{ fireType==='vegetation'?'El filtro excluye los registros sin tipo, incluidos los NRT. ':'' }}Los sensores tienen sensibilidades distintas; la cobertura es desconocida.</p>
<div v-if="error" class="context-banner" role="alert">{{ error }}</div><div v-else-if="loading" class="context-banner" role="status">Calculando Huánuco y su referencia estacional…</div>
<Transition name="view" mode="out-in"><MapView v-if="view==='map'" :mode="mode" :grid="grid" :year="year" :analysis="analysis" :confidence="confidence" :fire-type="fireType"/><CalendarView v-else-if="view==='calendar'" :analysis="analysis" :year="year" :mode="mode"/><HistoryView v-else :analysis="analysis" :year="year" :mode="mode"/></Transition>
</main><footer class="app-footer"><p><Info :size="15"/>Una detección no confirma un incendio ni su causa. Sin detecciones no significa sin fuego.</p><span>NASA FIRMS · UTC</span></footer></div>
</template>
