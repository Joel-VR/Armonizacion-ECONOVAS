import test from 'node:test'
import assert from 'node:assert/strict'
import {
  getPixelCoords,
  getLandCoverMeta,
  classifyPoint,
  setMaskPixelData,
  LAND_COVER_CONFIG,
} from '../src/utils/mapbiomasClassifier.ts'

test('getPixelCoords calcula píxeles válidos dentro de Huánuco', () => {
  // Centro aproximado de Huánuco (-75.9, -9.4)
  const coords = getPixelCoords(-75.9, -9.4)
  assert.ok(coords !== null)
  assert.ok(coords.px >= 0 && coords.px < 2080)
  assert.ok(coords.py >= 0 && coords.py < 1632)
})

test('getPixelCoords devuelve null para puntos fuera de la cuadrícula', () => {
  const coords = getPixelCoords(0, 0) // Ecuador / Meridiano Greenwich
  assert.equal(coords, null)
})

test('getLandCoverMeta retorna configuración correcta para cada clase', () => {
  const forestMeta = getLandCoverMeta('forest')
  assert.equal(forestMeta.label, 'Bosque Natural')
  assert.equal(forestMeta.alertClass, 'danger')

  const agriMeta = getLandCoverMeta('agriculture')
  assert.equal(agriMeta.label, 'Zona Agropecuaria')
  assert.equal(agriMeta.alertClass, 'warning')

  const fallback = getLandCoverMeta('unknown_type')
  assert.equal(fallback.label, 'Otras Coberturas')
})

test('classifyPoint clasifica correctamente usando el buffer simulado', () => {
  // Crear un buffer simulado de 2080x1632 con 4 canales RGBA
  const testBuffer = new Uint8ClampedArray(2080 * 1632 * 4)

  // Obtener píxel para Tingo María (-75.99, -9.29)
  const coords = getPixelCoords(-75.99, -9.29)
  assert.ok(coords)

  const idx = (coords.py * 2080 + coords.px) * 4

  // 1. Simular Bosque (R = 255)
  testBuffer[idx] = 255
  testBuffer[idx + 1] = 0
  testBuffer[idx + 2] = 0
  testBuffer[idx + 3] = 255
  setMaskPixelData(testBuffer)
  assert.equal(classifyPoint(-75.99, -9.29), 'forest')

  // 2. Simular Zona Agropecuaria (G = 255)
  testBuffer[idx] = 0
  testBuffer[idx + 1] = 255
  testBuffer[idx + 2] = 0
  assert.equal(classifyPoint(-75.99, -9.29), 'agriculture')

  // 3. Simular Mosaico Mixto (B = 255)
  testBuffer[idx] = 0
  testBuffer[idx + 1] = 0
  testBuffer[idx + 2] = 255
  assert.equal(classifyPoint(-75.99, -9.29), 'mixed')

  // Limpiar
  setMaskPixelData(null)
})
