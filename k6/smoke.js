/**
 * Smoke Test — Sanidade do ambiente
 *
 * Propósito: verificar que o cenário está funcionando corretamente
 * antes de iniciar um load test real. Carga mínima (1 VU, 1 minuto).
 *
 * Execução:
 *   docker compose --profile scenario-X run --rm k6 \
 *     run /scripts/smoke.js -e TARGET_URL=http://app-X:8080
 */

import { sleep } from 'k6';
import { testHealth, testCompute, testMemory } from './lib/endpoints.js';

export const options = {
  vus:      1,
  duration: '1m',

  thresholds: {
    http_req_failed:              ['rate<0.01'],   // < 1% de erros
    http_req_duration:            ['p(95)<500'],   // p95 < 500ms
    'endpoint_health_duration':   ['p(95)<100'],   // /health deve ser muito rápido
    'endpoint_compute_duration':  ['p(95)<1000'],  // /compute pode ser mais pesado
    'endpoint_memory_duration':   ['p(95)<200'],   // /memory é leve
  },
};

export default function () {
  testHealth();
  sleep(0.1);

  testCompute();
  sleep(0.1);

  testMemory();
  sleep(0.1);
}
