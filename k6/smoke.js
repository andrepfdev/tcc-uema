/**
 * Smoke Test — Sanidade do ambiente
 *
 * Execução:
 *   docker compose --profile scenario-X run --rm k6 \
 *     run /scripts/smoke.js -e TARGET_URL=http://app-X:8080
 */

import { sleep } from 'k6';
import { testHealth, testCompute, testMemory, testDb } from './lib/endpoints.js';

export const options = {
  vus:      1,
  duration: '1m',

  thresholds: {
    http_req_failed:             ['rate<0.01'],
    http_req_duration:           ['p(95)<500'],
    'endpoint_health_duration':  ['p(95)<100'],
    'endpoint_compute_duration': ['p(95)<1000'],
    'endpoint_memory_duration':  ['p(95)<200'],
    'endpoint_db_duration':      ['p(95)<300'],
  },
};

export default function () {
  testHealth();
  sleep(0.1);

  testCompute();
  sleep(0.1);

  testMemory();
  sleep(0.1);

  testDb();
  sleep(0.1);
}
