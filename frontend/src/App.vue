<script setup lang="ts">
import { defineAsyncComponent, ref, watch } from 'vue'
import {
  Map,
  CalendarDays,
  ChartNoAxesCombined,
  Info,
  RefreshCw,
} from '@lucide/vue'
import MapView from './components/MapView.vue'
import { type Analysis } from './huanuco'
const WeeklyView = defineAsyncComponent(() => import('./components/WeeklyView.vue'))
const view = ref('map')
const refresh = ref(0)
const year = ref(2026)
const weekly = ref<Analysis | null>(null)
const weeklyError = ref('')
watch([refresh, year], async (_, __, onCleanup) => {
  const controller = new AbortController()
  onCleanup(() => controller.abort())
  weeklyError.value = ''
  try {
    const response = await fetch(`/api/departments/PE-HUC/analysis?year=${year.value}&grid=5&confidence=all&fire_type=all`, { signal: controller.signal })
    if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail || 'No se pudieron consultar los indicadores semanales.') }
    const result = await response.json()
    if (!controller.signal.aborted) weekly.value = result
  } catch (e) { if (!controller.signal.aborted) { weekly.value = null; weeklyError.value = e instanceof Error ? e.message : 'Error de conexión.' } }
}, { immediate: true })
const nav = [
  { id: 'map', title: 'Mapa principal', icon: Map },
  { id: 'calendar', title: 'Calendario', icon: CalendarDays },
  { id: 'history', title: 'Análisis histórico', icon: ChartNoAxesCombined },
]
</script>
<template>
  <a href="#main" class="skip-link">Saltar al contenido</a>
  <div class="app-shell huanuco-app thematic-app" :class="{ 'map-page': view === 'map' }">
    <header class="topbar">
      <a class="brand turki-brand" href="#" @click.prevent="view = 'map'" aria-label="T'UKRI · Inicio">
        <span class="brand-logo"><img src="/brand/turki.png" alt="Mascota de T'UKRI" /></span>
        <span class="brand-name">T'UKRI</span>
        <span class="brand-location">Huánuco<small>Perú · {{ year }}</small></span>
      </a>
      <nav aria-label="Navegación principal">
        <button
          v-for="item in nav"
          :key="item.id"
          :class="{ active: view === item.id }"
          :aria-current="view === item.id ? 'page' : undefined"
          @click="view = item.id"
        >
          <component :is="item.icon" :size="18" />{{ item.title }}
        </button>
      </nav>
      <button class="icon-button header-refresh" aria-label="Actualizar datos" title="Actualizar datos" @click="refresh++">
        <RefreshCw :size="18"  />
      </button>
    </header>
    <main id="main">
      <div v-if="view !== 'map'" class="page-heading">
        <div>
          <h1>
            {{
              view === 'map'
                ? 'Detección de incendios forestales y quemas agrícolas'
                : view === 'calendar'
                  ? 'Cada día cuenta.'
                  : 'El año, en perspectiva.'
            }}
          </h1>
        </div>
      </div>
      <div v-if="weeklyError" class="context-banner" role="alert"><Info :size="16" />{{ weeklyError }}</div>
      <MapView
        v-if="view === 'map'"
        :refresh="refresh"
        :analysis="weekly"
        v-model:year="year"
      />
      <WeeklyView v-if="view === 'calendar' || view === 'history'" :analysis="weekly" :calendar="view === 'calendar'" v-model:year="year" />
      <WeeklyView v-if="view === 'map'" :analysis="weekly" :calendar="false" :year="year" compact />
    </main>
    <footer class="app-footer">
      <p>
        <Info :size="15" />Una observación no equivale a un incendio. La cobertura anterior y el
        centro del píxel son aproximaciones.
      </p>
      <span>NASA FIRMS · MapBiomas Perú · UTC</span>
    </footer>
  </div>
</template>
