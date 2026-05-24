/**
 * Load Test — Teste de carga principal do TCC
 *
 * Cenários de rampa:
 *   - Aquecimento:  2 min  → 10 VUs   (warm-up do OPcache e do Worker loop)
 *   - Rampa:        3 min  → 100 VUs  (incremento gradual)
 *   - Pico:        10 min  @ 100 VUs  (carga sustentada — dados principais do TCC)
 *   - Desaceleração: 1 min →  0 VUs
 *
 * Métricas coletadas via Prometheus remote_write (K6_PROMETHEUS_RW_SERVER_URL)
 * Visualizadas em tempo real no Grafana: http://localhost:3000
 *
 * Execução:
 *   docker compose --profile scenario-X run --rm k6 \
 *     run /scripts/load.js -e TARGET_URL=http://app-X:8080
 */

import { sleep } from 'k6';
import { testHealth, testCompute, testMemory } from './lib/endpoints.js';

export const options = {
  stages: [
    { duration: '2m',  target: 10  },   // aquecimento
    { duration: '3m',  target: 100 },   // rampa de carga
    { duration: '10m', target: 100 },   // pico sustentado
    { duration: '1m',  target: 0   },   // desaceleração
  ],

  thresholds: {
    // Critérios de aceitação globais
    http_req_failed:   ['rate<0.05'],    // < 5% de erros totais
    http_req_duration: ['p(99)<2000'],   // p99 < 2s

    // Por endpoint
    'endpoint_health_duration':   ['p(95)<200'],
    'endpoint_compute_duration':  ['p(95)<2000'],
    'endpoint_memory_duration':   ['p(95)<500'],
  },
};

export default function () {
  // Distribuição de carga: simula tráfego misto entre os 3 endpoints
  const rand = Math.random();

  if (rand < 0.2) {
    // 20% — health check (latência base)
    testHealth();
  } else if (rand < 0.6) {
    // 40% — compute (CPU-bound, principal diferenciador de throughput)
    testCompute();
  } else {
    // 40% — memory (demonstra persistência de estado no Worker Mode)
    testMemory();
  }

  // Sem sleep: simula carga contínua para maximizar RPS medido
}
