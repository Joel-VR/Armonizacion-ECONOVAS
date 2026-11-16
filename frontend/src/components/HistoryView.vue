<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { apiUrl } from '../api'
import { language, tr } from '../language'
import { use, init, type EChartsType } from 'echarts/core'
import { LineChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, MarkAreaComponent, MarkLineComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import {
  TrendingUp,
  Download,
  Info,
  Scale,
  Calendar,
  AlertTriangle,
  CheckCircle2,
} from '@lucide/vue'
import { type Analysis, type BurnCalendarData, percent } from '../huanuco'

use([LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, MarkAreaComponent, MarkLineComponent, CanvasRenderer])

const props = defineProps<{
  analysis: Analysis | null
  departmentCode: string
  year: number
}>()

const emit = defineEmits<{
  'update:year': [year: number]
}>()

const chartMode = ref<'harmonized' | 'sensors' | 'anomaly'>('harmonized')
const chartElement = ref<HTMLDivElement>()
let chart: EChartsType | undefined
let resizeObserver: ResizeObserver | undefined

const calendarData = ref<BurnCalendarData | null>(null)
const loadingCal = ref(false)

async function fetchCalendar() {
  loadingCal.value = true
  try {
    const res = await fetch(apiUrl(`/api/departments/${props.departmentCode}/calendar`))
    if (res.ok) calendarData.value = await res.json()
  } catch {
    // fallback
  } finally {
    loadingCal.value = false
  }
}

watch(() => props.departmentCode, () => fetchCalendar(), { immediate: true })

const weeks = computed(() => {
  return props.analysis?.year === props.year ? props.analysis.weekly : []
})

// Metrics summary for selected year
const yearStats = computed(() => {
  const items = weeks.value
  if (!items.length) return { avgIndex: null, criticalWeeks: 0, agreement: null, totalModis: 0, totalViirs: 0 }
  const valid = items.filter(w => w.combined !== null)
  const avg = valid.length ? valid.reduce((acc, w) => acc + (w.combined || 0), 0) / valid.length : null
  const critical = items.filter(w => (w.combined || 0) >= 0.75).length
  const agreements = items.filter(w => w.disagreement !== null).map(w => 1 - (w.disagreement || 0))
  const avgAgr = agreements.length ? agreements.reduce((a, b) => a + b, 0) / agreements.length : null
  const totalM = items.reduce((acc, w) => acc + (w.sensors.MODIS.cells || 0), 0)
  const totalV = items.reduce((acc, w) => acc + (w.sensors.VIIRS.cells || 0), 0)
  return {
    avgIndex: avg,
    criticalWeeks: critical,
    agreement: avgAgr,
    totalModis: totalM,
    totalViirs: totalV
  }
})

function drawChart() {
  if (!chartElement.value || !chart) return

  const items = weeks.value
  const labels = items.map(w => `${tr('Sem', 'Wk')} ${w.week}`)

  // Monthly historical median approximated to weekly timeline
  const monthlyMedians = calendarData.value?.months || []
  const getBaselineForWeek = (weekNum: number) => {
    // Approx map week 1..52 to month 1..12
    const mIdx = Math.min(12, Math.max(1, Math.round(weekNum / 4.33)))
    const base = monthlyMedians.find(m => m.month === mIdx)?.baseline
    return {
      median: base?.median ?? 0.25,
      p25: base?.p25 ?? 0.15,
      p75: base?.p75 ?? 0.45
    }
  }

  const baselineMedians = items.map(w => getBaselineForWeek(w.week).median * 100)
  const baselineP25 = items.map(w => getBaselineForWeek(w.week).p25 * 100)
  const baselineP75 = items.map(w => getBaselineForWeek(w.week).p75 * 100)

  if (chartMode.value === 'harmonized') {
    // UNIFIED HARMONIZED CURVE VS HISTORICAL BASELINE
    const harmonizedData = items.map(w => w.combined !== null ? Math.round(w.combined * 100) : null)

    chart.setOption({
      textStyle: { fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" },
      animation: false,
      tooltip: {
        trigger: 'axis',
        formatter: (params: any[]) => {
          const idx = params[0]?.dataIndex
          const item = items[idx]
          if (!item) return ''
          let html = `<div style="font-size:12px;font-weight:700;margin-bottom:4px;">${tr('Semana', 'Week')} ${item.week} (${item.start} – ${item.end})</div>`
          params.forEach(p => {
            if (p.value !== undefined && p.value !== null) {
              html += `<div style="display:flex;justify-content:space-between;gap:12px;color:${p.color};font-size:11px;">
                <span>${p.seriesName}:</span><strong>${Math.round(p.value)}%</strong>
              </div>`
            }
          })
          return html
        }
      },
      legend: {
        top: 8,
        data: [tr('Índice Armonizado (Año Actual)', 'Harmonized index (current year)'), tr('Mediana Histórica (2016–2024)', 'Historical median (2016–2024)'), tr('Banda Normal (P25 - P75)', 'Normal band (P25 - P75)')]
      },
      grid: { top: 50, left: 55, right: 30, bottom: 40 },
      xAxis: {
        type: 'category',
        data: labels,
        axisLine: { lineStyle: { color: '#cbd5e1' } },
        axisLabel: { color: '#64748b', fontSize: 10, interval: 3 }
      },
      yAxis: {
        type: 'value',
        name: tr('Índice de Actividad (%)', 'Activity index (%)'),
        max: 100,
        min: 0,
        axisLabel: { formatter: '{value}%', color: '#64748b' },
        splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } }
      },
      series: [
        {
          name: tr('Banda Normal (P25 - P75)', 'Normal band (P25 - P75)'),
          type: 'line',
          data: baselineP75,
          lineStyle: { opacity: 0 },
          stack: 'confidence-band',
          symbol: 'none'
        },
        {
          name: tr('Banda Normal (P25 - P75)', 'Normal band (P25 - P75)'),
          type: 'line',
          data: baselineP75.map((v, i) => Math.max(0, v - baselineP25[i])),
          lineStyle: { opacity: 0 },
          areaStyle: { color: 'rgba(234, 179, 8, 0.15)' },
          stack: 'confidence-band',
          symbol: 'none'
        },
        {
          name: tr('Mediana Histórica (2016–2024)', 'Historical median (2016–2024)'),
          type: 'line',
          data: baselineMedians,
          lineStyle: { color: '#94a3b8', width: 2, type: 'dashed' },
          itemStyle: { color: '#94a3b8' },
          symbol: 'none'
        },
        {
          name: tr('Índice Armonizado (Año Actual)', 'Harmonized index (current year)'),
          type: 'line',
          data: harmonizedData,
          smooth: true,
          lineStyle: { color: '#dc2626', width: 3 },
          itemStyle: { color: '#dc2626' },
          symbolSize: 6,
          markArea: {
            itemStyle: { color: 'rgba(220, 38, 38, 0.06)' },
            data: [
              [
                { name: tr('Temporada Crítica Habitual', 'Usual critical season'), xAxis: `${tr('Sem', 'Wk')} 27` },
                { xAxis: `${tr('Sem', 'Wk')} 43` }
              ]
            ]
          }
        }
      ]
    }, true)
  } else if (chartMode.value === 'sensors') {
    // RAW SENSOR DISCREPANCY COMPARISON
    const modisData = items.map(w => w.sensors.MODIS.cells ?? 0)
    const viirsData = items.map(w => w.sensors.VIIRS.cells ?? 0)

    chart.setOption({
      textStyle: { fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" },
      animation: false,
      tooltip: { trigger: 'axis' },
      legend: { top: 8, data: ['MODIS (Terra/Aqua · 1 km)', 'VIIRS Suomi (375 m)'] },
      grid: { top: 50, left: 60, right: 30, bottom: 40 },
      xAxis: {
        type: 'category',
        data: labels,
        axisLine: { lineStyle: { color: '#cbd5e1' } },
        axisLabel: { color: '#64748b', fontSize: 10, interval: 3 }
      },
      yAxis: {
        type: 'value',
        name: tr('Celdas-Día Detectadas', 'Detected cell-days'),
        axisLabel: { color: '#64748b' },
        splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } }
      },
      series: [
        {
          name: 'MODIS (Terra/Aqua · 1 km)',
          type: 'bar',
          data: modisData,
          itemStyle: { color: '#eab308' },
          barMaxWidth: 16
        },
        {
          name: 'VIIRS Suomi (375 m)',
          type: 'bar',
          data: viirsData,
          itemStyle: { color: '#ef4444' },
          barMaxWidth: 16
        }
      ]
    }, true)
  } else {
    // ANOMALY DEVIATION (% OVER/UNDER MEDIAN)
    const anomalies = items.map(w => {
      if (w.combined === null) return null
      const baseMed = getBaselineForWeek(w.week).median
      const pct = ((w.combined - baseMed) / Math.max(baseMed, 0.05)) * 100
      return Math.round(pct)
    })

    chart.setOption({
      textStyle: { fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" },
      animation: false,
      tooltip: {
        trigger: 'axis',
        formatter: (params: any[]) => {
          const idx = params[0]?.dataIndex
          const item = items[idx]
          const val = anomalies[idx]
          if (val === null) return ''
          return `<strong>${tr('Semana', 'Week')} ${item.week}</strong>: ${tr('Desviación de', 'Deviation of')} ${val > 0 ? '+' : ''}${val}% ${tr('respecto a la mediana histórica', 'from the historical median')}`
        }
      },
      legend: { top: 8, data: [tr('Desviación vs Mediana Histórica (%)', 'Deviation from historical median (%)')] },
      grid: { top: 50, left: 60, right: 30, bottom: 40 },
      xAxis: {
        type: 'category',
        data: labels,
        axisLine: { lineStyle: { color: '#cbd5e1' } },
        axisLabel: { color: '#64748b', fontSize: 10, interval: 3 }
      },
      yAxis: {
        type: 'value',
        name: tr('Desviación (%)', 'Deviation (%)'),
        axisLabel: { formatter: '{value}%', color: '#64748b' },
        splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } }
      },
      series: [
        {
          name: tr('Desviación vs Mediana Histórica (%)', 'Deviation from historical median (%)'),
          type: 'bar',
          data: anomalies.map(val => ({
            value: val,
            itemStyle: {
              color: (val || 0) >= 30 ? '#dc2626' : (val || 0) <= -20 ? '#0284c7' : '#10b981'
            }
          })),
          barMaxWidth: 20
        }
      ]
    }, true)
  }
}

