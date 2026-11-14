import test from 'node:test'
import assert from 'node:assert/strict'
import { percent } from '../src/huanuco.ts'

test('presenta percentiles y ausencias sin inventar ceros', () => {
  assert.equal(percent(null), '—')
  assert.equal(percent(0), '0%')
  assert.equal(percent(0.255), '26%')
})
