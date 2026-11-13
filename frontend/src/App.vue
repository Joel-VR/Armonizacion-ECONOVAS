<script setup lang="ts">
import { ref, defineAsyncComponent } from 'vue'
import {
  Map,
  CalendarDays,
  ChartNoAxesCombined,
  FlaskConical,
  Clock3,
  ChevronDown,
  Info,
  Satellite,
  ShieldCheck,
} from '@lucide/vue'
import MapView from './components/MapView.vue'
import { periodLabels, type Period } from './data'
const CalendarView = defineAsyncComponent(() => import('./components/CalendarView.vue'))
const HistoryView = defineAsyncComponent(() => import('./components/HistoryView.vue'))
const view = ref('map')
const period = ref<Period>('week')
const nav = [
  { id: 'map', title: 'Mapa principal', icon: Map },
  { id: 'calendar', title: 'Calendario', icon: CalendarDays },
  { id: 'history', title: 'Análisis histórico', icon: ChartNoAxesCombined },
]
</script>
<template>
  <a href="#main" class="skip-link">Saltar al contenido</a>
  <div class="app-shell">
    <header class="topbar">
      <a class="brand" href="#" aria-label="Brinco Alerta, inicio" @click.prevent="view = 'map'"
        ><span class="brand-logo"
          ><img src="/brand/brinco-alerta.png" alt="Conejo bombero de Brinco Alerta" /></span
        ><span
          >BRINCO<span class="brand-alert">ALERTA</span><small>OBSERVAR PARA PROTEGER</small></span
        ></a
      >
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
      <span class="demo-indicator"
        ><FlaskConical :size="15" /><span>PROTOTIPO<small>Conexión pendiente</small></span></span
      >
    </header>
    <main id="main">
      <div class="page-heading">
        <div>
          <span class="eyebrow"
            ><span class="tiny-line" />{{
              view === 'map'
                ? 'EXPLORA EL TERRITORIO'
                : view === 'calendar'
                  ? 'EXPLORA POR FECHA'
                  : 'COMPRENDE LOS PATRONES'
            }}</span
          >
          <h1>
            {{
              view === 'map'
                ? 'Incendios forestales y quemas agrícolas'
                : view === 'calendar'
                  ? 'Cada día cuenta.'
                  : 'Una mirada a lo largo del tiempo.'
            }}
          </h1>
          <p>
            {{
              view === 'map'
                ? 'Monitoreo satelital para conocer y proteger nuestro territorio.'
                : view === 'calendar'
                  ? 'Consulta las observaciones en el calendario de Perú.'
                  : 'Explora tendencias sin confundir detecciones con eventos confirmados.'
            }}
          </p>
        </div>
        <div class="update-status">
          <Clock3 :size="20" />
          <div><strong>Última actualización</strong><span>Vistas pendientes de conexión</span></div>
        </div>
      </div>
      <template v-if="view === 'map'"
        ><div class="map-toolbar">
          <label for="period"><CalendarDays :size="17" />Periodo</label>
          <div class="select-wrap">
            <select id="period" v-model="period">
              <option v-for="(label, key) in periodLabels" :key="key" :value="key">
                {{ label }}
              </option></select
            ><ChevronDown :size="15" />
          </div>
          <span class="toolbar-source"
            ><Satellite :size="16" />MODIS + VIIRS<span class="muted"
              >Conexión pendiente</span
            ></span
          ><span class="demo-date">Datos reales disponibles en la base</span>
        </div>
        <MapView :period="period"
      /></template>
      <Suspense v-else
        ><CalendarView v-if="view === 'calendar'" /><HistoryView v-else /><template #fallback
          ><div class="view-loading" role="status">Preparando la vista…</div></template
        ></Suspense
      >
    </main>
    <footer class="app-footer">
      <p>
        <Info :size="15" />Una detección satelital no confirma por sí sola un incendio forestal ni
        una quema agrícola.
      </p>
      <span><ShieldCheck :size="14" />Cuidemos lo que nos rodea.</span>
    </footer>
  </div>
</template>
