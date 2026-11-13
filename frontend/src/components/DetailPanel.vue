<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  X,
  MapPin,
  Satellite,
  CalendarDays,
  ExternalLink,
  Info,
  Newspaper,
  ArrowUpRight,
  Flame,
  Crosshair,
} from '@lucide/vue'
import { dateLabel, periodLabels, type Detection, type Period } from '../data'
const props = defineProps<{
  detection: Detection
  period: Period
  count: number
  countryName: string
}>()
const emit = defineEmits<{ close: [] }>()
const closeButton = ref<HTMLButtonElement>()
onMounted(() => closeButton.value?.focus({ preventScroll: true }))
const newsUrl = computed(
  () =>
    'https://news.google.com/search?q=' +
    encodeURIComponent(
      `incendio forestal quema agrícola ${props.detection.department} ${props.countryName}`,
    ) +
    '&hl=es-419&gl=PE&ceid=PE:es-419',
)
const rows = computed(() => [
  ['Adquisición (UTC)', dateLabel(props.detection.acquiredAt)],
  ['Instrumento', props.detection.sensor],
  ['Satélite', props.detection.satellite],
  ['Confianza original', props.detection.confidence],
  ['Potencia radiativa (FRP)', `${props.detection.frp.toFixed(1)} MW`],
  [
    props.detection.sensor === 'VIIRS' ? 'Temperatura I-4' : 'Temperatura canal 21/22',
    `${props.detection.brightness.toFixed(1)} K`,
  ],
  ['Píxel · scan × track', `${props.detection.scan} × ${props.detection.track} km`],
  ['Observación', props.detection.daynight === 'D' ? 'Diurna' : 'Nocturna'],
  ['Versión del producto', 'Sin producto real cargado'],
  ['Armonización', 'Método pendiente de validación'],
])
</script>
<template>
  <aside class="detail-panel" aria-labelledby="detail-title" @keydown.esc="emit('close')">
    <header class="detail-header">
      <div>
        <span class="eyebrow"><MapPin :size="13" /> ÁREA SELECCIONADA</span>
        <h2 id="detail-title">
          {{ detection.department }}<small>{{ countryName }}</small>
        </h2>
      </div>
      <button
        ref="closeButton"
        class="icon-button"
        aria-label="Cerrar detalles"
        @click="emit('close')"
      >
        <X :size="19" />
      </button>
    </header>
    <div class="detail-body">
      <span class="badge badge-yellow">Observación satelital</span>
      <section>
        <h3><MapPin :size="17" /> Información del área</h3>
        <dl class="data-list">
          <div>
            <dt>Periodo seleccionado</dt>
            <dd>{{ periodLabels[period] }}</dd>
          </div>
          <div>
            <dt>Departamento / región</dt>
            <dd>{{ detection.department }}</dd>
          </div>
          <div>
            <dt>Provincia / distrito</dt>
            <dd>Sin determinar</dd>
          </div>
          <div>
            <dt>Observaciones en el área</dt>
            <dd>{{ count }}</dd>
          </div>
        </dl>
        <div class="coordinate-card">
          <Crosshair :size="17" />
          <div>
            <small>Centro del píxel</small
            ><strong
              >{{ detection.latitude.toFixed(4) }}°, {{ detection.longitude.toFixed(4) }}°</strong
            >
          </div>
        </div>
      </section>
      <section>
        <h3><Satellite :size="18" /> Observación seleccionada</h3>
        <dl class="data-list">
          <div v-for="[name, value] in rows" :key="name">
            <dt>{{ name }}</dt>
            <dd>{{ value }}</dd>
          </div>
        </dl>
        <p class="inline-note">
          <Info :size="15" /> La confianza y la temperatura dependen del instrumento. No son una
          escala de gravedad.
        </p>
      </section>
      <section class="event-note">
        <Flame :size="21" />
        <div>
          <h4>Clasificación por verificar</h4>
          <p>
            Una detección puede corresponder a fuego u otra anomalía térmica. No permite distinguir
            por sí sola un incendio forestal de una quema agrícola ni calcular el área quemada.
          </p>
        </div>
      </section>
      <section>
        <div class="section-title">
          <h3><Newspaper :size="18" /> Noticias relacionadas</h3>
          <ArrowUpRight :size="17" />
        </div>
        <div class="news-empty">
          <Newspaper :size="27" />
          <h4>Contrasta con fuentes locales</h4>
          <p>
            No hay noticias verificadas vinculadas a esta observación. Puedes buscar cobertura de
            {{ detection.department }}.
          </p>
          <a :href="newsUrl" target="_blank" rel="noopener noreferrer" class="button button-outline"
            >Buscar noticias <ExternalLink :size="15"
          /></a>
        </div>
        <p class="fine-print">
          La búsqueda abre Google Noticias. Sus resultados no confirman una relación con esta
          detección.
        </p>
      </section>
      <a
        class="source-link"
        href="https://firms.modaps.eosdis.nasa.gov/"
        target="_blank"
        rel="noopener noreferrer"
        ><CalendarDays :size="15" /> Conoce la fuente NASA FIRMS <ExternalLink :size="13"
      /></a>
    </div>
  </aside>
</template>
