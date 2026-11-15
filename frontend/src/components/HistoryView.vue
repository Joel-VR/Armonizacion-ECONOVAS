<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { use, init, type EChartsType } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { Info, ChartNoAxesCombined } from '@lucide/vue'
import { decisionLabels, type Decision, type ScreenedAnalysis } from '../huanuco'
use([BarChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])
const props = defineProps<{ analysis: ScreenedAnalysis | null; decision: Decision }>()
const element = ref<HTMLDivElement>(),
  group = ref('month')
let chart: EChartsType | undefined, observer: ResizeObserver | undefined
const rows = computed(() => {
  const data = new Map<string, { label: string; MODIS: number; VIIRS: number }>()
  for (const d of props.analysis?.daily ?? []) {
    const key = group.value === 'month' ? d.day.slice(0, 7) : d.day
    const row = data.get(key) ?? { label: key, MODIS: 0, VIIRS: 0 }
    row[d.sensor] += d.detections
    data.set(key, row)
  }
  return [...data.values()].sort((a, b) => a.label.localeCompare(b.label))
})
const totals = computed(() => ({
  MODIS: (props.analysis?.daily ?? [])
    .filter((d) => d.sensor === 'MODIS')
    .reduce((n, d) => n + d.detections, 0),
  VIIRS: (props.analysis?.daily ?? [])
    .filter((d) => d.sensor === 'VIIRS')
    .reduce((n, d) => n + d.detections, 0),
}))
function draw() {
  chart?.setOption(
    {
      animation: false,
      color: ['#ed9d3b', '#dc3545'],
      tooltip: { trigger: 'axis', confine: true },
      legend: { bottom: 0 },
      grid: { top: 35, left: 55, right: 20, bottom: 75 },
      xAxis: {
        type: 'category',
        data: rows.value.map((r) => r.label),
        axisLabel: { color: '#838995', fontSize: 10 },
        axisTick: { show: false },
        axisLine: { lineStyle: { color: '#e5e8ed' } },
      },
      yAxis: {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: '#edf0f2', type: 'dashed' } },
      },
      series: ['MODIS', 'VIIRS'].map((sensor) => ({
        name: sensor,
        type: 'bar',
        barMaxWidth: 28,
        itemStyle: { borderRadius: [4, 4, 0, 0] },
        data: rows.value.map((r) => r[sensor as 'MODIS' | 'VIIRS']),
      })),
    },
    true,
  )
}
watch([rows, () => props.analysis], async () => {
  await nextTick()
  draw()
})
onMounted(() => {
  if (!element.value) return
  chart = init(element.value)
  draw()
  observer = new ResizeObserver(() => chart?.resize())
  observer.observe(element.value)
})
onUnmounted(() => {
  observer?.disconnect()
  chart?.dispose()
})
</script>
<template>
  <div class="secondary-view">
    <div class="context-banner">
      <span class="badge badge-yellow">{{ decisionLabels[decision] }}</span>
      <p>
        Huánuco 2026 · {{ analysis?.event_count ?? 0 }} eventos probables, sustentados por
        {{ analysis?.total_selected ?? 0 }} observaciones. Las barras cuentan observaciones por
        sensor, no incendios distintos.
      </p>
    </div>
    <div class="history-stats">
      <article class="surface">
        <small>MODIS · observaciones filtradas</small
        ><strong>{{ analysis ? totals.MODIS.toLocaleString('es-PE') : '—' }}</strong>
        <p>Última fecha del archivo: {{ analysis?.ends.MODIS ?? '—' }}</p>
      </article>
      <article class="surface">
        <small>VIIRS Suomi · observaciones filtradas</small
        ><strong>{{ analysis ? totals.VIIRS.toLocaleString('es-PE') : '—' }}</strong>
        <p>Última fecha del archivo: {{ analysis?.ends.VIIRS ?? '—' }}</p>
      </article>
      <article class="surface">
        <small>Referencia territorial</small><strong>{{ analysis?.reference.year ?? '—' }}</strong>
        <p>MapBiomas · Cobertura anterior, no verificación del evento</p>
      </article>
    </div>
    <section class="surface chart-card">
      <div class="section-title">
        <div>
          <span class="eyebrow">ACTIVIDAD OBSERVADA · HUÁNUCO</span>
          <h2>Observaciones aceptadas por el filtro</h2>
          <p>{{ decisionLabels[decision] }} · Las fuentes se conservan separadas</p>
        </div>
        <label class="history-group"
          >Agrupar<select v-model="group">
            <option value="month">Por mes</option>
            <option value="day">Por día</option>
          </select></label
        ><ChartNoAxesCombined class="red-icon" :size="22" />
      </div>
      <div
        ref="element"
        class="history-chart"
        role="img"
        :aria-label="`Observaciones evaluadas: ${totals.MODIS} MODIS y ${totals.VIIRS} VIIRS`"
      />
      <details class="chart-table">
        <summary>Ver tabla de datos accesible</summary>
        <table>
          <thead>
            <tr>
              <th>Periodo UTC</th>
              <th>MODIS</th>
              <th>VIIRS</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in rows" :key="r.label">
              <th>{{ r.label }}</th>
              <td>{{ r.MODIS }}</td>
              <td>{{ r.VIIRS }}</td>
            </tr>
          </tbody>
        </table>
      </details>
    </section>
    <p class="inline-note">
      <Info :size="16" />Esta versión une la estructura y los criterios de revisión, conservando
      cada sensor. No convierte conteos en incendios únicos ni presenta una calibración estadística
      validada.
    </p>
  </div>
</template>
