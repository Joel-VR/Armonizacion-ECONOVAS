import test from 'node:test'
import assert from 'node:assert/strict'
import { detections, inPeriod } from '../src/data.ts'

test('las vistas no contienen detecciones ficticias', () => {
  assert.deepEqual(detections, [])
})
test('los filtros temporales no incluyen fechas futuras', () => {
  const tomorrow = new Date(Date.now() + 86400000).toISOString()
  assert.equal(inPeriod({ acquiredAt: tomorrow }, 'today'), false)
  assert.equal(inPeriod({ acquiredAt: tomorrow }, 'week'), false)
  assert.equal(inPeriod({ acquiredAt: tomorrow }, 'month'), false)
})
