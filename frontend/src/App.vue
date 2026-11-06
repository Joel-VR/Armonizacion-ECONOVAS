<script setup lang="ts">
import { onMounted, ref } from 'vue'
const status = ref('Consultando API…')
onMounted(async () => {
  try {
    const response = await fetch('/api/health')
    if (!response.ok) throw new Error('API no disponible')
    const data: { status: string } = await response.json()
    status.value = data.status === 'ok' ? 'API disponible' : 'Estado desconocido'
  } catch { status.value = 'API no disponible; revise que el backend esté en ejecución.' }
})
</script>
<template><main><p class="eyebrow">NASA FIRMS · PROTOTIPO</p><h1>IGNISTERRA</h1><p>Exploración de focos de calor detectados por satélite.</p><p>Las detecciones no confirman por sí solas incendios forestales.</p><section><h2>Estado del proyecto</h2><p>{{ status }}</p><p>El mapa, el calendario y el análisis histórico están pendientes. No hay datos cargados.</p></section></main></template>
