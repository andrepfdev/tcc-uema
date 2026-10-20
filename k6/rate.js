/**
 * Rate Test — carga de taxa de chegada fixa (modelo aberto)
 *
 * Mesma mistura de endpoints do load.js (10% health, 30% compute, 30% memory, 30% db), mas com
 * taxa de requisições constante (RATE, padrão 100/s), independente da latência das respostas.
 * Com a taxa abaixo da capacidade de todos os cenários, a latência mede o tempo de serviço
 * e não o tempo de fila (no modelo fechado do load.js, a latência acompanha a vazão: L = N / X).
 *
 * Fases (reusa phase() de lib/endpoints.js): aquecimento WARMUP_S, depois patamar PLATEAU_S.
 * Validade: dropped_iterations deve ser 0 (se > 0, a taxa pedida não foi sustentada).
 *
 * Execução:
 *   RATE=100 WARMUP_S=60 RAMP_S=0 PLATEAU_S=480 ./scripts/run-scenario.sh <a|b|c|d|e> rate
 */

import { testHealth, testCompute, testMemory, testDb } from './lib/endpoints.js';

const RATE      = Number(__ENV.RATE      || 100);
const WARMUP_S  = Number(__ENV.WARMUP_S  || 60);
const RAMP_S    = Number(__ENV.RAMP_S    || 0);
const PLATEAU_S = Number(__ENV.PLATEAU_S || 480);

export const options = {
  scenarios: {
    default: {
      executor: 'constant-arrival-rate',
      rate: RATE,
      timeUnit: '1s',
      duration: `${WARMUP_S + RAMP_S + PLATEAU_S}s`,
      preAllocatedVUs: 100,
      maxVUs: 400,
    },
  },

  tags: {
    scenario: __ENV.SCENARIO_NAME || 'unknown',
  },

  thresholds: {
    http_req_failed:             ['rate<0.05'],
    http_req_duration:           ['p(99)<5000'],

    // Submétricas do PATAMAR (força o k6 a exportá-las no summary)
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
