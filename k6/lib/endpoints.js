import http from 'k6/http';
import { check } from 'k6';
import { Trend } from 'k6/metrics';

export const healthDuration  = new Trend('endpoint_health_duration',  true);
export const computeDuration = new Trend('endpoint_compute_duration', true);
export const memoryDuration  = new Trend('endpoint_memory_duration',  true);

const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8080';

export function testHealth() {
  const res = http.get(`${BASE_URL}/health`, { tags: { endpoint: 'health' } });
  healthDuration.add(res.timings.duration);
  check(res, {
    'health: status 200':          (r) => r.status === 200,
    'health: body has status ok':  (r) => r.json('status') === 'ok',
  });
  return res;
}

export function testCompute() {
  const res = http.get(`${BASE_URL}/compute`, { tags: { endpoint: 'compute' } });
  computeDuration.add(res.timings.duration);
  check(res, {
    'compute: status 200':         (r) => r.status === 200,
    'compute: body has data array':(r) => Array.isArray(r.json('data')),
  });
  return res;
}

export function testMemory() {
  const res = http.get(`${BASE_URL}/memory`, { tags: { endpoint: 'memory' } });
  memoryDuration.add(res.timings.duration);
  check(res, {
    'memory: status 200':          (r) => r.status === 200,
    'memory: counter exists':      (r) => r.json('counter') > 0,
    'memory: pid exists':          (r) => r.json('pid') > 0,
  });
  return res;
}
