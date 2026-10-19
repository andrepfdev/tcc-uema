/**
 * Long Test — mesmo perfil do load.js com patamar de 30 min (crescimento de memória)
 *
 * Distribuição de endpoints:
 *   10% health  — latência base
 *   30% compute — CPU-bound puro (sem I/O)
 *   30% memory  — persistência de estado em memória
 *   30% db      — persistência de conexão PostgreSQL (principal diferencial Worker Mode)
 *
 * Métricas via Prometheus remote_write → Grafana: http://localhost:3000
 *
 * Execução:
 *   docker compose --profile scenario-X run --rm k6 \
 *     run /scripts/load.js -e TARGET_URL=http://app-X:8080
 */

import { testHealth, testCompute, testMemory, testDb } from './lib/endpoints.js';

export const options = {
  stages: [
    { duration: '2m',  target: 10  },  // aquecimento
    { duration: '2m',  target: 100 },  // rampa de carga
    { duration: '30m', target: 100 },  // pico sustentado (teste longo de memória)
    { duration: '1m',  target: 0   },  // desaceleração
  ],

  // Tag global: todas as métricas enviadas ao Prometheus carregam o label `scenario`.
  // Permite filtrar por cenário no Grafana mesmo com o TSDB acumulando múltiplos runs.
  tags: {
    scenario: __ENV.SCENARIO_NAME || 'unknown',
  },

  thresholds: {
    http_req_failed:             ['rate<0.05'],
    http_req_duration:           ['p(99)<5000'],
    'endpoint_health_duration':  ['p(95)<5000'],
    'endpoint_compute_duration': ['p(95)<5000'],
    'endpoint_memory_duration':  ['p(95)<5000'],
    'endpoint_db_duration':      ['p(95)<5000'],

    // Submétricas do PATAMAR (força o k6 a exportá-las no summary): RPS = contagem / duração do patamar
    'http_reqs{phase:plateau}':                    ['count>=0'],
    'http_req_failed{phase:plateau}':              ['rate<0.05'],
    'http_req_duration{phase:plateau}':            ['p(99)<60000'],
    'endpoint_health_duration{phase:plateau}':     ['p(99)<60000'],
    'endpoint_compute_duration{phase:plateau}':    ['p(99)<60000'],
    'endpoint_memory_duration{phase:plateau}':     ['p(99)<60000'],
    'endpoint_db_duration{phase:plateau}':         ['p(99)<60000'],
  },
};

export default function () {
  const rand = Math.random();

  if (rand < 0.10) {
    testHealth();
  } else if (rand < 0.40) {
    testCompute();
  } else if (rand < 0.70) {
    testMemory();
  } else {
    testDb();
  }
}
