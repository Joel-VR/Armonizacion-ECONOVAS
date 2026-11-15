<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed, nextTick } from 'vue'
import {
  Map,
  CalendarDays,
  ChartNoAxesCombined,
  Info,
  RefreshCw,
  BookOpen,
  MapPin,
  Search,
  ChevronDown,
  Check,
  X,
} from '@lucide/vue'
import MapView from './components/MapView.vue'
import CalendarView from './components/CalendarView.vue'
import HistoryView from './components/HistoryView.vue'
import MethodologyModal from './components/MethodologyModal.vue'
import { type Analysis } from './huanuco'

const view = ref<'map' | 'calendar' | 'history'>('map')
const refresh = ref(0)
const year = ref(2026)
const selectedMonthForMap = ref<number | string>('all')
const weekly = ref<Analysis | null>(null)
const weeklyError = ref('')
const showMethodology = ref(false)

const currentDepartment = ref('PE-HUC')
const isDeptOpen = ref(false)
const deptSearch = ref('')
const deptSelectorRef = ref<HTMLElement | null>(null)
const deptSearchInputRef = ref<HTMLInputElement | null>(null)

const departmentsList = ref([
  { code: 'PE-HUC', name: 'Huánuco' },
  { code: 'PE-UCA', name: 'Ucayali' },
  { code: 'PE-MDD', name: 'Madre de Dios' },
  { code: 'PE-LOR', name: 'Loreto' },
  { code: 'PE-SAM', name: 'San Martín' },
  { code: 'PE-CUS', name: 'Cusco' },
  { code: 'PE-PAS', name: 'Pasco' },
  { code: 'PE-JUN', name: 'Junín' },
  { code: 'PE-AMA', name: 'Amazonas' },
  { code: 'PE-ANC', name: 'Áncash' },
  { code: 'PE-APU', name: 'Apurímac' },
  { code: 'PE-ARE', name: 'Arequipa' },
  { code: 'PE-AYA', name: 'Ayacucho' },
  { code: 'PE-CAJ', name: 'Cajamarca' },
  { code: 'PE-HUV', name: 'Huancavelica' },
  { code: 'PE-ICA', name: 'Ica' },
  { code: 'PE-LAL', name: 'La Libertad' },
  { code: 'PE-LAM', name: 'Lambayeque' },
  { code: 'PE-LIM', name: 'Lima' },
  { code: 'PE-MOQ', name: 'Moquegua' },
  { code: 'PE-PIU', name: 'Piura' },
  { code: 'PE-PUN', name: 'Puno' },
  { code: 'PE-TAC', name: 'Tacna' },
  { code: 'PE-TUM', name: 'Tumbes' },
  { code: 'PE-CAL', name: 'Callao' },
])

const currentDepartmentName = computed(() => {
  return departmentsList.value.find((d) => d.code === currentDepartment.value)?.name || 'Huánuco'
})

const filteredDepartments = computed(() => {
  const q = deptSearch.value.trim().toLowerCase()
  if (!q) return departmentsList.value
  return departmentsList.value.filter(
    (d) => d.name.toLowerCase().includes(q) || d.code.toLowerCase().includes(q)
  )
})

function toggleDeptDropdown() {
  isDeptOpen.value = !isDeptOpen.value
  if (isDeptOpen.value) {
    deptSearch.value = ''
    nextTick(() => {
      deptSearchInputRef.value?.focus()
    })
  }
}

function selectDepartment(code: string) {
  currentDepartment.value = code
  isDeptOpen.value = false
  deptSearch.value = ''
}

function selectFirstFiltered() {
  if (filteredDepartments.value.length > 0) {
    selectDepartment(filteredDepartments.value[0].code)
  }
}

function handleClickOutside(event: MouseEvent) {
  if (deptSelectorRef.value && !deptSelectorRef.value.contains(event.target as Node)) {
    isDeptOpen.value = false
  }
}

onMounted(async () => {
  window.addEventListener('click', handleClickOutside)
  try {
    const res = await fetch('/api/departments')
    if (res.ok) {
      const data = await res.json()
      if (data.data?.length) {
        departmentsList.value = data.data
      }
    }
  } catch {
    // Keep fallback
  }
})

onUnmounted(() => {
  window.removeEventListener('click', handleClickOutside)
})

watch(
  [refresh, year, currentDepartment],
  async (_, __, onCleanup) => {
    const controller = new AbortController()
    onCleanup(() => controller.abort())
    weeklyError.value = ''
    try {
      const response = await fetch(
        `/api/departments/${currentDepartment.value}/analysis?year=${year.value}&grid=5&confidence=all&fire_type=all`,
        { signal: controller.signal }
      )
      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(body.detail || 'No se pudieron consultar los indicadores semanales.')
      }
      const result = await response.json()
      if (!controller.signal.aborted) weekly.value = result
    } catch (e) {
      if (!controller.signal.aborted) {
        weekly.value = null
        weeklyError.value = e instanceof Error ? e.message : 'Error de conexión.'
      }
    }
  },
  { immediate: true }
)

