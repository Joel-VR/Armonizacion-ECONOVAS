<script setup lang="ts">
import { computed, ref } from 'vue'
import { ChevronLeft, ChevronRight, CalendarDays, Flame, Satellite, Info } from '@lucide/vue'
import { detections, dateLabel } from '../data'
const month = ref(10)
const year = ref(2026)
const selected = ref(13)
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
  'Diciembre',
]
const days = computed(() => new Date(year.value, month.value + 1, 0).getDate())
const offset = computed(() => (new Date(year.value, month.value, 1).getDay() + 6) % 7)
const dateKey = (day: number) =>
  `${year.value}-${String(month.value + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
const observations = (day: number) =>
  detections.filter((d) => d.country === 'PER' && d.acquiredAt.startsWith(dateKey(day)))
const chosen = computed(() => observations(selected.value))
const total = computed(
  () =>
    detections.filter((d) => d.country === 'PER' && d.acquiredAt.startsWith(dateKey(1).slice(0, 7)))
      .length,
)
function changeMonth(delta: number) {
  const date = new Date(year.value, month.value + delta, 1)
  month.value = date.getMonth()
  year.value = date.getFullYear()
  selected.value = 1
}
function reset() {
  year.value = 2026
  month.value = 10
  selected.value = 13
}
</script>
<template>
  <div class="secondary-view">
    <div class="context-banner">
      <span class="badge badge-yellow">Datos ficticios</span>
      <p>
        Perú · Ejemplos disponibles del 1 al 13 de noviembre de 2026. Los días vacíos no indican
        ausencia de incendios.
      </p>
    </div>
    <div class="calendar-layout">
      <section class="surface calendar-card">
        <div class="section-title">
          <div>
            <span class="eyebrow">CALENDARIO DE OBSERVACIONES</span>
            <h2>
              {{ months[month] }} <span class="muted">{{ year }}</span>
            </h2>
          </div>
          <div class="calendar-actions">
            <button class="button button-outline" @click="reset">Ir a la demo</button
            ><button class="icon-button" aria-label="Mes anterior" @click="changeMonth(-1)">
              <ChevronLeft :size="19" /></button
            ><button class="icon-button" aria-label="Mes siguiente" @click="changeMonth(1)">
              <ChevronRight :size="19" />
            </button>
          </div>
        </div>
        <div class="calendar-grid weekdays">
          <span v-for="day in ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']" :key="day">{{
            day
          }}</span>
        </div>
        <div class="calendar-grid dates">
          <span v-for="i in offset" :key="'empty-' + i" /><button
            v-for="day in days"
            :key="day"
            :class="{ selected: selected === day, 'has-data': observations(day).length > 0 }"
            :aria-pressed="selected === day"
            :aria-label="`${day} de ${months[month]}: ${observations(day).length} observaciones de ejemplo`"
            @click="selected = day"
          >
            <span>{{ day }}</span><small v-if="observations(day).length"
              ><i />{{ observations(day).length
              }}<span class="desktop-label"> observaciones</span></small
            ><span v-else class="day-empty">—</span>
          </button>
        </div>
        <div class="calendar-key">
          <span><i />Con observaciones de ejemplo</span
          ><span>{{ total }} observaciones en el mes · Perú</span>
        </div>
      </section>
      <aside class="surface calendar-detail">
        <span class="eyebrow"><CalendarDays :size="14" />DÍA SELECCIONADO</span>
        <h2>{{ selected }} de {{ months[month].toLowerCase() }}</h2>
        <p>{{ year }} · Perú</p>
        <div class="day-count">
          <Flame :size="27" /><strong>{{ chosen.length }}</strong
          ><span>observaciones de ejemplo</span>
        </div>
        <div v-if="chosen.length" class="day-observations">
          <article v-for="d in chosen" :key="d.id">
            <span class="day-location">{{ d.department }}</span><small
              ><Satellite :size="12" />{{ d.sensor }} · {{ d.frp.toFixed(1) }} MW</small
            ><time>{{ dateLabel(d.acquiredAt) }}</time>
          </article>
        </div>
        <div v-else class="news-empty">
          <CalendarDays :size="28" />
          <h4>Sin ejemplos para esta fecha</h4>
          <p>Selecciona un día marcado o vuelve a noviembre de 2026.</p>
        </div>
        <p class="inline-note">
          <Info :size="15" />Cada registro representa una observación, no un incendio confirmado.
        </p>
      </aside>
    </div>
  </div>
</template>
