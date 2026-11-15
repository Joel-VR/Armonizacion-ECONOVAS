<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { percent, type Analysis } from '../huanuco'

const props = defineProps<{ analysis: Analysis | null; calendar: boolean; compact?: boolean; year: number }>()
const emit = defineEmits<{ 'update:year': [year: number] }>()
const selected = ref(`${props.year}-01-01`)
watch(() => props.year, year => { selected.value = `${year}-01-01` })
const week = computed(() => props.analysis?.weekly.find(w => w.start <= selected.value && w.end >= selected.value))
</script>

<template>
  <section class="surface chart-card">
    <div class="section-title"><div>
      <span class="eyebrow">HUÁNUCO · {{ year }} · CUADRÍCULA DE 5 KM</span>
      <h2>{{ calendar ? 'Calendario de actividad semanal' : 'Indicadores armonizados' }}</h2>
      <p>Resultados experimentales precalculados por semana. No son conteos de incendios.</p>
    </div></div>
    <label v-if="!compact">Año <select :value="year" @change="emit('update:year', Number(($event.target as HTMLSelectElement).value))"><option v-for="y in 11" :key="y" :value="2027-y">{{ 2027-y }}</option></select></label>
    <p v-if="!analysis || analysis.year !== year">Consultando indicadores semanales…</p>
    <p v-else-if="!analysis.weekly.length">No hay indicadores disponibles para Huánuco en {{ year }}.</p>
    <template v-else>
      <label v-if="calendar">Fecha <input v-model="selected" type="date" :min="`${year}-01-01`" :max="`${year}-12-31`"></label>
      <div v-if="calendar && week" class="week-card">
        <h3>Semana {{ week.week }} · {{ week.start }} a {{ week.end }}</h3>
        <p>MODIS: {{ week.sensors.MODIS.cells ?? '—' }} celdas-día · percentil {{ percent(week.sensors.MODIS.percentile) }}</p>
        <p>VIIRS Suomi: {{ week.sensors.VIIRS.cells ?? '—' }} celdas-día · percentil {{ percent(week.sensors.VIIRS.percentile) }}</p>
        <p>Índice combinado: {{ percent(week.combined) }} · diferencia: {{ percent(week.disagreement) }}</p>
      </div>
      <p v-else-if="calendar">No hay datos semanales para la fecha seleccionada.</p>
      <details v-if="!calendar" :open="!compact" class="chart-table">
        <summary>Ver indicadores por semana</summary>
        <table><thead><tr><th>Inicio UTC</th><th>MODIS celdas-día</th><th>VIIRS celdas-día</th><th>Índice combinado</th><th>Diferencia</th></tr></thead>
          <tbody><tr v-for="w in analysis.weekly" :key="w.start"><th>{{ w.start }}</th><td>{{ w.sensors.MODIS.cells ?? '—' }}</td><td>{{ w.sensors.VIIRS.cells ?? '—' }}</td><td>{{ percent(w.combined) }}</td><td>{{ percent(w.disagreement) }}</td></tr></tbody>
        </table>
      </details>
      <p class="inline-note">La tabla no incluye puntos geográficos, conteos diarios ni eventos evaluados. Los filtros de eventos no modifican estos indicadores.</p>
    </template>
  </section>
</template>
