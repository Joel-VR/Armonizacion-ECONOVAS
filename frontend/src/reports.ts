import type { EvaluatedPoint } from './huanuco'

// Curated public reports. District proximity is context, never event confirmation.
interface Report {
  district: string
  date: string
  title: string
  source: string
  url: string
  kind: 'official' | 'news' | 'social'
  image?: string
}
export const reportKinds = { official: 'Reporte oficial', news: 'Noticia', social: 'Red social' }
const reports: Report[] = [
  { district: 'Tomay Kichwa', date: '2026-06-30', title: 'Incendio forestal en Las Pampas, Tomay Kichwa', source: 'COEN · INDECI', kind: 'official', url: 'https://portal.indeci.gob.pe/emergencias/reporte-complementario-n-o-8711-1-7-2026-coen-indeci-1432-horas-reporte-n-1-incendio-forestal-en-el-distrito-de-tomay-kichwa-huanuco/' },
  { district: 'La Union', date: '2026-08-12', title: 'Incendio forestal en Huánuco Pampa, La Unión', source: 'COEN · INDECI', kind: 'official', url: 'https://portal.indeci.gob.pe/emergencias/reporte-preliminar-n-o-0733-12-8-2026-coen-indeci-1930-horas-incendio-forestal-en-el-distrito-de-la-union-huanuco/' },
  { district: 'Amarilis', date: '2026-08-17', title: 'Incendio forestal en Fundo Pacán, Amarilis', source: 'COEN · INDECI', kind: 'official', url: 'https://portal.indeci.gob.pe/emergencias/reporte-complementario-n-o-10636-17-8-2026-coen-indeci-2045-horas-reporte-n-o-1-incendio-forestal-en-el-distrito-de-amarilis-huanuco/' },
  { district: 'Ambo', date: '2026-09-20', title: 'Incendio forestal en el sector Ponga, Ambo', source: 'COEN · INDECI', kind: 'official', url: 'https://portal.indeci.gob.pe/emergencias/reporte-preliminar-n-0895-20-9-2026-coen-indeci-2055-horas-incendio-forestal-en-el-distrito-de-ambo-huanuco/' },
  { district: '', date: '2026-07-11', title: 'COER reporta cuatro incendios forestales en Huánuco durante julio', source: 'Diario Ahora', kind: 'news', url: 'https://ahora.com.pe/regional/huanuco-periodo-mayor-riesgo-incendios-forestales' },
]
const normalize = (text: string) => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim()
export function relatedReports(point: EvaluatedPoint) {
  const sameDistrict = reports.filter(r => normalize(r.district) === normalize(point.district || ''))
  const candidates = sameDistrict.length ? sameDistrict : reports
  return [...candidates].sort((a, b) => Math.abs(Date.parse(a.date) - Date.parse(point.acquired_at)) - Math.abs(Date.parse(b.date) - Date.parse(point.acquired_at))).slice(0, 2).map(r => ({ ...r, context: sameDistrict.length ? 'Mismo distrito · vínculo sin verificar' : 'Contexto regional · vínculo sin verificar' }))
}
