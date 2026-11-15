export type Sensor = 'MODIS' | 'VIIRS'
export interface SensorWeek {
  cells: number | null
  percentile: number | null
  sample: number
  years: number
  ties: number | null
}
export interface Week {
  start: string
  end: string
  week: number
  sensors: Record<Sensor, SensorWeek>
  combined: number | null
  disagreement: number | null
}
export interface Daily {
  day: string
  sensor: Sensor
  detections: number
}
export interface Analysis {
  weekly: Week[]
  daily: Daily[]
  starts: Record<Sensor, string>
  ends: Record<Sensor, string>
  grid_km: number | null
  year: number
}
export type Decision = 'candidate' | 'review' | 'excluded'
export type Cover = 'forest' | 'agriculture' | 'water' | 'urban' | 'other' | 'unknown' | 'mixed'
export const coverLabels: Record<Cover, string> = {
  forest: 'Bosque',
  agriculture: 'Agrícola',
  water: 'Agua',
  urban: 'Urbano',
  other: 'Otras coberturas',
  unknown: 'Sin clasificación',
  mixed: 'Mosaico mixto',
}
export const decisionLabels: Record<Decision, string> = {
  candidate: 'Eventos probables',
  review: 'Por revisar',
  excluded: 'Excluidos por tipo NASA',
}
export interface LandCover {
  ready: boolean
  year: number
  collection: number
  layer_id: string
  source_url: string
  display_resolution_m: number
  coordinates: [number, number][]
  layers: { id: Cover; label: string; color: string; url: string }[]
  warning: string
}
export interface ScreenedAnalysis extends Analysis {
  event_count: number
  event_daily: { day: string; tipo: string; events: number }[]
  counts: Record<Decision, number>
  total_selected: number
  reference: LandCover
  limitations: string[]
}
export interface EvaluatedPoint extends Point {
  event_type: string
  verification_status: string
  country: string
  department: string
  province: string | null
  district: string | null
  biome: string | null
  observation_count: number
  ultima_deteccion: string
  representative_id: number
  fire_type: string | null
  brightness: number | null
  scan: number | null
  track: number | null
  daynight: string
  cover_category: Cover
  cover_code: number
  decision: Decision
  reason: string
  rule_version: string
}
export interface Point {
  id: number
  latitude: number
  longitude: number
  acquired_at: string
  sensor: Sensor
  satellite: string
  confidence: string
  frp: number | null
  version: string
  source_kind: string
}
export const percent = (x: number | null) => (x === null ? '—' : Math.round(x * 100) + '%')
export const dateText = (x: string) =>
  new Intl.DateTimeFormat('es-PE', { day: 'numeric', month: 'short', timeZone: 'UTC' }).format(
    new Date(x.slice(0, 10) + 'T00:00:00Z'),
  )

export interface MonthCalendarCell {
  year: number
  month: number
  month_name: string
  month_short: string
  harmonized_index: number | null
  historical_median: number | null
  baseline_p25?: number | null
  baseline_p75?: number | null
  anomaly_delta: number | null
  anomaly_pct: number | null
  anomaly_status: 'sin_datos' | 'unusually_low' | 'normal' | 'elevated' | 'critical'
  modis_cells: number
  viirs_cells: number
  total_cells: number
  weeks_count: number
  is_peak_season: boolean
  is_unusual_timing: boolean
  is_baseline_year: boolean
}

export interface MonthlyBaseline {
  month: number
  name: string
  short: string
  baseline: {
    median: number | null
    p25: number | null
    p75: number | null
    min: number | null
    max: number | null
  }
}

export interface BurnCalendarData {
  department: { code: string; name: string; srid: number }
  years: number[]
  months: MonthlyBaseline[]
  matrix: Record<string, MonthCalendarCell[]>
  peak_season: number[]
  highest_month: {
    year: number
    month: number
    month_name: string
    value: number
    anomaly_pct: number
  } | null
  critical_count: number
  alerts: string[]
  methodology: {
    reference_period: string
    grid_km: number
    sensors: string
    anomaly_formula: string
  }
}