const nav = [
  { id: 'map' as const, title: 'Mapa principal', icon: Map },
  { id: 'calendar' as const, title: 'Calendario de Quemas', icon: CalendarDays },
  { id: 'history' as const, title: 'Análisis histórico', icon: ChartNoAxesCombined },
]

function onNavigateToMap({ year: yr, month: m }: { year: number; month: number }) {
  year.value = yr
  selectedMonthForMap.value = m
  view.value = 'map'
}
</script>

<template>
  <a href="#main" class="skip-link">Saltar al contenido</a>
  <div class="app-shell huanuco-app thematic-app" :class="{ 'map-page': view === 'map' }">
    <!-- Topbar Navigation -->
    <header class="topbar">
      <a class="brand turki-brand" href="#" @click.prevent="view = 'map'" aria-label="T'UKRI · Inicio">
        <span class="brand-logo"><img src="/brand/turki.svg" alt="Mascota de T'UKRI" /></span>
        <span class="brand-name">T'UKRI</span>
        <span class="brand-location">
          {{ currentDepartmentName }}<small>Perú · {{ year }}</small>
        </span>
      </a>

      <!-- Department AOI Combobox / Searchable Selector -->
      <div ref="deptSelectorRef" class="header-aoi-selector" :class="{ 'is-open': isDeptOpen }">
        <button
          type="button"
          class="dept-trigger"
          aria-haspopup="listbox"
          :aria-expanded="isDeptOpen"
          title="Seleccionar departamento del Perú"
          @click.stop="toggleDeptDropdown"
        >
          <span class="aoi-label">
            <MapPin :size="13" /> Departamento:
          </span>
          <span class="dept-current-name">{{ currentDepartmentName }}</span>
          <ChevronDown :size="13" class="dept-chevron" :class="{ 'rotate': isDeptOpen }" />
        </button>

        <!-- Floating Dropdown Panel -->
        <div v-if="isDeptOpen" class="dept-dropdown-panel" role="listbox" @click.stop>
          <div class="dept-search-header">
            <Search :size="14" class="search-icon" />
            <input
              ref="deptSearchInputRef"
              v-model="deptSearch"
              type="text"
              class="dept-search-input"
              placeholder="Buscar departamento..."
              @keydown.esc="isDeptOpen = false"
              @keydown.enter.prevent="selectFirstFiltered"
            />
            <button
              v-if="deptSearch"
              type="button"
              class="clear-search-btn"
              title="Borrar búsqueda"
              @click="deptSearch = ''"
            >
              <X :size="12" />
            </button>
          </div>

          <ul class="dept-options-list">
            <li
              v-for="d in filteredDepartments"
              :key="d.code"
              class="dept-option-item"
              :class="{ 'is-selected': d.code === currentDepartment }"
              role="option"
              :aria-selected="d.code === currentDepartment"
              @click="selectDepartment(d.code)"
            >
              <span class="option-name">{{ d.name }}</span>
              <span class="option-code">{{ d.code.replace('PE-', '') }}</span>
              <Check v-if="d.code === currentDepartment" :size="14" class="check-icon" />
            </li>
            <li v-if="filteredDepartments.length === 0" class="dept-no-results">
              No se encontró "{{ deptSearch }}"
            </li>
          </ul>

          <div class="dept-dropdown-footer">
            <span>25 departamentos · Ámbito nacional</span>
          </div>
        </div>
      </div>

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

      <div class="header-right-tools">
        <!-- Methodology Trigger -->
        <button
          class="methodology-pill-btn"
          aria-label="Metodología NASA"
          title="Ver metodología de armonización y sensores"
          @click="showMethodology = true"
        >
          <BookOpen :size="15" />
          <span>Metodología NASA</span>
        </button>

        <!-- Refresh Button -->
        <button
          class="icon-button header-refresh"
          aria-label="Actualizar datos"
          title="Actualizar datos"
          @click="refresh++"
        >
          <RefreshCw :size="18" />
        </button>
      </div>
    </header>

    <main id="main">
      <div v-if="view !== 'map'" class="page-heading">
        <div>
          <h1>
            {{
              view === 'calendar'
                ? `Calendario de Actividad de Fuego · ${currentDepartmentName}`
                : `Trayectoria Histórica y Detección de Anomalías · ${currentDepartmentName}`
            }}
          </h1>
          <p class="heading-sub">
            Sistema de Armonización Satelital MODIS & VIIRS · NASA Space Apps Challenge
          </p>
        </div>
      </div>

      <div v-if="weeklyError" class="context-banner" role="alert">
        <Info :size="16" />{{ weeklyError }}
      </div>

      <!-- MAP VIEW -->
      <MapView
        v-if="view === 'map'"
        :refresh="refresh"
        :analysis="weekly"
        :department-code="currentDepartment"
        :department-name="currentDepartmentName"
        :initial-month="selectedMonthForMap"
        v-model:year="year"
      />

      <!-- BURNING ACTIVITY CALENDAR VIEW -->
      <CalendarView
        v-else-if="view === 'calendar'"
        :department-code="currentDepartment"
        :selected-year="year"
        :analysis="weekly"
        v-model:year="year"
        @navigate-to-map="onNavigateToMap"
      />

      <!-- HISTORICAL ANALYSIS VIEW -->
      <HistoryView
        v-else-if="view === 'history'"
        :analysis="weekly"
        :department-code="currentDepartment"
        v-model:year="year"
      />
    </main>

    <!-- Methodology Modal -->
    <MethodologyModal :open="showMethodology" @close="showMethodology = false" />

    <footer class="app-footer">
      <p>
        <Info :size="15" />Una detección térmica satelital no equivale a un incendio confirmado en campo.
        Índices armonizados generados mediante la metodología oficial NASA Space Apps.
      </p>
      <span>NASA FIRMS · MODIS C6.1 · VIIRS C2 · UTC</span>
    </footer>
  </div>
