import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
test('la interfaz consulta la API', () => { const app = readFileSync(new URL('../src/App.vue', import.meta.url), 'utf8'); assert.ok(app.includes('/api/fires?')); assert.ok(app.includes('/api/daily?')); assert.ok(app.includes('role="alert"')) })
