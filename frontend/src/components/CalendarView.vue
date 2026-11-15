<script setup lang="ts">
import { computed, ref } from 'vue'
import { ChevronLeft, ChevronRight, CalendarDays, Info } from '@lucide/vue'
import { decisionLabels, type Decision, type ScreenedAnalysis } from '../huanuco'
const props = defineProps<{ analysis: ScreenedAnalysis | null; decision: Decision }>()
const month = ref(10),
  selected = ref('2026-11-01')
const months = [
  'Enero',
  'Febrero',
  'Marzo',
  'Abril',
  'Mayo',
  'Junio',
  'Julio',
  'Agosto',
  'Septiembre',
  'Octubre',
  'Noviembre',
]
const key = (day: number) =>
  '2026-' + String(month.value + 1).padStart(2, '0') + '-' + String(day).padStart(2, '0')
const days = computed(() => new Date(Date.UTC(2026, month.value + 1, 0)).getUTCDate())
const offset = computed(() => (new Date(Date.UTC(2026, month.value, 1)).getUTCDay() + 6) % 7)
const counts = computed(() => {
  const result = new Map<string, number>()
  for (const r of props.analysis?.event_daily ?? [])
    result.set(r.day, (result.get(r.day) ?? 0) + r.events)
  return result
})
const rows = computed(() => props.analysis?.daily.filter((r) => r.day === selected.value) ?? [])
const beyond = (day: number) => key(day) > '2026-11-13'
function change(delta: number) {
  month.value = Math.max(0, Math.min(10, month.value + delta))
  selected.value = key(1)
}
</script>
<template>
  <div class="secondary-view">
    <div class="context-banner">
      <span class="badge badge-yellow">{{ decisionLabels[decision] }}</span>
      <p>
        Mismos filtros que el mapa · Huánuco 2026. Los conteos representan inicios de agrupaciones
        probables; el detalle conserva sus observaciones.
      </p>
    </div>
    <div class="calendar-layout">
      <section class="surface calendar-card">
        <div class="section-title">
          <div>
            <span class="eyebrow">CALENDARIO EVALUADO</span>
            <h2>{{ months[month] }} <span class="muted">2026</span></h2>
          </div>
          <div class="calendar-actions">
            <button
              class="icon-button"
              aria-label="Mes anterior"
              :disabled="month === 0"
              @click="change(-1)"
            >
              <ChevronLeft :size="20" /></button
            ><button
              class="icon-button"
              aria-label="Mes siguiente"
              :disabled="month === 10"
              @click="change(1)"
            >
              <ChevronRight :size="20" />
            </button>
          </div>
        </div>
        <div class="calendar-grid weekdays">
          <span v-for="d in ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']" :key="d">{{
            d
          }}</span>
        </div>
        <div class="calendar-grid dates">
          <span v-for="i in offset" :key="'offset-' + i" /><button
            v-for="day in days"
            :key="day"
            :disabled="beyond(day)"
            :class="{ selected: selected === key(day), 'has-data': counts.has(key(day)) }"
            :aria-pressed="selected === key(day)"
            :aria-label="
              key(day) +
              ': ' +
              (beyond(day)
                ? 'fuera de la descarga'
                : (counts.get(key(day)) ?? 0) + ' eventos probables')
            "
            @click="selected = key(day)"
          >
            <span>{{ day }}</span><small v-if="counts.has(key(day))"
              ><i />{{ counts.get(key(day)) }}</small
            ><span v-else class="day-empty">—</span>
          </button>
        </div>
        <div class="calendar-key">
          <span><i />Con eventos probables</span
          ><span>Fechas UTC · Sin registros no significa sin fuego</span>
        </div>
      </section>
      <aside class="surface calendar-detail">
        <span class="eyebrow"><CalendarDays :size="15" />DÍA SELECCIONADO</span>
        <h2>{{ selected }}</h2>
        <p>Huánuco · {{ decisionLabels[decision] }}</p>
        <div class="sensor-mini">
          <div v-for="sensor in ['MODIS', 'VIIRS'] as const" :key="sensor">
            <span>{{ sensor }}</span><strong>{{
              !analysis || selected > analysis.ends[sensor]
                ? '—'
                : (rows.find((r) => r.sensor === sensor)?.detections ?? 0)
            }}</strong
            ><small>{{
              analysis && selected > analysis.ends[sensor]
                ? 'Fuera de la descarga disponible'
                : 'observaciones evaluadas'
            }}</small>
          </div>
        </div>
        <p class="inline-note">
          <Info :size="15" />La fecha de la última observación no demuestra cobertura diaria sin
          nubes. Suomi y MODIS tienen fechas de corte diferentes.
        </p>
        <div class="week-card">
          <span class="eyebrow">CRITERIO COMPARTIDO</span>
          <p>
            La misma decisión, cobertura y confianza se aplica al mapa, al calendario y al análisis.
          </p>
        </div>
      </aside>
    </div>
  </div>
</template>