</template>

<style scoped>
.header-aoi-selector {
  position: relative;
  display: flex;
  align-items: center;
}

.dept-trigger {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  background: #f8fafc;
  padding: 0.3rem 0.65rem;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
  font-family: inherit;
  outline: none;
}

.dept-trigger:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.header-aoi-selector.is-open .dept-trigger {
  background: #ffffff;
  border-color: #94a3b8;
  box-shadow: 0 0 0 2px rgba(15, 23, 42, 0.06);
}

.dept-trigger:focus-visible {
  outline: 2px solid rgba(184, 29, 36, 0.35);
  outline-offset: 2px;
}

.aoi-label {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.72rem;
  font-weight: 750;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.dept-current-name {
  font-size: 0.85rem;
  font-weight: 800;
  color: #0f172a;
}

.dept-chevron {
  color: #64748b;
  transition: transform 0.18s ease;
}

.dept-chevron.rotate {
  transform: rotate(180deg);
}

/* Floating Dropdown Panel */
.dept-dropdown-panel {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  width: 250px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.12), 0 8px 10px -6px rgba(0, 0, 0, 0.04);
  z-index: 1000;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  animation: deptPop 0.15s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes deptPop {
  from {
    opacity: 0;
    transform: translateY(-4px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.dept-search-header {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.5rem 0.65rem;
  border-bottom: 1px solid #f1f5f9;
  background: #f8fafc;
}

.search-icon {
  color: #94a3b8;
  flex-shrink: 0;
}

.dept-search-input {
  width: 100%;
  border: none;
  background: transparent;
  font-size: 0.82rem;
  font-weight: 600;
  color: #0f172a;
  outline: none;
  font-family: inherit;
}

.dept-search-input::placeholder {
  color: #94a3b8;
}

.clear-search-btn {
  background: transparent;
  border: none;
  padding: 2px;
  color: #94a3b8;
  cursor: pointer;
  display: flex;
  align-items: center;
  border-radius: 4px;
}

.clear-search-btn:hover {
  color: #0f172a;
  background: #e2e8f0;
}

.dept-options-list {
  list-style: none;
  margin: 0;
  padding: 0.3rem 0;
  max-height: 220px;
  overflow-y: auto;
}

.dept-options-list::-webkit-scrollbar {
  width: 5px;
}

.dept-options-list::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}

.dept-option-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.45rem 0.75rem;
  font-size: 0.83rem;
  font-weight: 600;
  color: #334155;
  cursor: pointer;
  transition: all 0.12s ease;
}

.dept-option-item:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.dept-option-item.is-selected {
  background: #fef2f2;
  color: #b81d24;
  font-weight: 750;
}

.option-name {
  flex: 1;
}

.option-code {
  font-size: 0.7rem;
  color: #94a3b8;
  font-weight: 700;
  margin-right: 0.4rem;
}

.check-icon {
  color: #b81d24;
  flex-shrink: 0;
}

.dept-no-results {
  padding: 1rem 0.75rem;
  text-align: center;
  font-size: 0.8rem;
  color: #94a3b8;
}

.dept-dropdown-footer {
  padding: 0.35rem 0.65rem;
  background: #f8fafc;
  border-top: 1px solid #f1f5f9;
  font-size: 0.68rem;
  font-weight: 600;
  color: #94a3b8;
  text-align: center;
}

.header-right-tools {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.methodology-pill-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.24rem 0.68rem;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 9999px;
  color: #b45309;
  font-weight: 800;
  font-size: 0.78rem;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: all 0.15s ease;
}
.methodology-pill-btn:hover {
  background: #fef3c7;
  border-color: #f59e0b;
  transform: translateY(-1px);
}

.heading-sub {
  font-size: 0.88rem;
  color: #64748b;
  margin: 0.25rem 0 0 0;
}
</style>
