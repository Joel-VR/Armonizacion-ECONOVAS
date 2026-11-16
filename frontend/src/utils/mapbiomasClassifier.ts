export type LandCoverType = 'forest' | 'agriculture' | 'mixed' | 'other' | 'outside'

export interface LandCoverMeta {
  type: LandCoverType
  label: string
  shortLabel: string
  color: string
  badge: string
  icon: string
  description: string
  alertClass: 'danger' | 'warning' | 'info' | 'neutral'
  badgeCategory: 'forestal' | 'agricola' | 'mixto' | 'otro'
}

export const LAND_COVER_CONFIG: Record<LandCoverType, LandCoverMeta> = {
  forest: {
    type: 'forest',
    label: 'Bosque Natural',
    shortLabel: 'Bosque',
    color: '#298743',
    badge: 'Alerta Crítica / Riesgo Forestal',
    icon: '🌲',
    description: 'Área clasificada como bosque continuo según MapBiomas Perú Colección 4 (2025). Requiere máxima prioridad de atención de SERFOR y Guardaparques.',
    alertClass: 'danger',
    badgeCategory: 'forestal',
  },
  agriculture: {
    type: 'agriculture',
    label: 'Zona Agropecuaria',
    shortLabel: 'Cultivos',
    color: '#d4a017',
    badge: 'Quema de Rastrojo / Manejo Agrícola',
    icon: '🌾',
    description: 'Área de cultivo o uso agropecuario según MapBiomas Perú Colección 4 (2025). Típicamente corresponde a quema de rastrojos o preparación de terreno.',
    alertClass: 'warning',
    badgeCategory: 'agricola',
  },
  mixed: {
    type: 'mixed',
    label: 'Mosaico Agro-forestal',
    shortLabel: 'Mosaico mixto',
    color: '#c49a45',
    badge: 'Transición Agro-forestal',
    icon: '🏞️',
    description: 'Mosaico mixto de vegetación secundaria y parcelas según MapBiomas Perú Colección 4 (2025). Zona de interfase agrícola-boscosa.',
    alertClass: 'info',
    badgeCategory: 'mixto',
  },
  other: {
    type: 'other',
    label: 'Otras Coberturas',
    shortLabel: 'Otras',
    color: '#64748b',
    badge: 'Pastizales / Vegetación No Leñosa',
    icon: '🍂',
    description: 'Pastizales, vegetación arbustiva u otras coberturas no boscosas según MapBiomas Perú Colección 4 (2025).',
    alertClass: 'neutral',
    badgeCategory: 'otro',
  },
  outside: {
    type: 'outside',
    label: 'Fuera de Huánuco',
    shortLabel: 'Exterior',
    color: '#94a3b8',
    badge: 'Sin Clasificación Territorial',
    icon: '📍',
    description: 'Coordenadas situadas fuera del ámbito raster departamental de Huánuco.',
    alertClass: 'neutral',
    badgeCategory: 'otro',
  },
}

// Bounding parameters in Web Mercator (EPSG:3857) matching MapBiomas Huánuco raster
const X_MIN = -8607450
const Y_MAX = -928765
const RESOLUTION = 150
const WIDTH = 2080
const HEIGHT = 1632

export function getPixelCoords(lon: number, lat: number): { px: number; py: number } | null {
  const x = (lon * 20037508.34) / 180
  const y = (Math.log(Math.tan(((90 + lat) * Math.PI) / 360)) / (Math.PI / 180) * 20037508.34) / 180
  const px = Math.floor((x - X_MIN) / RESOLUTION)
  const py = Math.floor((Y_MAX - y) / RESOLUTION)
  if (px < 0 || px >= WIDTH || py < 0 || py >= HEIGHT) {
    return null
  }
  return { px, py }
}

let maskPixelData: Uint8ClampedArray | null = null
let loadingPromise: Promise<boolean> | null = null

export function isMapBiomasLoaded(): boolean {
  return maskPixelData !== null
}

export function setMaskPixelData(data: Uint8ClampedArray | null): void {
  maskPixelData = data
}

export async function loadMapBiomasMask(url = '/geo/huanuco/mapbiomas-rgb-mask.png'): Promise<boolean> {
  if (maskPixelData) return true
  if (loadingPromise) return loadingPromise

  loadingPromise = (async () => {
    if (typeof window === 'undefined' || typeof document === 'undefined') {
      return false
    }
    try {
      const img = new Image()
      img.crossOrigin = 'anonymous'
      img.src = url
      await new Promise<void>((resolve, reject) => {
        img.onload = () => resolve()
        img.onerror = () => reject(new Error('Failed to load MapBiomas mask image'))
      })

      const canvas = document.createElement('canvas')
      canvas.width = WIDTH
      canvas.height = HEIGHT
      const ctx = canvas.getContext('2d', { willReadFrequently: true })
      if (!ctx) return false

      ctx.drawImage(img, 0, 0)
      const imgData = ctx.getImageData(0, 0, WIDTH, HEIGHT)
      maskPixelData = imgData.data
      return true
    } catch (e) {
      console.warn('MapBiomas mask could not be loaded:', e)
      return false
    }
  })()

  return loadingPromise
}

export function classifyPoint(lon: number, lat: number): LandCoverType {
  const coords = getPixelCoords(lon, lat)
  if (!coords) return 'outside'
  if (!maskPixelData) return 'other'

  const { px, py } = coords
  const idx = (py * WIDTH + px) * 4
  const r = maskPixelData[idx]
  const g = maskPixelData[idx + 1]
  const b = maskPixelData[idx + 2]

  if (r > 128) return 'forest'
  if (g > 128) return 'agriculture'
  if (b > 128) return 'mixed'
  return 'other'
}

export function getLandCoverMeta(type: string | null | undefined, locale: 'en' | 'es' = 'es'): LandCoverMeta {
  const key = type && type in LAND_COVER_CONFIG ? type as LandCoverType : 'other'
  const meta = LAND_COVER_CONFIG[key]
  if (locale === 'es') return meta
  const english: Record<LandCoverType, Pick<LandCoverMeta, 'label' | 'shortLabel' | 'badge' | 'description'>> = {
    forest: { label: 'Natural forest', shortLabel: 'Forest', badge: 'Critical alert / Forest risk', description: 'Area classified as continuous forest by MapBiomas Peru Collection 4 (2025). Requires the highest priority attention from SERFOR and park rangers.' },
    agriculture: { label: 'Agricultural area', shortLabel: 'Crops', badge: 'Crop residue burning / Agricultural management', description: 'Crop or agricultural land according to MapBiomas Peru Collection 4 (2025). Typically associated with crop residue burning or land preparation.' },
    mixed: { label: 'Agroforestry mosaic', shortLabel: 'Mixed mosaic', badge: 'Agroforestry transition', description: 'Mixed mosaic of secondary vegetation and plots according to MapBiomas Peru Collection 4 (2025). Agricultural-forest interface.' },
    other: { label: 'Other land cover', shortLabel: 'Other', badge: 'Grassland / Non-woody vegetation', description: 'Grassland, shrub vegetation or other non-forest cover according to MapBiomas Peru Collection 4 (2025).' },
    outside: { label: 'Outside Huánuco', shortLabel: 'Outside', badge: 'No land classification', description: 'Coordinates outside the Huánuco departmental raster extent.' },
  }
  return { ...meta, ...english[key] }
}
