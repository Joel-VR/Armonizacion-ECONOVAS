<script setup lang="ts">
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import {
  Map,
  CalendarDays,
  ChartNoAxesCombined,
  Info,
  RefreshCw,
} from '@lucide/vue'
import MapView from './components/MapView.vue'
import { type ScreenedAnalysis, type Decision } from './huanuco'
const CalendarView = defineAsyncComponent(() => import('./components/CalendarView.vue'))
const HistoryView = defineAsyncComponent(() => import('./components/HistoryView.vue'))
const view = ref('map')
const decision = ref<Decision>('candidate')
const cover = ref('all'),
  confidence = ref('all')
const analysis = ref<ScreenedAnalysis | null>(null),
  loading = ref(false),
  error = ref('')
const refresh = ref(0)
const nav = [
  { id: 'map', title: 'Mapa principal', icon: Map },
  { id: 'calendar', title: 'Calendario', icon: CalendarDays },
  { id: 'history', title: 'Análisis histórico', icon: ChartNoAxesCombined },
]
const query = computed(
  () =>
    '/api/huanuco/events/analysis?' +
    new URLSearchParams({
      decision: decision.value,
      cover: cover.value,
      confidence: confidence.value,
      refresh: String(refresh.value),
    }),
)
let controller: AbortController | undefined
watch(
  query,
  async (q) => {
    controller?.abort()
    const active = new AbortController()
    controller = active
    loading.value = true
    error.value = ''
    analysis.value = null
    try {
      const response = await fetch(q, { signal: active.signal })
      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(
          body.detail || 'No se pudo consultar la base local. Comprueba que la API esté activa.',
        )
      }
      const body = await response.json()
      if (!active.signal.aborted) analysis.value = body
    } catch (e) {
      if (!active.signal.aborted)
        error.value = e instanceof Error ? e.message : 'No se pudo conectar.'
    } finally {
      if (!active.signal.aborted) loading.value = false
    }
  },
  { immediate: true },
)
</script>
<template>
  <a href="#main" class="skip-link">Saltar al contenido</a>
  <div class="app-shell huanuco-app thematic-app" :class="{ 'map-page': view === 'map' }">
    <header class="topbar">
      <a class="brand turki-brand" href="#" @click.prevent="view = 'map'" aria-label="T'UKRI · Inicio">
        <span class="brand-logo"><img src="/brand/turki.png" alt="Mascota de T'UKRI" /></span>
        <span class="brand-name">T'UKRI</span>
        <span class="brand-location">Huánuco<small>Perú · 2026</small></span>
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
        <RefreshCw :size="18" :class="{ spin: loading }" />
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
      <div v-if="error" class="context-banner" role="alert"><Info :size="16" />{{ error }}</div>
      <p v-else-if="loading" class="loading-inline" role="status">
        Consultando las observaciones evaluadas…
      </p>
      <MapView
        v-if="view === 'map'"
        :decision="decision"
        :cover="cover"
        :confidence="confidence"
        :refresh="refresh"
        :analysis="analysis"
      />
      <CalendarView v-else-if="view === 'calendar'" :analysis="analysis" :decision="decision" />
      <HistoryView v-else :analysis="analysis" :decision="decision" />
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
