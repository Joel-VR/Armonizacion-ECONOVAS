import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import union from '@turf/union'
import { detections, inPeriod, frpColor } from '../src/data.ts'

test('los periodos incluyen sus límites y no incorporan fechas futuras', () => {
  const record = { ...detections[0] }
  assert.equal(inPeriod({ ...record, acquiredAt: '2026-11-07T00:00:00Z' }, 'week'), true)
  assert.equal(inPeriod({ ...record, acquiredAt: '2026-11-06T23:59:59Z' }, 'week'), false)
  assert.equal(inPeriod({ ...record, acquiredAt: '2026-11-14T00:00:00Z' }, 'week'), false)
  assert.equal(inPeriod({ ...record, acquiredAt: '2026-11-14T00:00:00Z' }, 'month'), false)
  assert.equal(inPeriod({ ...record, acquiredAt: '2026-10-31T23:59:59Z' }, 'month'), false)
  assert.equal(inPeriod({ ...record, acquiredAt: '2026-11-12T23:59:59Z' }, 'today'), false)
})

test('los resúmenes por territorio coinciden con las observaciones filtradas', () => {
  const peru = detections.filter((d) => d.country === 'PER')
  assert.equal(peru.filter((d) => inPeriod(d, 'today')).length, 16)
  assert.equal(peru.filter((d) => inPeriod(d, 'week')).length, 40)
  assert.equal(peru.filter((d) => inPeriod(d, 'month')).length, 56)
  assert.equal(new Set(peru.map((d) => d.department)).size, 8)
  assert.equal(detections.filter((d) => inPeriod(d, 'week')).length, 65)
  assert.equal(new Set(detections.map((d) => d.id)).size, detections.length)
})

test('la leyenda separa FRP en los límites de 10 y 30 MW', () => {
  assert.equal(frpColor(9.9), '#f5c928')
  assert.equal(frpColor(10), '#f58a26')
  assert.equal(frpColor(29.9), '#f58a26')
  assert.equal(frpColor(30), '#e3323b')
})

test('la cartografía de Perú puede disolverse para ocultar países adyacentes', () => {
  const peru = JSON.parse(
    readFileSync(new URL('../public/geo/peru-departments.geojson', import.meta.url)),
  )
  // This administrative dataset separates metropolitan Lima from Lima region.
  assert.equal(peru.features.length, 26)
  assert.ok(peru.features.some((f) => f.properties.shapeName === 'Huánuco'))
  const dissolved = union(peru)
  assert.ok(dissolved && ['Polygon', 'MultiPolygon'].includes(dissolved.geometry.type))
})
