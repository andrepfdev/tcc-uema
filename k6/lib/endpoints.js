import http from 'k6/http';
import { check } from 'k6';
import { Trend } from 'k6/metrics';
import exec from 'k6/execution';

export const healthDuration  = new Trend('endpoint_health_duration',  true);
export const computeDuration = new Trend('endpoint_compute_duration', true);
export const memoryDuration  = new Trend('endpoint_memory_duration',  true);
export const dbDuration      = new Trend('endpoint_db_duration',      true);

const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8080';

// Fase do teste, por tempo decorrido (s): warmup -> ramp -> plateau -> rampdown.
// Padrão = stages de load.js (2m + 2m + 10m + 1m). O patamar (plateau) é a janela de análise dos resultados.
const WARMUP_S  = Number(__ENV.WARMUP_S  || 120);
const RAMP_S    = Number(__ENV.RAMP_S    || 120);
const PLATEAU_S = Number(__ENV.PLATEAU_S || 600);
export function phase() {
  const t = exec.instance.currentTestRunDuration / 1000;
  if (t < WARMUP_S) return 'warmup';
  if (t < WARMUP_S + RAMP_S) return 'ramp';
  if (t < WARMUP_S + RAMP_S + PLATEAU_S) return 'plateau';
  return 'rampdown';
}

export function testHealth() {
  const ph = phase();
  const res = http.get(`${BASE_URL}/health`, { tags: { endpoint: 'health', phase: ph } });
  healthDuration.add(res.timings.duration, { phase: ph });
  check(res, {
    'health: status 200':         (r) => r.status === 200,
    'health: body has status ok': (r) => r.json('status') === 'ok',
  });
  return res;
}

export function testCompute() {
  const ph = phase();
  const res = http.get(`${BASE_URL}/compute`, { tags: { endpoint: 'compute', phase: ph } });
  computeDuration.add(res.timings.duration, { phase: ph });
  check(res, {
    'compute: status 200':          (r) => r.status === 200,
    'compute: body has data array': (r) => Array.isArray(r.json('data')),
  });
  return res;
}

export function testMemory() {
  const ph = phase();
  const res = http.get(`${BASE_URL}/memory`, { tags: { endpoint: 'memory', phase: ph } });
  memoryDuration.add(res.timings.duration, { phase: ph });
  check(res, {
    'memory: status 200':     (r) => r.status === 200,
    'memory: counter exists': (r) => r.json('counter') > 0,
    'memory: pid exists':     (r) => r.json('pid') > 0,
  });
  return res;
}

export function testDb() {
  const ph = phase();
  const res = http.get(`${BASE_URL}/db`, { tags: { endpoint: 'db', phase: ph } });
  dbDuration.add(res.timings.duration, { phase: ph });
  check(res, {
    'db: status 200':      (r) => r.status === 200,
    'db: item returned':   (r) => r.json('item') !== null,
    'db: item has id':     (r) => r.json('item.id') > 0,
  });
  return res;
}
