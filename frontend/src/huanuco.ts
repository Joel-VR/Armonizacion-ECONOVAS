export type Sensor = 'MODIS' | 'VIIRS'
export interface SensorWeek { cells: number | null; percentile: number | null; sample: number; years: number; ties: number | null }
export interface Week { start: string; end: string; week: number; sensors: Record<Sensor, SensorWeek>; combined: number | null; disagreement: number | null }
export interface Daily { day: string; sensor: Sensor; detections: number }
export interface Analysis { weekly: Week[]; daily: Daily[]; starts: Record<Sensor, string>; ends: Record<Sensor, string>; grid_km: number; year: number }
export interface Point { id: number; latitude: number; longitude: number; acquired_at: string; sensor: Sensor; satellite: string; confidence: string; frp: number | null; version: string; source_kind: string }
export const percent = (x: number | null) => x === null ? '—' : Math.round(x * 100) + '%'
export const dateText = (x: string) => new Intl.DateTimeFormat('es-PE', {day:'numeric',month:'short',timeZone:'UTC'}).format(new Date(x.slice(0,10)+'T00:00:00Z'))