watch([weeks, chartMode, language, () => props.year], async () => {
  await nextTick()
  drawChart()
})

onMounted(() => {
  if (chartElement.value) {
    chart = init(chartElement.value)
    drawChart()
    resizeObserver = new ResizeObserver(() => chart?.resize())
    resizeObserver.observe(chartElement.value)
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  chart?.dispose()
})

function downloadHistoricalCSV() {
  window.open(apiUrl(`/api/departments/${props.departmentCode}/calendar/export.csv`), '_blank')
}
</script>

<template>
  <div class="history-page-shell">
    <!-- Header with Controls -->
    <div class="history-topbar">
      <div>
        <span class="eyebrow"><TrendingUp :size="14" /> {{ tr('ANÁLISIS HISTÓRICO Y TENDENCIAS', 'HISTORICAL ANALYSIS AND TRENDS') }}</span>
        <h2>{{ tr('Trayectoria del Fuego y Detección de Anomalías', 'Fire Trends and Anomaly Detection') }}</h2>
        <p>
          {{ tr('Comparación directa del año', 'Direct comparison of') }} {{ year }} {{ tr('contra la línea base histórica del departamento.', 'against the department’s historical baseline.') }}
        </p>
      </div>

      <div class="topbar-actions">
        <!-- Year Selector -->
        <label class="year-picker">
          {{ tr('Año:', 'Year:') }}
          <select :value="year" @change="emit('update:year', Number(($event.target as HTMLSelectElement).value))">
            <option v-for="y in 27" :key="y" :value="2027 - y">{{ 2027 - y }}</option>
          </select>
          <span class="era-indicator" :class="year < 2012 ? 'ind-modis' : year <= 2024 ? 'ind-dual' : 'ind-viirs'">
            {{ year < 2012 ? tr('Era MODIS', 'MODIS era') : year <= 2024 ? tr('Era Dual MODIS+VIIRS', 'MODIS+VIIRS dual era') : tr('Era VIIRS', 'VIIRS era') }}
          </span>
        </label>

        <!-- Mode Toggle -->
        <div class="view-mode">
          <button :class="{ active: chartMode === 'harmonized' }" @click="chartMode = 'harmonized'">
            {{ tr('Índice Armonizado', 'Harmonized index') }}
          </button>
          <button :class="{ active: chartMode === 'sensors' }" @click="chartMode = 'sensors'">
            MODIS vs VIIRS
          </button>
          <button :class="{ active: chartMode === 'anomaly' }" @click="chartMode = 'anomaly'">
            {{ tr('Anomalías (%)', 'Anomalies (%)') }}
          </button>
        </div>

        <button class="icon-text-btn" @click="downloadHistoricalCSV" :title="tr('Exportar serie a CSV', 'Export series to CSV')">
          <Download :size="16" />
          <span>CSV</span>
        </button>
      </div>
    </div>

    <!-- KPI Summary Row -->
    <div class="history-kpis">
      <article class="surface kpi-box">
        <small>{{ tr('Índice Promedio del Año', 'Average annual index') }}</small>
        <strong>{{ percent(yearStats.avgIndex) }}</strong>
        <span class="subtext">{{ tr('Media sobre las 52 semanas', 'Average over 52 weeks') }}</span>
      </article>

      <article class="surface kpi-box">
        <small>{{ tr('Semanas en Nivel Crítico (≥75%)', 'Weeks at critical level (≥75%)') }}</small>
        <strong :style="{ color: yearStats.criticalWeeks > 0 ? '#dc2626' : '#166534' }">
          {{ yearStats.criticalWeeks }} {{ tr('semanas', 'weeks') }}
        </strong>
        <span class="subtext">{{ tr('Actividad extrema sobre el percentil 75', 'Extreme activity above the 75th percentile') }}</span>
      </article>

      <article class="surface kpi-box">
        <small>{{ tr('Concordancia entre Sensores', 'Sensor agreement') }}</small>
        <strong>{{ percent(yearStats.agreement) }}</strong>
        <span class="subtext">1 - |MODIS% - VIIRS%|</span>
      </article>

      <article class="surface kpi-box">
        <small>{{ tr('Huella de Observaciones en Bruto', 'Raw observation footprint') }}</small>
        <strong>
          {{ yearStats.totalViirs.toLocaleString(language === 'en' ? 'en-US' : 'es-PE') }} VIIRS / {{ yearStats.totalModis.toLocaleString(language === 'en' ? 'en-US' : 'es-PE') }} MODIS
        </strong>
        <span class="subtext">{{ tr('Ratio sensor:', 'Sensor ratio:') }} {{ Math.round((yearStats.totalViirs / Math.max(1, yearStats.totalModis)) * 10) / 10 }}x</span>
      </article>
    </div>

    <!-- Chart Container -->
    <section class="surface chart-container">
      <div class="chart-caption">
        <div v-if="chartMode === 'harmonized'">
          <h3>{{ tr('Serie Armonizada vs Rango de Referencia 2016–2024', 'Harmonized series vs 2016–2024 reference range') }}</h3>
          <p>
            {{ tr(`La línea roja muestra la trayectoria unificada de fuego en ${year}. El área sombreada delimita la banda normal estacional (percentiles 25–75). Superar esta banda indica un comportamiento anómalo.`, `The red line shows the combined fire trend in ${year}. The shaded area marks the normal seasonal band (25th–75th percentiles). Values above it indicate anomalous activity.`) }}
          </p>
        </div>
        <div v-else-if="chartMode === 'sensors'">
          <h3>{{ tr('Comparación de Conteos en Bruto: ¿Por qué es necesaria la armonización?', 'Raw count comparison: Why is harmonization needed?') }}</h3>
          <p>
            {{ tr('VIIRS detecta sistemáticamente 3 a 5 veces más celdas de fuego que MODIS debido a su pixel de 375 m vs 1 km. Sin armonización, las series históricas sufrirían un salto artificial al cambiar de sensor.', 'VIIRS consistently detects three to five times more fire cells than MODIS because its pixels are 375 m rather than 1 km. Without harmonization, historical series would show an artificial jump when sensors change.') }}
          </p>
        </div>
        <div v-else>
          <h3>{{ tr('Porcentaje de Anomalía Semanal Respecto a la Mediana', 'Weekly anomaly percentage relative to the median') }}</h3>
          <p>
            {{ tr('Barras rojas denotan semanas con exceso de fuego (+30% sobre lo habitual); barras verdes o azules denotan semanas dentro o por debajo de la mediana.', 'Red bars indicate weeks with excess fire activity (+30% above normal); green or blue bars indicate weeks at or below the median.') }}
          </p>
        </div>
      </div>

      <div ref="chartElement" class="echarts-stage" />
    </section>

    <!-- Context Insights Banner -->
    <div class="surface insights-panel">
      <div class="insight-header">
        <Scale :size="18" />
        <h4>{{ tr('Interpretación Científica para Gestores y Tomadores de Decisión', 'Scientific interpretation for managers and decision-makers') }}</h4>
      </div>
      <div class="insight-grid">
        <div class="insight-item">
          <strong>{{ tr('1. Relevo de Sensores Garantizado', '1. Sensor continuity') }}</strong>
          <p>{{ tr('Cuando los satélites Terra y Aqua dejen de operar, el índice armonizado continuará funcionando con VIIRS calibrado a la misma escala histórica sin rotura en el registro multianual.', 'When Terra and Aqua stop operating, the harmonized index will continue using VIIRS calibrated to the same historical scale, without a break in the multiyear record.') }}</p>
        </div>
        <div class="insight-item">
          <strong>{{ tr('2. Alerta Temprana en Anomalías', '2. Early anomaly alerts') }}</strong>
          <p>{{ tr('Toda semana con desviación superior a +50% en temporada seca representa un riesgo inminente de propagación descontrolada de incendios forestales en la región.', 'A week with a deviation above +50% during the dry season represents an imminent risk of uncontrolled wildfire spread in the region.') }}</p>
        </div>
        <div class="insight-item">
          <strong>{{ tr('3. Métrica Neutra de Píxel', '3. Pixel-neutral metric') }}</strong>
          <p>{{ tr('El uso de la cuadrícula de 5 km celda-día evita la inflación artificial de conteos por múltiples detecciones de un mismo foco en pasadas adyacentes de VIIRS.', 'The 5 km cell-day grid prevents artificial inflation from multiple detections of the same hotspot on adjacent VIIRS overpasses.') }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.history-page-shell {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 1.25rem 1.75rem;
  max-width: 1600px;
  margin: 0 auto;
  width: 100%;
}

.history-topbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1rem;
}
.history-topbar .eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.72rem;
  font-weight: 700;
  color: #c2410c;
  text-transform: uppercase;
  margin-bottom: 0.25rem;
}
.history-topbar h2 {
  font-size: 1.4rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0 0 0.25rem 0;
}
.history-topbar p {
  font-size: 0.88rem;
  color: #64748b;
  margin: 0;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.year-picker {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  font-weight: 700;
  color: #334155;
}
.year-picker select {
  padding: 0.35rem 0.65rem;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  font-weight: 700;
  background: #ffffff;
}
.era-indicator {
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}
.ind-modis { background: #fef9c3; color: #854d0e; }
.ind-dual { background: #dbeafe; color: #1e40af; }
.ind-viirs { background: #fee2e2; color: #991b1b; }

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

.icon-text-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.45rem 0.85rem;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  color: #334155;
  font-weight: 700;
  font-size: 0.82rem;
  cursor: pointer;
  transition: all 0.15s ease;
}
.icon-text-btn:hover {
  background: #f8fafc;
  border-color: #94a3b8;
}

/* KPIs */
.history-kpis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 1rem;
}
.kpi-box {
  padding: 1rem 1.25rem;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
}
.kpi-box small {
  display: block;
  font-size: 0.74rem;
  font-weight: 600;
  text-transform: uppercase;
  color: #64748b;
  letter-spacing: 0.04em;
}
.kpi-box strong {
  display: block;
  font-size: 1.25rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0.2rem 0;
}
.kpi-box .subtext {
  font-size: 0.78rem;
  color: #64748b;
}

/* Chart */
.chart-container {
  padding: 1.5rem;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
}
.chart-caption h3 {
  font-size: 1.15rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0 0 0.25rem 0;
}
.chart-caption p {
  font-size: 0.86rem;
  color: #64748b;
  margin: 0 0 1rem 0;
}
.echarts-stage {
  width: 100%;
  height: 420px;
}

/* Insights */
.insights-panel {
  padding: 1.25rem 1.5rem;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
}
.insight-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #c2410c;
  margin-bottom: 0.75rem;
}
.insight-header h4 {
  font-size: 0.95rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
}
.insight-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.25rem;
}
.insight-item strong {
  display: block;
  font-size: 0.85rem;
  color: #1e293b;
  margin-bottom: 0.25rem;
}
.insight-item p {
  font-size: 0.82rem;
  color: #475569;
  margin: 0;
  line-height: 1.5;
}
</style>
