<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { use, init, type EChartsType } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, AriaComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { ChartNoAxesCombined, Flame, MapPin, Satellite, Info, ChevronDown } from '@lucide/vue'
import { detections } from '../data'
use([BarChart, GridComponent, TooltipComponent, LegendComponent, AriaComponent, CanvasRenderer])
const region = ref('Todas')
const granularity = ref('day')
const chartElement = ref<HTMLDivElement>()
let chart: EChartsType | undefined
let observer: ResizeObserver | undefined
const regions = [
  ...new Set(detections.filter((d) => d.country === 'PER').map((d) => d.department)),
].sort()
const records = computed(() =>
  detections.filter(
    (d) => d.country === 'PER' && (region.value === 'Todas' || d.department === region.value),
  ),
)
const regionCount = computed(() => new Set(records.value.map((d) => d.department)).size)
const modis = computed(() => records.value.filter((d) => d.sensor === 'MODIS').length)
const buckets = computed(() =>
  granularity.value === 'day'
    ? Array.from({ length: 13 }, (_, i) => ({
        label: `${i + 1} nov.`,
        prefix: `2026-11-${String(i + 1).padStart(2, '0')}`,
      }))
    : [{ label: 'Noviembre', prefix: '2026-11' }],
)
function draw() {
  if (!chart) return
  chart.setOption(
    {
      aria: { enabled: true },
      color: ['#e63740', '#f5a13a'],
      tooltip: { trigger: 'axis', confine: true },
      legend: { bottom: 0, icon: 'roundRect', itemWidth: 12, itemHeight: 8 },
      grid: { left: 42, top: 30, right: 20, bottom: 75 },
      xAxis: {
        type: 'category',
        data: buckets.value.map((b) => b.label),
        axisLine: { lineStyle: { color: '#e6e8ed' } },
        axisTick: { show: false },
        axisLabel: { color: '#7c818c', fontSize: 11 },
      },
      yAxis: {
        type: 'value',
        minInterval: 1,
        name: 'Observaciones',
        nameTextStyle: { color: '#858a95', align: 'left' },
        splitLine: { lineStyle: { color: '#f0f1f4', type: 'dashed' } },
        axisLabel: { color: '#858a95' },
      },
      series: ['MODIS', 'VIIRS'].map((sensor) => ({
        name: sensor,
        type: 'bar',
        barMaxWidth: 24,
        itemStyle: { borderRadius: [4, 4, 0, 0] },
        data: buckets.value.map(
          (b) =>
            records.value.filter((d) => d.sensor === sensor && d.acquiredAt.startsWith(b.prefix))
              .length,
        ),
      })),
    },
    true,
  )
}
watch([region, granularity], async () => {
  await nextTick()
  draw()
})
onMounted(() => {
  if (!chartElement.value) return
  chart = init(chartElement.value)
  draw()
  observer = new ResizeObserver(() => chart?.resize())
  observer.observe(chartElement.value)
})
onUnmounted(() => {
  observer?.disconnect()
  chart?.dispose()
})
</script>
<template>
  <div class="secondary-view">
    <div class="context-banner">
      <span class="badge badge-yellow">Conexión pendiente</span>
      <p>
        La conexión con la base de datos está pendiente; todavía no hay un análisis histórico para mostrar.
      </p>
    </div>
    <div class="surface history-controls">
      <div>
        <span class="eyebrow">CONFIGURA TU CONSULTA</span>
        <h2>Panorama de observaciones</h2>
        <p>Perú · Datos no disponibles</p>
      </div>
      <div class="history-selects">
        <label
          >Departamento
          <div class="select-wrap">
            <select v-model="region">
              <option>Todas</option>
              <option v-for="name in regions" :key="name">{{ name }}</option></select
            ><ChevronDown :size="14" /></div></label
        ><label
          >Agrupar por
          <div class="select-wrap">
            <select v-model="granularity">
              <option value="day">Día</option>
              <option value="month">Mes</option></select
            ><ChevronDown :size="14" /></div
        ></label>
      </div>
    </div>
    <div v-if="records.length" class="history-stats">
      <article class="surface">
        <span class="stat-icon"><Flame :size="20" /></span><small>Observaciones</small
        ><strong>{{ records.length }}</strong>
        <p>En el periodo y territorio seleccionados</p>
      </article>
      <article class="surface">
        <span class="stat-icon"><MapPin :size="20" /></span
        ><small>Departamentos representados</small><strong>{{ regionCount }}</strong>
        <p>Datos no disponibles</p>
      </article>
      <article class="surface">
        <span class="stat-icon"><Satellite :size="20" /></span
        ><small>Distribución por instrumento</small
        ><strong
          >{{ modis }} <em>/ {{ records.length - modis }}</em></strong
        >
        <p>MODIS / VIIRS · sin armonizar</p>
      </article>
    </div>
    <section v-if="records.length" class="surface chart-card">
      <div class="section-title">
        <div>
          <span class="eyebrow">DISTRIBUCIÓN TEMPORAL</span>
          <h2>Observaciones por {{ granularity === 'day' ? 'día' : 'mes' }}</h2>
          <p>Datos no disponibles · {{ region === 'Todas' ? 'Todo el Perú' : region }}</p>
        </div>
        <ChartNoAxesCombined class="red-icon" :size="25" />
      </div>
      <div
        ref="chartElement"
        class="history-chart"
        role="img"
        :aria-label="`Gráfico de ${records.length} observaciones: ${modis} MODIS y ${records.length - modis} VIIRS`"
      />
      <details class="chart-table">
        <summary>Ver los datos del gráfico en tabla</summary>
        <table>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>MODIS</th>
              <th>VIIRS</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="b in buckets" :key="b.prefix">
              <th>{{ b.label }}</th>
              <td>
                {{
                  records.filter((d) => d.sensor === 'MODIS' && d.acquiredAt.startsWith(b.prefix))
                    .length
                }}
              </td>
              <td>
                {{
                  records.filter((d) => d.sensor === 'VIIRS' && d.acquiredAt.startsWith(b.prefix))
                    .length
                }}
              </td>
            </tr>
          </tbody>
        </table>
      </details>
    </section>
    <div class="surface calendar-card" role="status">No hay datos para mostrar. La conexión de esta vista con la base está pendiente.</div>
    <p class="inline-note">
      <Info :size="16" />MODIS y VIIRS tienen resoluciones y sensibilidades distintas. Los conteos
      no equivalen a incendios únicos ni a superficie quemada.
    </p>
  </div>
</template>
