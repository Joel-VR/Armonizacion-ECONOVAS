<script setup lang="ts">
import { computed, ref } from 'vue'
import { ChevronLeft, ChevronRight, CalendarDays, Flame, Satellite, Info } from '@lucide/vue'
import { detections, dateLabel } from '../data'
const month = ref(new Date().getUTCMonth())
const year = ref(new Date().getUTCFullYear())
const selected = ref(new Date().getUTCDate())
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
function changeMonth(delta: number) {
  const date = new Date(year.value, month.value + delta, 1)
  month.value = date.getMonth()
  year.value = date.getFullYear()
  selected.value = 1
}
function reset() {
  const now = new Date()
  year.value = now.getUTCFullYear()
  month.value = now.getUTCMonth()
  selected.value = now.getUTCDate()
}
</script>
<template>
  <div class="secondary-view">
    <div class="context-banner">
      <span class="badge badge-yellow">Conexión pendiente</span>
      <p>
        Perú · La vista aún no está conectada a los datos. Los días vacíos no indican ausencia de incendios.
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
            <button class="button button-outline" @click="reset">Ir a hoy</button
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
            :aria-label="`${day} de ${months[month]}: datos no disponibles`"
            @click="selected = day"
          >
            <span>{{ day }}</span><small v-if="observations(day).length"
              ><i />{{ observations(day).length
              }}<span class="desktop-label"> observaciones</span></small
            ><span v-else class="day-empty">—</span>
          </button>
        </div>
        <div class="calendar-key">
          <span><i />Con observaciones</span
          ><span>Datos del mes no disponibles</span>
        </div>
      </section>
      <aside class="surface calendar-detail">
        <span class="eyebrow"><CalendarDays :size="14" />DÍA SELECCIONADO</span>
        <h2>{{ selected }} de {{ months[month].toLowerCase() }}</h2>
        <p>{{ year }} · Perú</p>
        <div class="day-count">
          <Flame :size="27" /><strong>{{ chosen.length }}</strong
          ><span>observaciones</span>
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
          <h4>No hay datos para mostrar</h4>
          <p>La conexión de esta vista con la base de datos está pendiente.</p>
        </div>
        <p class="inline-note">
          <Info :size="15" />Cada registro representa una observación, no un incendio confirmado.
        </p>
      </aside>
    </div>
  </div>
</template>
