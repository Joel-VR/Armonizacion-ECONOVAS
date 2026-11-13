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
// Fixed, reproducible fixtures. These are NOT NASA observations or harmonized events.
export const DEMO_DATE = new Date('2026-11-13T23:59:59Z')
export const periodLabels: Record<Period, string> = {
  today: 'Hoy',
  week: 'Últimos 7 días',
  month: 'Este mes',
}
export const locations = [
  { department: 'Huánuco', country: 'PER', lat: -9.45, lng: -75.85 },
  { department: 'Ucayali', country: 'PER', lat: -9.22, lng: -73.65 },
  { department: 'Loreto', country: 'PER', lat: -4.6, lng: -74.3 },
  { department: 'Cusco', country: 'PER', lat: -12.5, lng: -72.6 },
  { department: 'Madre de Dios', country: 'PER', lat: -12.2, lng: -69.7 },
  { department: 'San Martín', country: 'PER', lat: -7.0, lng: -76.6 },
  { department: 'Junín', country: 'PER', lat: -11.2, lng: -74.7 },
  { department: 'Amazonas', country: 'PER', lat: -5.1, lng: -78.1 },
  { department: 'Mato Grosso', country: 'BRA', lat: -12.5, lng: -55.5 },
  { department: 'Santa Cruz', country: 'BOL', lat: -16.8, lng: -62.2 },
  { department: 'Caquetá', country: 'COL', lat: 1.0, lng: -74.4 },
  { department: 'Queensland', country: 'AUS', lat: -22.0, lng: 144.0 },
  { department: 'California', country: 'USA', lat: 38.0, lng: -121.0 },
] as const
export const detections: Detection[] = locations.flatMap((location, index) =>
  Array.from({ length: 7 }, (_, i) => {
    const sensor = i % 2 === 0 ? 'VIIRS' : 'MODIS'
    const date = new Date(Date.UTC(2026, 10, 13 - [0, 0, 1, 3, 6, 9, 12][i], 8 + i * 2, index * 3))
    return {
      id: `DEMO-${index}-${i}`,
      country: location.country,
      department: location.department,
      latitude: location.lat + ((i % 3) - 1) * 0.12,
      longitude: location.lng + ((i % 4) - 1.5) * 0.13,
      acquiredAt: date.toISOString(),
      sensor,
      satellite: sensor === 'VIIRS' ? 'Suomi NPP' : 'Aqua',
      confidence: sensor === 'VIIRS' ? ['Nominal', 'Alta', 'Baja'][i % 3] : `${65 + i * 5}%`,
      frp: [4.2, 12.8, 35.1, 8.6, 24.3, 46.7, 3.1][(i + index) % 7],
      brightness: 310 + i * 7.6,
      scan: sensor === 'VIIRS' ? 0.42 : 1.1,
      track: sensor === 'VIIRS' ? 0.39 : 1.05,
      daynight: i % 3 ? 'D' : 'N',
    }
  }),
)
export function inPeriod(d: Detection, period: Period) {
  const day = d.acquiredAt.slice(0, 10)
  return period === 'today'
    ? day === '2026-11-13'
    : period === 'week'
      ? day >= '2026-11-07' && day <= '2026-11-13'
      : day.startsWith('2026-11-') && day <= '2026-11-13'
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
