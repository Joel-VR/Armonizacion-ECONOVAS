<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import {
  Calendar,
  Flame,
  TrendingUp,
  AlertTriangle,
  Download,
  ArrowRight,
  Info,
  Layers,
} from '@lucide/vue'
import {
  type BurnCalendarData,
  type MonthCalendarCell,
  type Analysis,
  percent,
} from '../huanuco'

const props = defineProps<{
  departmentCode: string
  selectedYear: number
  analysis: Analysis | null
}>()

const emit = defineEmits<{
  'update:year': [year: number]
  'navigate-to-map': [payload: { year: number; month: number }]
}>()

const activeTab = ref<'matrix' | 'weekly'>('matrix')
const eraFilter = ref<'all' | '2020s' | '2010s' | '2000s'>('all')
const calendarData = ref<BurnCalendarData | null>(null)
const loading = ref(true)
const error = ref('')

const selectedCell = ref<MonthCalendarCell | null>(null)

const visibleYears = computed(() => {
  const yrs = calendarData.value?.years.slice().reverse() || []
  if (eraFilter.value === '2020s') return yrs.filter((y) => y >= 2020)
  if (eraFilter.value === '2010s') return yrs.filter((y) => y >= 2010 && y <= 2019)
  if (eraFilter.value === '2000s') return yrs.filter((y) => y < 2010)
  return yrs
})

