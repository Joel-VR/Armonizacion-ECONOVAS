import { ref, watch } from 'vue'

export type Language = 'en' | 'es'
export const language = ref<Language>(localStorage.getItem('tukri-language') === 'es' ? 'es' : 'en')

watch(language, (value) => {
  localStorage.setItem('tukri-language', value)
  document.documentElement.lang = value
  document.title = value === 'en' ? "T'UKRI · Satellite Monitoring and Harmonization" : "T'UKRI · Monitoreo y Armonización Satelital"
}, { immediate: true })

export function tr(es: string, en: string): string {
  return language.value === 'en' ? en : es
}
