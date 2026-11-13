export type Period = 'today' | 'week' | 'month'
export type Scope = 'country' | 'world'
export interface Detection {
  id: string
  country: string
  department: string
  latitude: number
  longitude: number
  acquiredAt: string
  sensor: 'MODIS' | 'VIIRS'
  satellite: string
  confidence: string
  frp: number
  brightness: number
  scan: number
  track: number
  daynight: 'D' | 'N'
}
export const periodLabels: Record<Period, string> = {
  today: 'Hoy', week: 'Últimos 7 días', month: 'Este mes',
}
// Las vistas anteriores están pendientes de conexión a la API real.
export const detections: Detection[] = []
export function inPeriod(d: Detection, period: Period) {
  const today = new Date().toISOString().slice(0, 10)
  const first = new Date(today + 'T00:00:00Z')
  if (period === 'week') first.setUTCDate(first.getUTCDate() - 6)
  if (period === 'month') first.setUTCDate(1)
  const day = d.acquiredAt.slice(0, 10)
  return day >= first.toISOString().slice(0, 10) && day <= today
}
export function frpColor(frp: number) {
  return frp < 10 ? '#f5c928' : frp < 30 ? '#f58a26' : '#e3323b'
}
export function dateLabel(value: string) {
  return (
    new Intl.DateTimeFormat('es-PE', {
      dateStyle: 'medium',
      timeStyle: 'short',
      timeZone: 'UTC',
    }).format(new Date(value)) + ' UTC'
  )
}