async function fetchCalendar() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/departments/${props.departmentCode}/calendar`)
    if (!res.ok) throw new Error('No se pudo obtener el calendario de quemas.')
    const data: BurnCalendarData = await res.json()
    calendarData.value = data
    // Auto-select latest active month
    const yr = String(props.selectedYear)
    if (data.matrix[yr]) {
      const activeMonth = data.matrix[yr].find((c) => c.month === 8) || data.matrix[yr][0]
      selectedCell.value = activeMonth
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Error al cargar calendario'
  } finally {
    loading.value = false
  }
}

watch(() => props.departmentCode, () => fetchCalendar(), { immediate: true })

watch(() => props.selectedYear, (yr) => {
  if (calendarData.value?.matrix[String(yr)]) {
    const prevMonth = selectedCell.value?.month || 8
    selectedCell.value = calendarData.value.matrix[String(yr)].find((c) => c.month === prevMonth) || calendarData.value.matrix[String(yr)][0]
  }
})

// Accessible Color Scale (Green -> Lime -> Amber -> Orange -> Crimson)
function getCellBg(cell: MonthCalendarCell): string {
  const val = cell.harmonized_index
  if (val === null) return '#f1f5f9'
  if (val === 0) return '#f8fafc'
  if (val < 0.20) return '#4c9f69' // Cool Forest Green
  if (val < 0.40) return '#84cc16' // Lime
  if (val < 0.60) return '#eab308' // Amber / Warm Yellow
  if (val < 0.80) return '#f97316' // Vibrant Orange
  return '#dc2626' // Deep Crimson / Extreme
}

function getCellTextColor(cell: MonthCalendarCell): string {
  const val = cell.harmonized_index
  if (val === null) return '#94a3b8'
  if (val < 0.40) return '#ffffff'
  if (val < 0.60) return '#0f172a'
  return '#ffffff'
}

function selectCell(cell: MonthCalendarCell) {
  selectedCell.value = cell
  emit('update:year', cell.year)
}

function goToMap() {
  if (!selectedCell.value) return
  emit('navigate-to-map', {
    year: selectedCell.value.year,
    month: selectedCell.value.month,
  })
}

function downloadCalendarCSV() {
  window.open(`/api/departments/${props.departmentCode}/calendar/export.csv`, '_blank')
}
</script>

<template>
  <div class="calendar-page-shell">
    <!-- Top KPI Cards -->
    <div class="kpi-banner">
      <article class="surface kpi-card">
        <div class="kpi-icon-box text-orange"><Flame :size="22" /></div>
        <div>
          <small>Temporada Crítica Principal</small>
          <strong>Julio – Octubre</strong>
          <span class="subtext">Concentra el 70%+ de quemas en el año</span>
        </div>
      </article>

      <article class="surface kpi-card">
        <div class="kpi-icon-box text-red"><TrendingUp :size="22" /></div>
        <div>
          <small>Récord Histórico Registrado</small>
          <strong v-if="calendarData?.highest_month">
            {{ calendarData.highest_month.month_name }} {{ calendarData.highest_month.year }}
          </strong>
          <strong v-else>—</strong>
          <span class="subtext" v-if="calendarData?.highest_month">
            Índice {{ Math.round((calendarData.highest_month.value || 0) * 100) }}% ({{ calendarData.highest_month.anomaly_pct > 0 ? '+' : '' }}{{ calendarData.highest_month.anomaly_pct }}% vs mediana)
          </span>
        </div>
      </article>

      <article class="surface kpi-card">
        <div class="kpi-icon-box text-amber"><AlertTriangle :size="22" /></div>
        <div>
          <small>Anomalías Críticas Registradas</small>
          <strong>{{ calendarData?.critical_count ?? 0 }} meses</strong>
          <span class="subtext">Superan en +65% la mediana histórica</span>
        </div>
      </article>

      <article class="surface kpi-card action-card">
        <button class="primary-download-btn" @click="downloadCalendarCSV" title="Descargar matriz en CSV">
          <Download :size="18" />
          <span>Exportar Calendario (CSV)</span>
        </button>
        <span class="subtext">Datos armonizados 2000–2026 (27 años)</span>
      </article>
    </div>

    <!-- Main Content Workspace -->
    <div class="calendar-workspace">
      <!-- Left: Heatmap Matrix -->
      <section class="surface matrix-container">
        <div class="matrix-header">
          <div>
            <span class="eyebrow"><Calendar :size="14" /> CALENDARIO DE ACTIVIDAD DE FUEGO</span>
            <h2>Matriz Multianual de Quemas e Incendios (2000–2026)</h2>
            <p>
              Índice Armonizado continuo: Integra más de dos décadas de observaciones satelitales NASA (MODIS 2000+ y VIIRS 2012+).
            </p>
          </div>

          <!-- Tab Selector -->
          <div class="view-mode">
            <button :class="{ active: activeTab === 'matrix' }" @click="activeTab = 'matrix'">
              Matriz 2000–2026
            </button>
            <button :class="{ active: activeTab === 'weekly' }" @click="activeTab = 'weekly'">
              Desglose Semanal
            </button>
          </div>
        </div>

        <!-- Era Filter Pills -->
        <div v-if="activeTab === 'matrix'" class="era-filter-bar">
          <span class="filter-label">Época Satelital:</span>
          <div class="era-pills">
            <button :class="{ active: eraFilter === 'all' }" @click="eraFilter = 'all'">
              Todo el Registro (2000–2026 · 27 años)
            </button>
            <button :class="{ active: eraFilter === '2020s' }" @click="eraFilter = '2020s'">
              2020s (Actual)
            </button>
            <button :class="{ active: eraFilter === '2010s' }" @click="eraFilter = '2010s'">
              2010s (Dual MODIS+VIIRS)
            </button>
            <button :class="{ active: eraFilter === '2000s' }" @click="eraFilter = '2000s'">
              2000s (MODIS Inicial)
            </button>
          </div>
        </div>

        <div v-if="loading" class="loading-state">
          <p>Consultando registros armonizados del departamento…</p>
        </div>

        <div v-else-if="error" class="error-state" role="alert">
          <AlertTriangle :size="20" />
          <p>{{ error }}</p>
        </div>

        <!-- MATRIX VIEW -->
        <div v-else-if="activeTab === 'matrix'" class="heatmap-table-wrap">
          <table class="heatmap-table">
            <thead>
              <tr>
                <th class="sticky-col">Año · Sensor</th>
                <th v-for="m in calendarData?.months" :key="m.month" :class="{ 'peak-header': m.month >= 7 && m.month <= 10 }">
                  {{ m.short }}
                </th>
                <th>Total Anual</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="yr in visibleYears"
                :key="yr"
                :class="{ 'current-row': yr === selectedYear }"
              >
                <th class="sticky-col year-label">
                  <span>{{ yr }}</span>
                  <small v-if="yr < 2012" class="era-tag era-modis" title="Solo observaciones MODIS (Terra/Aqua)">MODIS</small>
                  <small v-else-if="yr <= 2024" class="era-tag era-dual" title="Observaciones duales MODIS + VIIRS (Periodo de referencia)">Dual</small>
                  <small v-else class="era-tag era-viirs" title="VIIRS como sensor primario">VIIRS</small>
                </th>
                <td
                  v-for="cell in calendarData?.matrix[String(yr)]"
                  :key="cell.month"
                  class="heatmap-cell"
                  :class="{
                    'cell-selected': selectedCell?.year === cell.year && selectedCell?.month === cell.month,
                    'is-anomalous': cell.anomaly_status === 'critical' || cell.is_unusual_timing
                  }"
                  :style="{ backgroundColor: getCellBg(cell), color: getCellTextColor(cell) }"
                  @click="selectCell(cell)"
                  :title="`${cell.month_name} ${cell.year}: Índice ${percent(cell.harmonized_index)} | Mediana: ${percent(cell.historical_median)} | Anomalía: ${cell.anomaly_pct ? (cell.anomaly_pct > 0 ? '+' : '') + cell.anomaly_pct + '%' : '—'}`"
                >
                  <span class="cell-val">{{ percent(cell.harmonized_index) }}</span>
                  <span v-if="cell.anomaly_status === 'critical'" class="anomaly-dot" title="Anomalía crítica"></span>
                  <span v-else-if="cell.is_unusual_timing" class="unusual-dot" title="Actividad inusualmente temprana/tardía"></span>
                </td>
                <td class="year-summary-cell">
                  <strong>
                    {{
                      Math.round(
                        (calendarData?.matrix[String(yr)].reduce((acc, c) => acc + (c.harmonized_index || 0), 0) || 0) /
                        (calendarData?.matrix[String(yr)].filter((c) => c.harmonized_index !== null).length || 1) * 100
                      )
                    }}%
                  </strong>
                </td>
              </tr>
            </tbody>

            <!-- Reference Baselines Footer -->
            <tfoot>
              <tr class="baseline-row">
                <th class="sticky-col">
                  <span>Mediana Histórica</span>
                  <small>(2016–2024)</small>
                </th>
                <td v-for="m in calendarData?.months" :key="'med-' + m.month" class="baseline-val-cell">
                  {{ percent(m.baseline.median) }}
                </td>
                <td>—</td>
              </tr>
              <tr class="baseline-row threshold-row">
                <th class="sticky-col">
                  <span>Umbral Crítico (P75)</span>
                  <small>Alerta 25% superior</small>
                </th>
                <td v-for="m in calendarData?.months" :key="'p75-' + m.month" class="threshold-val-cell">
                  {{ percent(m.baseline.p75) }}
                </td>
                <td>—</td>
              </tr>
            </tfoot>
          </table>

          <!-- Heatmap Legend -->
          <div class="heatmap-legend">
            <span class="legend-title">Escala de Actividad:</span>
            <div class="legend-scale">
              <span class="legend-item"><i style="background: #4c9f69"></i> &lt;20% Baja</span>
              <span class="legend-item"><i style="background: #84cc16"></i> 20–40% Moderada</span>
              <span class="legend-item"><i style="background: #eab308"></i> 40–60% Típica Seca</span>
              <span class="legend-item"><i style="background: #f97316"></i> 60–80% Elevada</span>
              <span class="legend-item"><i style="background: #dc2626"></i> ≥80% Crítica / Extrema</span>
            </div>
            <div class="legend-indicators">
              <span><i class="dot-red"></i> Anomalía Crítica (+65% vs mediana)</span>
              <span><i class="dot-amber"></i> Fuera de Temporada Habitual</span>
            </div>
          </div>
        </div>

        <!-- WEEKLY BREAKDOWN VIEW -->
        <div v-else-if="activeTab === 'weekly'" class="weekly-breakdown-wrap">
          <div class="weekly-controls">
            <label>
              Año:
              <select :value="selectedYear" @change="emit('update:year', Number(($event.target as HTMLSelectElement).value))">
                <option v-for="y in calendarData?.years.slice().reverse()" :key="y" :value="y">{{ y }}</option>
              </select>
            </label>
            <span class="inline-note">Mostrando semanas ISO del año {{ selectedYear }} en {{ calendarData?.department.name }}.</span>
          </div>

          <!-- Banner explicativo para la Era Pre-VIIRS -->
          <div v-if="selectedYear < 2012" class="pre-viirs-banner">
            <Info :size="16" class="pre-viirs-icon" />
            <div>
              <strong>Era Pre-VIIRS ({{ selectedYear }}):</strong>
              El sensor VIIRS (375 m) inició transmisiones en 2012. Para los años 2000–2011, el monitoreo satelital operaba exclusivamente con el sensor <strong>MODIS (Terra y Aqua a 1 km)</strong>.
            </div>
          </div>

          <div v-if="!analysis?.weekly.length" class="empty-state">
            <p>No se encontraron datos semanales disponibles para {{ selectedYear }}.</p>
          </div>

          <table v-else class="weekly-table">
            <thead>
              <tr>
                <th>Semana</th>
                <th>Periodo (UTC)</th>
                <th>Celdas MODIS</th>
                <th>Celdas VIIRS</th>
                <th>Índice Combinado</th>
                <th>Diferencia Sensores</th>
                <th>Diagnóstico</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="w in analysis.weekly" :key="w.start" :class="{ 'peak-week': (w.combined || 0) >= 0.7 }">
                <td>Semana {{ w.week }}</td>
                <td>{{ w.start }} a {{ w.end }}</td>
                <td>{{ w.sensors.MODIS.cells ?? '—' }}</td>
                <td>{{ w.sensors.VIIRS.cells ?? '—' }}</td>
                <td>
                  <strong :style="{ color: (w.combined || 0) >= 0.75 ? '#dc2626' : (w.combined || 0) >= 0.5 ? '#f97316' : '#4c9f69' }">
                    {{ percent(w.combined) }}
                  </strong>
                </td>
                <td>{{ percent(w.disagreement) }}</td>
                <td>
                  <span v-if="(w.combined || 0) >= 0.75" class="badge badge-red">Crítico</span>
                  <span v-else-if="(w.combined || 0) >= 0.45" class="badge badge-amber">Elevado</span>
                  <span v-else-if="w.combined !== null" class="badge badge-green">Normal</span>
                  <span
                    v-else-if="w.sensors.MODIS.cells !== null && w.sensors.VIIRS.cells !== null"
                    class="badge badge-blue"
                    title="Actividad basal típica de temporada de lluvias con empates en cero en la serie histórica (metodología NASA)"
                  >
                    Actividad basal
                  </span>
                  <span
                    v-else-if="w.sensors.MODIS.cells !== null && w.sensors.VIIRS.cells === null"
                    class="badge badge-purple"
                    :title="w.sensors.MODIS.cells > 0 ? `MODIS registró ${w.sensors.MODIS.cells} celdas activas (VIIRS aún no operaba en ${selectedYear})` : `Actividad basal en MODIS (VIIRS aún no operaba en ${selectedYear})`"
                  >
                    {{ w.sensors.MODIS.cells > 0 ? 'Solo MODIS (' + w.sensors.MODIS.cells + ')' : 'Basal (MODIS)' }}
                  </span>
                  <span v-else class="badge badge-gray">Sin datos</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Right: Detailed Period Inspector -->
      <aside class="surface detail-drawer" v-if="selectedCell">
        <div class="drawer-header">
          <span class="eyebrow"><Layers :size="14" /> DIAGNÓSTICO DEL PERIODO</span>
          <h3>{{ selectedCell.month_name }} {{ selectedCell.year }}</h3>
          <p class="dep-tag">{{ calendarData?.department.name }} · {{ selectedCell.is_baseline_year ? 'Año de Referencia' : 'Año Evaluado' }}</p>
        </div>

        <div class="drawer-metrics">
          <!-- Main Index Card -->
          <div class="metric-highlight" :style="{ borderColor: getCellBg(selectedCell) }">
            <span class="metric-label">Índice de Fuego Armonizado</span>
            <div class="metric-value-row">
              <span class="huge-metric" :style="{ color: getCellBg(selectedCell) }">
                {{ percent(selectedCell.harmonized_index) }}
              </span>
              <span
                class="status-pill"
                :class="{
                  'pill-critical': selectedCell.anomaly_status === 'critical',
                  'pill-elevated': selectedCell.anomaly_status === 'elevated',
                  'pill-normal': selectedCell.anomaly_status === 'normal',
                  'pill-low': selectedCell.anomaly_status === 'unusually_low'
                }"
              >
                {{
                  selectedCell.anomaly_status === 'critical' ? 'Crítico / Extremo' :
                  selectedCell.anomaly_status === 'elevated' ? 'Sobre lo Habitual' :
                  selectedCell.anomaly_status === 'unusually_low' ? 'Bajo lo Habitual' : 'Dentro del Rango Normal'
                }}
              </span>
            </div>
            <p class="metric-subtext">
              Promedio ponderado de las cuadrículas de 5 km en semanas de este mes.
            </p>
          </div>

          <!-- Comparison to Historical Baseline -->
          <div class="stats-box">
            <h4>Comparación vs Mediana Histórica</h4>
            <div class="comparison-row">
              <span>Mediana 2016–2024:</span>
              <strong>{{ percent(selectedCell.historical_median) }}</strong>
            </div>
            <div class="comparison-row">
              <span>Rango Normal (P25 - P75):</span>
              <span>{{ percent(selectedCell.baseline_p25 ?? null) }} – {{ percent(selectedCell.baseline_p75 ?? null) }}</span>
            </div>
            <div class="comparison-row highlight-row">
              <span>Desviación / Anomalía:</span>
              <strong :style="{ color: (selectedCell.anomaly_pct || 0) > 30 ? '#dc2626' : '#0284c7' }">
                {{ selectedCell.anomaly_pct !== null ? (selectedCell.anomaly_pct > 0 ? '+' : '') + selectedCell.anomaly_pct + '%' : '—' }}
              </strong>
            </div>
          </div>

          <!-- Raw Sensor Footprint Breakdown -->
          <div class="stats-box">
            <h4>Celdas-Día Detectadas por Sensor</h4>
            <div class="sensor-row">
              <span class="sensor-badge modis-badge">MODIS (1 km)</span>
              <strong>{{ selectedCell.modis_cells.toLocaleString('es-PE') }} celdas</strong>
            </div>
            <div class="sensor-row">
              <span class="sensor-badge viirs-badge">VIIRS Suomi (375 m)</span>
              <strong v-if="selectedCell.year < 2012" class="text-muted" title="Sensor no lanzado en este año (inició transmisiones en 2012)">
                No disponible (inició 2012)
              </strong>
              <strong v-else>{{ selectedCell.viirs_cells.toLocaleString('es-PE') }} celdas</strong>
            </div>
            <p class="sensor-disclaimer" v-if="selectedCell.year < 2012">
              <Info :size="13" /> Entre 2000 y 2011 (era Pre-VIIRS), la detección operaba exclusivamente con el sensor MODIS. VIIRS inició sus transmisiones en 2012.
            </p>
            <p class="sensor-disclaimer" v-else>
              <Info :size="13" /> VIIRS detecta fuegos de menor escala y quemas frías debido a su mayor resolución espacial (375 m vs 1 km). La armonización nivela este sesgo.
            </p>
          </div>

          <!-- Temporal Anomaly Alert -->
          <div v-if="selectedCell.is_unusual_timing" class="alert-box">
            <AlertTriangle :size="18" />
            <div>
              <strong>Alerta de Quema Fuera de Temporada</strong>
              <p>Este mes se encuentra fuera del periodo seco regular (Julio–Octubre) pero presentó una actividad superior al umbral de base.</p>
            </div>
          </div>
        </div>

        <!-- Action Button -->
        <div class="drawer-actions">
          <button class="primary-action-btn" @click="goToMap">
            <span>Ver Focos en el Mapa</span>
            <ArrowRight :size="18" />
          </button>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.calendar-page-shell {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 1.25rem 1.75rem;
  max-width: 1600px;
  margin: 0 auto;
  width: 100%;
}

/* KPI Banner */
.kpi-banner {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1rem;
}
.kpi-card {
  padding: 1rem 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
}
.kpi-icon-box {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8fafc;
}
.text-orange { color: #f97316; background: #fff7ed; }
.text-red { color: #dc2626; background: #fef2f2; }
.text-amber { color: #d97706; background: #fffbeb; }

.kpi-card small {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  color: #64748b;
  letter-spacing: 0.04em;
}
.kpi-card strong {
  display: block;
  font-size: 1.15rem;
  font-weight: 800;
  color: #0f172a;
}
.kpi-card .subtext {
  font-size: 0.78rem;
  color: #64748b;
}

.action-card {
  flex-direction: column;
  justify-content: center;
  align-items: stretch;
  gap: 0.4rem;
}
.primary-download-btn {
  background: #b81d24;
  color: #fff;
  border: none;
  padding: 0.6rem 1rem;
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.88rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  cursor: pointer;
  transition: background 0.15s ease;
}
.primary-download-btn:hover {
  background: #991b1b;
}

/* Main Workspace */
.calendar-workspace {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 1.25rem;
  align-items: start;
}
@media (max-width: 1100px) {
  .calendar-workspace {
    grid-template-columns: 1fr;
  }
}

.matrix-container {
  padding: 1.5rem;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  overflow-x: auto;
}
.matrix-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 1.25rem;
  gap: 1rem;
  flex-wrap: wrap;
}
.matrix-header .eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.72rem;
  font-weight: 700;
  color: #c2410c;
  text-transform: uppercase;
  margin-bottom: 0.25rem;
}
.matrix-header h2 {
  font-size: 1.4rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0 0 0.25rem 0;
}
.matrix-header p {
  font-size: 0.88rem;
  color: #64748b;
  margin: 0;
}

/* View Mode Buttons */
.view-mode {
  display: inline-flex;
  padding: 0.25rem;
  background: #f1f5f9;
  border-radius: 8px;
  gap: 0.25rem;
}
.view-mode button {
  padding: 0.4rem 0.85rem;
  border: none;
  background: transparent;
  font-size: 0.82rem;
  font-weight: 700;
  color: #64748b;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.view-mode button.active {
  background: #ffffff;
  color: #0f172a;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* Era Filter Bar */
.era-filter-bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
  font-size: 0.82rem;
}
.filter-label {
  font-weight: 700;
  color: #475569;
}
.era-pills {
  display: inline-flex;
  gap: 0.35rem;
  background: #f1f5f9;
  padding: 0.2rem;
  border-radius: 6px;
  flex-wrap: wrap;
}
.era-pills button {
  padding: 0.25rem 0.65rem;
  border: none;
  background: transparent;
  font-size: 0.76rem;
  font-weight: 700;
  color: #64748b;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.era-pills button.active {
  background: #ffffff;
  color: #0f172a;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
}
.era-tag {
  font-size: 0.65rem;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  font-weight: 700;
  text-transform: uppercase;
}
.era-modis { background: #fef9c3; color: #854d0e; }
.era-dual { background: #dbeafe; color: #1e40af; }
.era-viirs { background: #fee2e2; color: #991b1b; }

/* Heatmap Table */
.heatmap-table-wrap {
  overflow-x: auto;
}
.heatmap-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 4px;
  font-size: 0.82rem;
}
.heatmap-table th {
  padding: 0.5rem 0.4rem;
  text-align: center;
  font-weight: 700;
  color: #64748b;
  font-size: 0.8rem;
}
.heatmap-table .peak-header {
  color: #ea580c;
  background: #fff7ed;
  border-radius: 4px;
}
.sticky-col {
  text-align: left;
  min-width: 80px;
}
.year-label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-weight: 800;
  color: #0f172a;
  font-size: 0.92rem;
}
.baseline-tag {
  background: #e2e8f0;
  color: #475569;
  font-size: 0.65rem;
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
  font-weight: 600;
}

.heatmap-cell {
  position: relative;
  text-align: center;
  padding: 0.65rem 0.25rem;
  border-radius: 6px;
  cursor: pointer;
  transition: transform 0.1s ease, box-shadow 0.1s ease;
  min-width: 52px;
  font-weight: 700;
  user-select: none;
}
.heatmap-cell:hover {
  transform: scale(1.08);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.15);
  z-index: 5;
}
.cell-selected {
  outline: 3px solid #0284c7;
  outline-offset: 1px;
  transform: scale(1.05);
  z-index: 6;
}
.cell-val {
  font-size: 0.82rem;
}
.anomaly-dot {
  position: absolute;
  top: 3px;
  right: 3px;
  width: 7px;
  height: 7px;
  background: #ffffff;
  border: 1px solid #7f1d1d;
  border-radius: 50%;
}
.unusual-dot {
  position: absolute;
  top: 3px;
  right: 3px;
  width: 7px;
  height: 7px;
  background: #fbbf24;
  border: 1px solid #78350f;
  border-radius: 50%;
}

.year-summary-cell {
  text-align: center;
  font-weight: 800;
  background: #f8fafc;
  border-radius: 6px;
  color: #334155;
}

/* Baselines Table Rows */
.baseline-row th {
  border-top: 2px solid #e2e8f0;
  padding-top: 0.75rem;
}
.baseline-row td {
  border-top: 2px solid #e2e8f0;
  padding: 0.5rem 0.25rem;
  text-align: center;
  font-weight: 700;
}
.baseline-val-cell {
  background: #f8fafc;
  border-radius: 4px;
  color: #0f172a;
}
.threshold-val-cell {
  background: #fef2f2;
  border-radius: 4px;
  color: #dc2626;
}

/* Legend */
.heatmap-legend {
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1rem;
  font-size: 0.8rem;
  color: #475569;
}
.legend-scale {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}
.legend-item i {
  width: 14px;
  height: 14px;
  border-radius: 3px;
  display: inline-block;
}
.legend-indicators {
  display: flex;
  gap: 1rem;
}
.legend-indicators span {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}
.dot-red {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #dc2626;
  display: inline-block;
}
.dot-amber {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f59e0b;
  display: inline-block;
}

/* Weekly Table */
.weekly-breakdown-wrap {
  margin-top: 1rem;
}
.weekly-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
  font-size: 0.88rem;
}
.weekly-controls select {
  padding: 0.35rem 0.65rem;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  font-weight: 700;
}
.weekly-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
.weekly-table th, .weekly-table td {
  padding: 0.65rem 0.75rem;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
}
.badge {
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
}
.badge-red { background: #fee2e2; color: #b91c1c; }
.badge-amber { background: #fef3c7; color: #b45309; }
.badge-green { background: #dcfce7; color: #15803d; }
.badge-blue { background: #e0f2fe; color: #0369a1; }
.badge-purple { background: #f3e8ff; color: #7e22ce; }
.badge-gray { background: #f1f5f9; color: #64748b; }

.pre-viirs-banner {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-left: 4px solid #6366f1;
  border-radius: 8px;
  padding: 0.6rem 0.85rem;
  margin-bottom: 0.9rem;
  font-size: 0.78rem;
  color: #334155;
  line-height: 1.4;
}

.pre-viirs-icon {
  color: #6366f1;
  flex-shrink: 0;
}

.text-muted {
  font-size: 0.75rem;
  color: #94a3b8;
  font-weight: 600;
}

/* Detail Drawer */
.detail-drawer {
  padding: 1.25rem;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}
.drawer-header .eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.72rem;
  font-weight: 700;
  color: #c2410c;
  text-transform: uppercase;
  margin-bottom: 0.25rem;
}
.drawer-header h3 {
  font-size: 1.3rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
}
.dep-tag {
  font-size: 0.82rem;
  color: #64748b;
  margin: 0.2rem 0 0 0;
}

.drawer-metrics {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.metric-highlight {
  background: #f8fafc;
  border-left: 4px solid #c2410c;
  padding: 0.85rem 1rem;
  border-radius: 0 8px 8px 0;
}
.metric-label {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  color: #64748b;
  display: block;
}
.metric-value-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin: 0.35rem 0;
}
.huge-metric {
  font-size: 2.2rem;
  font-weight: 900;
  line-height: 1;
}
.status-pill {
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.25rem 0.65rem;
  border-radius: 9999px;
}
.pill-critical { background: #fee2e2; color: #b91c1c; }
.pill-elevated { background: #fff7ed; color: #c2410c; }
.pill-normal { background: #dcfce7; color: #166534; }
.pill-low { background: #e0f2fe; color: #075985; }

.metric-subtext {
  font-size: 0.78rem;
  color: #64748b;
  margin: 0;
}

.stats-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.85rem 1rem;
}
.stats-box h4 {
  font-size: 0.82rem;
  font-weight: 700;
  color: #334155;
  margin: 0 0 0.65rem 0;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}
.comparison-row, .sensor-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.84rem;
  padding: 0.3rem 0;
}
.highlight-row {
  border-top: 1px dashed #cbd5e1;
  margin-top: 0.35rem;
  padding-top: 0.5rem;
}
.sensor-badge {
  font-size: 0.72rem;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font-weight: 700;
}
.modis-badge { background: #fef9c3; color: #854d0e; }
.viirs-badge { background: #fee2e2; color: #991b1b; }
.sensor-disclaimer {
  font-size: 0.74rem;
  color: #64748b;
  margin: 0.5rem 0 0 0;
  display: flex;
  align-items: flex-start;
  gap: 0.35rem;
  line-height: 1.4;
}

.alert-box {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  padding: 0.75rem;
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  color: #92400e;
  font-size: 0.82rem;
}
.alert-box strong {
  display: block;
  font-weight: 700;
  margin-bottom: 0.2rem;
}
.alert-box p {
  margin: 0;
  line-height: 1.4;
}

.drawer-actions {
  margin-top: auto;
}
.primary-action-btn {
  width: 100%;
  background: #0f172a;
  color: #ffffff;
  border: none;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.88rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  cursor: pointer;
  transition: background 0.15s ease;
}
.primary-action-btn:hover {
  background: #1e293b;
}

.loading-state, .error-state, .empty-state {
  padding: 3rem 1rem;
  text-align: center;
  color: #64748b;
}
.error-state {
  color: #dc2626;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}
</style>
