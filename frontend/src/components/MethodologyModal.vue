<script setup lang="ts">
import { X, BookOpen, Layers, Flame, Scale, AlertTriangle, ExternalLink } from '@lucide/vue'

defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: [] }>()
</script>

<template>
  <div v-if="open" class="modal-backdrop" @click.self="emit('close')">
    <div class="modal-card surface" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <header class="modal-header">
        <div class="modal-title-group">
          <span class="eyebrow"><BookOpen :size="14" /> NASA SPACE APPS CHALLENGE</span>
          <h2 id="modal-title">Metodología de Armonización MODIS & VIIRS</h2>
        </div>
        <button class="icon-button" aria-label="Cerrar ventana" @click="emit('close')">
          <X :size="20" />
        </button>
      </header>

      <div class="modal-content">
        <!-- 1. El Desafío -->
        <section class="doc-section">
          <h3><Scale :size="18" /> 1. El Desafío: El relevo de MODIS por VIIRS</h3>
          <p>
            Los sensores <strong>MODIS</strong> (a bordo de Terra y Aqua) han proporcionado más de dos décadas de monitoreo continuo de focos de calor activos. Sin embargo, se acercan al fin de su vida operativa y están siendo reemplazados por los sensores <strong>VIIRS</strong> (Suomi-NPP, NOAA-20, NOAA-21).
          </p>
          <div class="comparison-grid">
            <div class="comp-card modis-card">
              <h4>Sensor MODIS (Terra / Aqua)</h4>
              <ul>
                <li><strong>Resolución espacial:</strong> 1 km en nadir (~2×4.8 km en los bordes de barrido).</li>
                <li><strong>Horas de sobrevuelo ecuatorial:</strong> ~10:30 AM/PM (Terra), ~01:30 AM/PM (Aqua).</li>
                <li><strong>Sensibilidad:</strong> Detecta fuegos con FRP típicamente superior a 10 MW.</li>
                <li><strong>Estado:</strong> Órbita a la deriva, fin operacional inminente.</li>
              </ul>
            </div>
            <div class="comp-card viirs-card">
              <h4>Sensor VIIRS (Suomi-NPP / NOAA-20, 21)</h4>
              <ul>
                <li><strong>Resolución espacial:</strong> 375 m en bandas I (canales infrarrojos térmicos).</li>
                <li><strong>Horas de sobrevuelo ecuatorial:</strong> ~01:30 AM/PM (Suomi-NPP / NOAA).</li>
                <li><strong>Sensibilidad:</strong> Detecta quemas agrícolas pequeñas y fuegos de baja intensidad (~3 a 5 veces más detecciones que MODIS).</li>
                <li><strong>Estado:</strong> Operacional actual y estándar futuro de NASA/NOAA.</li>
              </ul>
            </div>
          </div>
          <p class="inline-callout">
            <strong>¿Por qué no comparar conteos directos?</strong> Si se grafican juntos los conteos de hotspots, parecería que los incendios se triplicaron o cuadruplicaron con la llegada de VIIRS en 2012, lo cual es un <em>artefacto de sensor</em> (mayor resolución y sensibilidad), no un aumento real del fuego.
          </p>
        </section>

        <!-- 2. Pipeline de Armonización -->
        <section class="doc-section">
          <h3><Layers :size="18" /> 2. Arquitectura de Armonización T'UKRI</h3>
          <ol class="steps-list">
            <li>
              <strong>Agrupación Espacio-Temporal en Celdas Métricas (5 km celdas-día):</strong>
              Para desacoplar el número de observaciones del tamaño del píxel, se proyectan las coordenadas a la cuadrícula UTM de la región y se calcula la métrica binaria de <em>celda-día</em> (si una celda de 5 km tuvo presencia de fuego en un día dado, cuenta como 1, independientemente de si VIIRS disparó 8 píxeles en su interior o MODIS disparó 1).
            </li>
            <li>
              <strong>Transformación a Distribución Empírica (Percentiles Semanales):</strong>
              Se compara el valor de celdas-día de cada semana con la serie histórica correspondiente a esa misma ventana estacional durante el periodo de referencia (2016–2024). Esto asigna a cada sensor un percentil de actividad entre 0% y 100%:
              <code>P(w) = (N_{menores} + 0.5 \times N_{iguales}) / N_{total}</code>
            </li>
            <li>
              <strong>Índice de Fuego Armonizado Unificado:</strong>
              Se combinan ambos sensores en un índice robusto donde ninguno sesga al otro:
              <code>H(w) = \frac{P_{MODIS}(w) + P_{VIIRS}(w)}{2}</code>
              Si ambos sensores concuerdan, la diferencia es cercana a cero.
            </li>
            <li>
              <strong>Cálculo de Línea Base y Detección de Anomalías:</strong>
              Para cada mes del año, se computa la <em>mediana histórica</em> y el rango intercuartil (P25 - P75). Toda semana o mes cuyo índice supere en más de un +30% o +75% la mediana histórica se clasifica como <strong>Anomalía Crítica</strong>, activando alertas tempranas para gestores de emergencias.
            </li>
          </ol>
        </section>

        <!-- 3. Supuestos y Limitaciones -->
        <section class="doc-section">
          <h3><AlertTriangle :size="18" /> 3. Supuestos, Limitaciones e Incertidumbre</h3>
          <ul class="limitations-list">
            <li><strong>No equivale a área quemada ni confirmación de campo:</strong> Los focos térmicos representan anomalías de temperatura en la superficie al momento del pase satelital; no determinan el perímetro final del incendio ni sustituyen el reporte de brigadistas.</li>
            <li><strong>Cobertura de nubes y humo espeso:</strong> La nubosidad densa o columnas intensas de humo pueden atenuar o enmascarar la radiación infrarroja, impidiendo la detección de fuegos activos subyacentes.</li>
            <li><strong>Sobrevuelos discretos:</strong> Satélites en órbita polar observan cada zona típicamente 2 veces al día por satélite. Fuegos de corta duración (p. ej., quemas agrícolas de 2 horas entre pases) pueden no ser detectados.</li>
            <li><strong>Contexto territorial:</strong> En el módulo detallado de Huánuco, se incorpora la cobertura de suelo de MapBiomas Perú (Bosque, Agrícola, Mosaico Mixto, Agua, Urbano) para sugerir la naturaleza del fuego sin inventar perímetros de clasificación.</li>
          </ul>
        </section>

        <!-- 4. Fuentes de Datos -->
        <section class="doc-section">
          <h3><Flame :size="18" /> 4. Fuentes de Datos y Citas</h3>
          <p>Esta aplicación utiliza datos oficiales de:</p>
          <div class="sources-links">
            <a href="https://firms.modaps.eosdis.nasa.gov/" target="_blank" rel="noopener noreferrer">
              NASA FIRMS (Fire Information for Resource Management System) <ExternalLink :size="13" />
            </a>
            <a href="https://peru.mapbiomas.org/" target="_blank" rel="noopener noreferrer">
              MapBiomas Perú · Colección 4 de Cobertura y Uso del Suelo <ExternalLink :size="13" />
            </a>
            <a href="https://earthdata.nasa.gov/" target="_blank" rel="noopener noreferrer">
              NASA Earthdata <ExternalLink :size="13" />
            </a>
          </div>
        </section>
      </div>

      <footer class="modal-footer">
        <button class="primary-button" @click="emit('close')">Entendido</button>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(4px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  overflow-y: auto;
}
.modal-card {
  max-width: 820px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.25);
  overflow: hidden;
  border: 1px solid #e2e8f0;
}
.modal-header {
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  background: #f8fafc;
}
.modal-title-group .eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  color: #c2410c;
  letter-spacing: 0.05em;
  margin-bottom: 0.25rem;
}
.modal-title-group h2 {
  font-size: 1.35rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
}
.modal-content {
  padding: 1.5rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  font-size: 0.92rem;
  line-height: 1.6;
  color: #334155;
}
.doc-section h3 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.05rem;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 0.75rem;
}
.comparison-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin: 1rem 0;
}
@media (max-width: 640px) {
  .comparison-grid {
    grid-template-columns: 1fr;
  }
}
.comp-card {
  padding: 1rem;
  border-radius: 8px;
  font-size: 0.85rem;
}
.modis-card {
  background: #fefce8;
  border: 1px solid #fde047;
}
.viirs-card {
  background: #fef2f2;
  border: 1px solid #fca5a5;
}
.comp-card h4 {
  font-weight: 700;
  margin-bottom: 0.5rem;
}
.comp-card ul {
  padding-left: 1.2rem;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.inline-callout {
  background: #f1f5f9;
  border-left: 4px solid #64748b;
  padding: 0.75rem 1rem;
  border-radius: 0 6px 6px 0;
  margin: 0.75rem 0;
  font-size: 0.88rem;
}
.steps-list {
  padding-left: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.steps-list code {
  display: block;
  background: #0f172a;
  color: #38bdf8;
  padding: 0.35rem 0.65rem;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.82rem;
  margin-top: 0.3rem;
  width: fit-content;
}
.limitations-list {
  padding-left: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.sources-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 0.5rem;
}
.sources-links a {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.4rem 0.75rem;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  color: #0369a1;
  text-decoration: none;
  font-weight: 600;
  font-size: 0.84rem;
  transition: all 0.15s ease;
}
.sources-links a:hover {
  background: #e0f2fe;
  border-color: #38bdf8;
}
.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid #e2e8f0;
  background: #f8fafc;
  display: flex;
  justify-content: flex-end;
}
.primary-button {
  background: #b81d24;
  color: #fff;
  border: none;
  padding: 0.55rem 1.5rem;
  border-radius: 6px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s ease;
}
.primary-button:hover {
  background: #991b1b;
}
</style>
