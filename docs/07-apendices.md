## APÊNDICES

### APÊNDICE A — Orquestração dos contêineres (docker-compose.yml)

**docker-compose.yml**

```yaml
services:

  # ===========================================================================
  # CENÁRIO A — Legacy: CodeIgniter 4 + PHP-FPM (Alpine) + Nginx
  # Topologia real de produção PHP tradicional
  # ===========================================================================
  app-a:
    profiles: [scenario-a]
    build:
      context: .
      dockerfile: docker/scenario-a/Dockerfile
    expose:
      - "9000"
    deploy:
      resources:
        limits:
          # 0.85 CPU / 448MB — orçamento do processo PHP-FPM
          # nginx-a recebe 0.15 CPU / 64MB: juntos totalizam 1.0 CPU / 512MB
          # Isso iguala o orçamento total do Cenário A aos demais (B, C, D)
          cpus: "0.85"
          memory: "448M"
    environment:
      SCENARIO_NAME: scenario-a
      COMPUTE_SIZE: "1000"
      CI_ENVIRONMENT: production
    volumes:
      - ./docker/scenario-a/php-fpm.conf:/usr/local/etc/php-fpm.d/www.conf
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - bench-net
    restart: unless-stopped

  nginx-a:
    profiles: [scenario-a]
    image: nginx:alpine
    ports:
      - "8080:8080"
    deploy:
      resources:
        limits:
          # 0.15 CPU / 64MB — orçamento do reverse proxy Nginx
          # Nginx é muito leve; esse limite reflete seu papel no stack
          # Total Cenário A: app-a (0.85/448M) + nginx-a (0.15/64M) = 1.0 CPU / 512MB
          cpus: "0.15"
          memory: "64M"
    volumes:
      - ./docker/scenario-a/nginx.conf:/etc/nginx/conf.d/default.conf
      - ./apps/ci4-base/public:/var/www/html/public:ro
    depends_on:
      - app-a
    networks:
      - bench-net
    restart: unless-stopped

  # ===========================================================================
  # CENÁRIO B — Modern Classic: CodeIgniter 4 + FrankenPHP Classic Mode
  # FrankenPHP como substituto do PHP-FPM (sem Worker, sem estado persistente)
  # Isola o ganho do motor FrankenPHP vs o Worker Mode em si
  # ===========================================================================
  app-b:
    profiles: [scenario-b]
    build:
      context: .
      dockerfile: docker/scenario-b/Dockerfile
    ports:
      - "8080:8080"
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: "512M"
    environment:
      SCENARIO_NAME: scenario-b
      COMPUTE_SIZE: "1000"
      CI_ENVIRONMENT: production
      SERVER_NAME: ":8080"
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - bench-net
    restart: unless-stopped

  # ===========================================================================
  # CENÁRIO C — Vanguard: CodeIgniter 4 + FrankenPHP Worker Mode
  # Bridge customizada mantém o CI4 em memória persistente entre requests
  # Este é o cenário central do TCC
  # ===========================================================================
  app-c:
    profiles: [scenario-c]
    build:
      context: .
      dockerfile: docker/scenario-c/Dockerfile
    ports:
      - "8080:8080"
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: "512M"
    environment:
      SCENARIO_NAME: scenario-c
      COMPUTE_SIZE: "1000"
      CI_ENVIRONMENT: production
      SERVER_NAME: ":8080"
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - bench-net
    restart: unless-stopped

  # ===========================================================================
  # CENÁRIO D — Referência: Laravel + Laravel Octane + FrankenPHP
  # Benchmark de mercado — Octane suporta Worker Mode nativamente
  # ===========================================================================
  app-d:
    profiles: [scenario-d]
    build:
      context: .
      dockerfile: docker/scenario-d/Dockerfile
    ports:
      - "8080:8080"
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: "512M"
    environment:
      SCENARIO_NAME: scenario-d
      COMPUTE_SIZE: "1000"
      APP_ENV: production
      APP_DEBUG: "false"
      OCTANE_SERVER: frankenphp
      SERVER_NAME: ":8080"
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - bench-net
    restart: unless-stopped

  # ===========================================================================
  # BANCO DE DADOS — PostgreSQL 16
  # Compartilhado entre todos os cenários (roda um de cada vez via profiles)
  # Recurso isolado: NÃO conta no orçamento de 1.0 CPU / 512MB dos apps
  #
  # Por que PostgreSQL para o benchmark:
  #   - Modelo process-per-connection (~5-10MB RAM/conexão) torna o custo de
  #     abrir uma nova conexão mais caro que MySQL (thread-based)
  #   - Amplifica exatamente o diferencial do Worker Mode (conexão persistente)
  #   - Cenário A (PHP-FPM): nova conexão PG por request = overhead mensurável
  #   - Cenário C (Worker Mode): conexão reutilizada = sem overhead de handshake
  # ===========================================================================
  postgres:
    profiles: [scenario-a, scenario-b, scenario-c, scenario-d]
    image: postgres:16-alpine
    environment:
      POSTGRES_DB:       benchmark
      POSTGRES_USER:     benchmark
      POSTGRES_PASSWORD: benchmark
    command: >
      postgres
        -c max_connections=20
        -c shared_buffers=64MB
        -c log_min_messages=WARNING
    volumes:
      - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U benchmark -d benchmark"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 10s
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: "256M"
    networks:
      - bench-net
    restart: unless-stopped

  # ===========================================================================
  # INJETOR DE CARGA — Grafana k6
  # 2.0 CPU / 512MB RAM conforme especificado no TCC
  # Executa apenas via `docker compose run --rm k6 run /scripts/...`
  # ===========================================================================
  k6:
    profiles: [scenario-a, scenario-b, scenario-c, scenario-d]
    image: grafana/k6:latest
    user: root
    volumes:
      - ./k6:/scripts
      - ./results:/results
    environment:
      K6_PROMETHEUS_RW_SERVER_URL: http://prometheus:9090/api/v1/write
      K6_PROMETHEUS_RW_TREND_AS_NATIVE_HISTOGRAM: "true"
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: "512M"
    networks:
      - bench-net
    depends_on:
      - prometheus

  # ===========================================================================
  # OBSERVABILIDADE
  # ===========================================================================

  prometheus:
    profiles: [scenario-a, scenario-b, scenario-c, scenario-d]
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--web.enable-remote-write-receiver"
      - "--storage.tsdb.retention.time=7d"
    networks:
      - bench-net
    restart: unless-stopped

  grafana:
    profiles: [scenario-a, scenario-b, scenario-c, scenario-d]
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: benchmark
      GF_AUTH_ANONYMOUS_ENABLED: "true"
      GF_AUTH_ANONYMOUS_ORG_ROLE: Viewer
      GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH: /var/lib/grafana/dashboards/benchmark.json
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
      - grafana-data:/var/lib/grafana
    networks:
      - bench-net
    depends_on:
      - prometheus
    restart: unless-stopped

  # cAdvisor — expõe CPU/RAM dos containers em formato Prometheus
  cadvisor:
    profiles: [scenario-a, scenario-b, scenario-c, scenario-d]
    image: gcr.io/cadvisor/cadvisor:latest
    ports:
      - "8081:8080"
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
    networks:
      - bench-net
    restart: unless-stopped

networks:
  bench-net:
    driver: bridge

volumes:
  prometheus-data:
  grafana-data:
  postgres-data:
```

### APÊNDICE B — Configuração dos servidores e imagens dos cenários

**docker/scenario-a/Dockerfile**

```
FROM php:8.3-fpm-alpine

# icu-dev: necessário para ext-intl (requerida pelo CI4)
# libpq-dev: necessário para ext-pgsql/pdo_pgsql
RUN apk add --no-cache icu-dev libpq-dev git unzip \
    && docker-php-ext-install opcache intl pgsql pdo_pgsql

# OPcache para benchmark justo (Scenario A recebe todos os otimizadores que tem direito)
COPY docker/scenario-a/opcache.ini /usr/local/etc/php/conf.d/opcache.ini

# Instalar composer
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

WORKDIR /var/www/html

# Copiar código da aplicação
COPY apps/ci4-base/ .

# Instalar dependências
RUN composer install --no-dev --optimize-autoloader --no-interaction --no-scripts

# Permissões de escrita para o CI4
RUN mkdir -p writable/{cache,logs,session,uploads,debugbar} \
    && chmod -R 777 writable/

# Variáveis de ambiente sobrescritas pelo docker-compose
ENV SCENARIO_NAME=scenario-a
ENV COMPUTE_SIZE=1000
ENV CI_ENVIRONMENT=production

EXPOSE 9000
CMD ["php-fpm"]
```

**docker/scenario-a/php-fpm.conf**

```
[www]
user  = www-data
group = www-data

listen = 0.0.0.0:9000

; Pool estático com 4 workers — mesma contagem dos Workers nos Cenários B/C/D
; Variável controlada nos 4 cenários para comparação justa
pm = static
pm.max_children = 4

; Desabilitar logs de acesso do FPM (reduz I/O nas medições)
access.log = /dev/null
```

**docker/scenario-a/nginx.conf**

```
server {
    listen 8080;
    root /var/www/html/public;
    index index.php;

    # Desabilita access log para eliminar I/O de disco das medições
    access_log off;
    error_log /var/log/nginx/error.log warn;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        fastcgi_pass          app-a:9000;
        fastcgi_index         index.php;
        fastcgi_param         SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_read_timeout  60s;
        include               fastcgi_params;
    }

    location ~ /\. {
        deny all;
    }
}
```

**docker/scenario-b/Dockerfile**

```
FROM dunglas/frankenphp:latest-php8.3

# git necessário para o Composer em imagens Debian
RUN apt-get update && apt-get install -y --no-install-recommends git unzip && rm -rf /var/lib/apt/lists/*

# Extensões para CI4
RUN install-php-extensions opcache intl pgsql pdo_pgsql

# OPcache — mesmo nível de otimização do Cenário A para comparação justa
COPY docker/scenario-b/opcache.ini /usr/local/etc/php/conf.d/opcache.ini

# Instalar composer
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

WORKDIR /app

# Copiar código da aplicação CI4
COPY apps/ci4-base/ .

# Instalar dependências
RUN composer install --no-dev --optimize-autoloader --no-interaction --no-scripts

# Permissões de escrita para o CI4
RUN mkdir -p writable/{cache,logs,session,uploads,debugbar} \
    && chmod -R 777 writable/

# Caddyfile para modo Classic (sem diretiva worker — comportamento igual ao PHP-FPM)
COPY docker/scenario-b/Caddyfile /etc/caddy/Caddyfile

ENV SCENARIO_NAME=scenario-b
ENV COMPUTE_SIZE=1000
ENV CI_ENVIRONMENT=production
ENV SERVER_NAME=":8080"

EXPOSE 8080
```

**docker/scenario-b/Caddyfile**

```
{
    # FrankenPHP modo Classic — sem diretiva worker
    # Cada request inicia um novo contexto PHP (equivalente ao PHP-FPM)
    frankenphp
    order php_server before file_server
    admin off
}

:8080 {
    root * /app/public

    php_server

    log {
        output discard
    }
}
```

**docker/scenario-c/Dockerfile**

```
FROM dunglas/frankenphp:latest-php8.3

# git necessário para o Composer em imagens Debian
RUN apt-get update && apt-get install -y --no-install-recommends git unzip && rm -rf /var/lib/apt/lists/*

# Extensões para CI4
RUN install-php-extensions opcache intl pgsql pdo_pgsql

# OPcache — mesmo nível dos outros cenários
COPY docker/scenario-c/opcache.ini /usr/local/etc/php/conf.d/opcache.ini

# Instalar composer
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

WORKDIR /app

# Copiar código da aplicação CI4
# Inclui public/frankenphp-worker.php (suporte nativo CI4 >= 4.7.0)
COPY apps/ci4-base/ .

# Instalar dependências (CI4 >= 4.7 para suporte nativo ao Worker Mode)
RUN composer install --no-dev --optimize-autoloader --no-interaction --no-scripts

# Gera public/frankenphp-worker.php via comando oficial do CI4
RUN php spark worker:install --no-interaction

# Permissões de escrita para o CI4
RUN mkdir -p writable/{cache,logs,session,uploads,debugbar} \
    && chmod -R 777 writable/

# Caddyfile oficial gerado pelo `php spark worker:install`
# Worker mode com 4 workers (mesmo número de pm.max_children do Cenário A)
COPY docker/scenario-c/Caddyfile /etc/caddy/Caddyfile

ENV SCENARIO_NAME=scenario-c
ENV COMPUTE_SIZE=1000
ENV CI_ENVIRONMENT=production
ENV SERVER_NAME=":8080"

EXPOSE 8080
```

**docker/scenario-c/Caddyfile**

```
{
    frankenphp {
        worker {
            file public/frankenphp-worker.php
            num 4
        }
    }
    order php_server before file_server
    admin off
}

:8080 {
    root * public

    php_server {
        try_files {path} frankenphp-worker.php
    }

    file_server

    log {
        output discard
    }
}
```

**docker/scenario-d/Dockerfile**

```
FROM dunglas/frankenphp:latest-php8.3

# git necessário para o Composer em imagens Debian
RUN apt-get update && apt-get install -y --no-install-recommends git unzip && rm -rf /var/lib/apt/lists/*

# Extensões para Laravel
RUN install-php-extensions opcache pcntl pgsql pdo_pgsql

# OPcache — mesmo nível dos outros cenários
COPY docker/scenario-d/opcache.ini /usr/local/etc/php/conf.d/opcache.ini

# Instalar composer
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

WORKDIR /app

# Copiar app Laravel
COPY apps/laravel-octane/ .

# Instalar dependências
RUN composer update --no-dev --optimize-autoloader --no-interaction --no-scripts

# Otimizações de produção do Laravel
RUN php artisan config:cache \
    && php artisan route:cache \
    && php artisan event:cache

# Permissões de armazenamento
RUN chmod -R 777 storage bootstrap/cache

ENV SCENARIO_NAME=scenario-d
ENV COMPUTE_SIZE=1000
ENV APP_ENV=production
ENV APP_DEBUG=false
ENV OCTANE_SERVER=frankenphp
ENV SERVER_NAME=":8080"

EXPOSE 8080

# Octane com FrankenPHP — 4 workers para comparação justa com os outros cenários
CMD ["php", "artisan", "octane:frankenphp", "--workers=4", "--port=8080", "--host=0.0.0.0"]
```

**docker/scenario-c/opcache.ini**

```
opcache.enable=1
opcache.memory_consumption=128
opcache.interned_strings_buffer=8
opcache.max_accelerated_files=10000
opcache.validate_timestamps=0
opcache.revalidate_freq=0
opcache.save_comments=0
opcache.fast_shutdown=1
```

### APÊNDICE C — Scripts de carga do k6

**k6/load.js**

```javascript
/**
 * Load Test — Teste de carga principal do TCC
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
    { duration: '10m', target: 100 },  // pico sustentado
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
```

**k6/lib/endpoints.js**

```javascript
import http from 'k6/http';
import { check } from 'k6';
import { Trend } from 'k6/metrics';

export const healthDuration  = new Trend('endpoint_health_duration',  true);
export const computeDuration = new Trend('endpoint_compute_duration', true);
export const memoryDuration  = new Trend('endpoint_memory_duration',  true);
export const dbDuration      = new Trend('endpoint_db_duration',      true);

const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8080';

export function testHealth() {
  const res = http.get(`${BASE_URL}/health`, { tags: { endpoint: 'health' } });
  healthDuration.add(res.timings.duration);
  check(res, {
    'health: status 200':         (r) => r.status === 200,
    'health: body has status ok': (r) => r.json('status') === 'ok',
  });
  return res;
}

export function testCompute() {
  const res = http.get(`${BASE_URL}/compute`, { tags: { endpoint: 'compute' } });
  computeDuration.add(res.timings.duration);
  check(res, {
    'compute: status 200':          (r) => r.status === 200,
    'compute: body has data array': (r) => Array.isArray(r.json('data')),
  });
  return res;
}

export function testMemory() {
  const res = http.get(`${BASE_URL}/memory`, { tags: { endpoint: 'memory' } });
  memoryDuration.add(res.timings.duration);
  check(res, {
    'memory: status 200':     (r) => r.status === 200,
    'memory: counter exists': (r) => r.json('counter') > 0,
    'memory: pid exists':     (r) => r.json('pid') > 0,
  });
  return res;
}

export function testDb() {
  const res = http.get(`${BASE_URL}/db`, { tags: { endpoint: 'db' } });
  dbDuration.add(res.timings.duration);
  check(res, {
    'db: status 200':      (r) => r.status === 200,
    'db: item returned':   (r) => r.json('item') !== null,
    'db: item has id':     (r) => r.json('item.id') > 0,
  });
  return res;
}
```

**k6/smoke.js**

```javascript
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

  // Tag global: todas as métricas enviadas ao Prometheus carregam o label `scenario`.
  // Permite filtrar por cenário no Grafana mesmo com o TSDB acumulando múltiplos runs.
  tags: {
    scenario: __ENV.SCENARIO_NAME || 'unknown',
  },

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
```

### APÊNDICE D — Scripts de automação dos testes

**scripts/run-scenario.sh**

```bash
#!/usr/bin/env bash
# ==============================================================================
# run-scenario.sh — Executa um cenário de benchmark de forma isolada e limpa
#
# Uso:
#   ./scripts/run-scenario.sh <cenário> <teste> [opções]
#
# Exemplos:
#   ./scripts/run-scenario.sh a smoke          # Cenário A, smoke test
#   ./scripts/run-scenario.sh b load           # Cenário B, load test
#   ./scripts/run-scenario.sh c load --no-cache-clear  # sem limpeza de cache
#
# Cenários disponíveis: a | b | c | d
# Testes disponíveis:   smoke | load
# ==============================================================================

set -euo pipefail

SCENARIO="${1:-}"
TEST="${2:-smoke}"
NO_CACHE_CLEAR=false

for arg in "${@:3}"; do
  [[ "$arg" == "--no-cache-clear" ]] && NO_CACHE_CLEAR=true
done

# Validações
if [[ -z "$SCENARIO" ]]; then
  echo "Erro: informe o cenário. Uso: $0 <a|b|c|d> <smoke|load>"
  exit 1
fi

if [[ ! "$SCENARIO" =~ ^[abcd]$ ]]; then
  echo "Erro: cenário inválido '$SCENARIO'. Use: a, b, c, ou d"
  exit 1
fi

if [[ ! "$TEST" =~ ^(smoke|load)$ ]]; then
  echo "Erro: teste inválido '$TEST'. Use: smoke ou load"
  exit 1
fi

PROFILE="scenario-${SCENARIO}"

# Determina o host alvo do k6 (Cenário A usa nginx-a como proxy, demais usam app-X diretamente)
if [[ "$SCENARIO" == "a" ]]; then
  TARGET_HOST="nginx-a"
else
  TARGET_HOST="app-${SCENARIO}"
fi
TARGET_URL="http://${TARGET_HOST}:8080"

echo "======================================================================"
echo " TCC UEMA — Benchmark PHP Architecture"
echo " Cenário:  ${PROFILE^^} (${TARGET_HOST})"
echo " Teste:    ${TEST}"
echo " Data/hora: $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================================================"

# --- Passo 1: Derrubar qualquer cenário em execução e limpar métricas anteriores ---
echo ""
echo "[1/6] Derrubando cenários anteriores..."
docker compose \
  --profile scenario-a \
  --profile scenario-b \
  --profile scenario-c \
  --profile scenario-d \
  down --remove-orphans 2>/dev/null || true

# Remove o volume do Prometheus para garantir que cada cenário comece com
# TSDB limpo. Sem isso, métricas de cenários anteriores ficam no banco e
# podem confundir a análise — especialmente em queries PromQL sem filtro de tempo.
# O grafana-data e postgres-data são preservados intencionalmente:
#   - grafana-data: dashboards e datasources provisionados não precisam resetar
#   - postgres-data: tabela read-only, dados determinísticos, init.sql já rodou
PROMETHEUS_VOLUME="$(basename "$(pwd)")_prometheus-data"
if docker volume inspect "$PROMETHEUS_VOLUME" &>/dev/null; then
  docker volume rm "$PROMETHEUS_VOLUME" > /dev/null
  echo "   Volume do Prometheus limpo (${PROMETHEUS_VOLUME})."
fi

# --- Passo 2: Limpar cache do sistema operacional ---
# Crítico para isolar os benchmarks: evita que resultados do cenário anterior
# influenciem o próximo por páginas de memória, dentries e inodes cacheados.
if [[ "$NO_CACHE_CLEAR" == false ]]; then
  echo ""
  echo "[2/6] Limpando cache do sistema operacional (page cache, dentries, inodes)..."

  if [[ "$(uname)" == "Linux" ]]; then
    if [[ -w /proc/sys/vm/drop_caches ]]; then
      # Sincroniza buffers pendentes antes de liberar o cache
      sync
      # 3 = libera page cache + dentries + inodes
      echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
      echo "   Cache do SO liberado com sucesso."
    else
      echo "   AVISO: sem permissão para limpar o cache do SO."
      echo "   Execute: echo 3 | sudo tee /proc/sys/vm/drop_caches"
      echo "   Ou adicione ao sudoers: $(whoami) ALL=(ALL) NOPASSWD: /usr/bin/tee /proc/sys/vm/drop_caches"
      echo "   Continuando sem limpeza de cache..."
    fi
  elif [[ "$(uname)" == "Darwin" ]]; then
    sudo purge 2>/dev/null && echo "   Cache do macOS liberado (purge)." || \
      echo "   AVISO: falha ao executar purge. Continuando..."
  else
    echo "   AVISO: sistema não reconhecido para limpeza de cache."
  fi
else
  echo ""
  echo "[2/6] Limpeza de cache do SO ignorada (--no-cache-clear)."
fi

# --- Passo 3: Aguardar memória assentar ---
echo ""
echo "[3/6] Aguardando 3s para memória assentar..."
sleep 3

# --- Passo 4: Subir o cenário + stack de observabilidade ---
echo ""
echo "[4/6] Iniciando ${PROFILE} + Prometheus + Grafana + cAdvisor..."
docker compose --profile "$PROFILE" up -d --build

# --- Passo 5: Aguardar o app estar pronto ---
echo ""
echo "[5/6] Aguardando ${TARGET_HOST} responder em /health..."
MAX_ATTEMPTS=30
ATTEMPT=0
until docker compose --profile "$PROFILE" run --rm --no-deps k6 \
  run --quiet \
  --duration 1s --vus 1 \
  -e TARGET_URL="$TARGET_URL" \
  -e SCRIPT=smoke \
  /scripts/smoke.js &>/dev/null; do
  ATTEMPT=$((ATTEMPT + 1))
  if [[ $ATTEMPT -ge $MAX_ATTEMPTS ]]; then
    echo "   ERRO: ${TARGET_HOST} não respondeu após ${MAX_ATTEMPTS} tentativas."
    echo "   Verifique: docker compose --profile $PROFILE logs"
    exit 1
  fi
  echo "   Tentativa ${ATTEMPT}/${MAX_ATTEMPTS}... aguardando 2s"
  sleep 2
done
echo "   ${TARGET_HOST} está pronto!"

# --- Passo 6: Executar o teste k6 ---
echo ""
echo "[6/6] Executando ${TEST} test contra ${TARGET_URL}..."
echo "      Grafana disponível em http://localhost:3000 (admin / benchmark)"
echo ""

RESULTS_DIR="$(dirname "$0")/../results"
mkdir -p "$RESULTS_DIR"
TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
RESULTS_TXT="/results/scenario-${SCENARIO}-${TEST}-${TIMESTAMP}.txt"
DASHBOARD_HTML="/results/dashboard-${PROFILE}-${TEST}-${TIMESTAMP}.html"

docker compose --profile "$PROFILE" run --rm \
  -e K6_WEB_DASHBOARD=true \
  -e K6_WEB_DASHBOARD_EXPORT="$DASHBOARD_HTML" \
  k6 run \
  --out experimental-prometheus-rw \
  --summary-export /results/last-run.json \
  -e TARGET_URL="$TARGET_URL" \
  -e SCENARIO_NAME="$PROFILE" \
  "/scripts/${TEST}.js" \
  | tee "${RESULTS_DIR}/scenario-${SCENARIO}-${TEST}-${TIMESTAMP}.txt"

echo ""
echo "======================================================================"
echo " Teste concluído!"
echo " Resultados: ${RESULTS_DIR}/scenario-${SCENARIO}-${TEST}-${TIMESTAMP}.txt
 Dashboard:  ${RESULTS_DIR}/dashboard-${PROFILE}-${TEST}-${TIMESTAMP}.html"
echo " Grafana:    http://localhost:3000"
echo " Prometheus: http://localhost:9090"
echo "======================================================================"
echo ""
echo " Para coletar snapshot de docker stats execute:"
echo "   ./scripts/collect-results.sh ${SCENARIO}"
echo ""
echo " Para derrubar o ambiente execute:"
echo "   docker compose --profile ${PROFILE} down"
echo "======================================================================"
```

**scripts/run-matrix.sh**

```bash
#!/usr/bin/env bash
# run-matrix.sh — Executa N rodadas de load test em ordem rotativa (a,b,c,d) e
# arquiva cada rodada em results/runs/<cenário>-run<N>/ (summary k6, dashboard, log, docker stats, env).
# Uso: ./scripts/run-matrix.sh [rodadas=3]
set -uo pipefail
cd "$(dirname "$0")/.."
ROUNDS="${1:-3}"
mkdir -p results/runs
for r in $(seq 1 "$ROUNDS"); do
  for s in a b c d; do
    dir="results/runs/${s}-run${r}"
    [[ -f "$dir/last-run.json" ]] && { echo "pulando $dir (já existe)"; continue; }
    mkdir -p "$dir"
    rm -f results/last-run.json
    ./scripts/run-scenario.sh "$s" load --no-cache-clear 2>&1 | tee "$dir/console.log"
    docker stats --no-stream --format '{{.Name}},{{.CPUPerc}},{{.MemUsage}}' > "$dir/docker-stats-post.csv" 2>/dev/null || true
    mv results/last-run.json "$dir/" 2>/dev/null
    mv results/dashboard-scenario-${s}-load-*.html "$dir/" 2>/dev/null
    mv results/scenario-${s}-load-*.txt "$dir/" 2>/dev/null
    date -Is > "$dir/finished_at"
  done
done
docker compose --profile scenario-a --profile scenario-b --profile scenario-c --profile scenario-d down --remove-orphans
```

**scripts/run-captura.sh**

```bash
#!/usr/bin/env bash
# Rodada extra de captura (Grafana tema claro, Chrome headless). Não entra nas médias oficiais.
# Tira o print do dashboard no minuto ~14:20 de cada rodada (janela de 16 min mostra a rodada inteira).
cd "$(dirname "$0")/.."
URL='http://localhost:3000/d/tcc-uema-benchmark?kiosk&theme=light&from=now-16m&to=now'
for s in a b c d; do
  log=results/captura/console-$s.log
  ( until grep -q "running (14m2" "$log" 2>/dev/null; do sleep 2; done
    timeout 90 google-chrome --headless=new --no-sandbox --disable-gpu --user-data-dir=/tmp/claude-1000/chrome-prof \
      --window-size=1600,1140 --virtual-time-budget=20000 --screenshot="docs/figuras/grafana-$s.png" "$URL" >/dev/null 2>&1 ) &
  ./scripts/run-scenario.sh "$s" load --no-cache-clear > "$log" 2>&1
  wait
  mkdir -p results/captura/$s
  mv results/dashboard-scenario-$s-load-*.html results/scenario-$s-load-*.txt results/last-run.json results/captura/$s/ 2>/dev/null
done
docker compose --profile scenario-a --profile scenario-b --profile scenario-c --profile scenario-d down --remove-orphans
```

**scripts/sample-stats.sh**

```bash
#!/usr/bin/env bash
# sample-stats.sh — amostra docker stats a cada 5 s (timestamp,container,cpu%,mem) durante a matriz
OUT="${1:-results/runs/stats-samples.csv}"
echo "ts,name,cpu_pct,mem_usage" > "$OUT"
while pgrep -f run-matrix.sh >/dev/null; do
  ts=$(date +%s)
  docker stats --no-stream --format '{{.Name}},{{.CPUPerc}},{{.MemUsage}}' 2>/dev/null | grep -E 'app-[abcd]|nginx-a' | sed "s/^/$ts,/" >> "$OUT"
  sleep 5
done
```

**scripts/analyze.py**

```bash
#!/usr/bin/env python3
"""Agrega as rodadas em results/runs/<cenário>-run<N>/last-run.json (k6 --summary-export)
e gera tabelas (Markdown/CSV) e figuras (PNG) em results/analysis/.

Uso: python3 scripts/analyze.py   (requer matplotlib para as figuras)
"""
import csv
import re
import json
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "results" / "runs"
OUT = ROOT / "results" / "analysis"
OUT.mkdir(parents=True, exist_ok=True)

NOMES = {
    "a": "A — CI4 + PHP-FPM",
    "b": "B — CI4 + FrankenPHP clássico",
    "c": "C — CI4 + FrankenPHP Worker",
    "d": "D — Laravel Octane",
}
ENDPOINTS = ["health", "compute", "memory", "db"]
CORES = {"a": "#8c8c8c", "b": "#4c78a8", "c": "#e07b39", "d": "#59a14f"}


def load():
    data = {s: [] for s in NOMES}
    for p in sorted(RUNS.glob("*-run*/last-run.json")):
        s = p.parent.name.split("-")[0]
        m = json.load(open(p))["metrics"]
        run = {
            "rps": m["http_reqs"]["rate"],
            "reqs": m["http_reqs"]["count"],
            "err": m["http_req_failed"].get("value", m["http_req_failed"].get("rate", 0)),
            "avg": m["http_req_duration"]["avg"],
            "p50": m["http_req_duration"]["med"],
            "p95": m["http_req_duration"]["p(95)"],
            "p99": m["http_req_duration"].get("p(99)", float("nan")),
        }
        for e in ENDPOINTS:
            k = f"endpoint_{e}_duration"
            if k in m:
                run[f"{e}_avg"] = m[k]["avg"]
                run[f"{e}_p95"] = m[k]["p(95)"]
        data[s].append(run)
    return data


def recursos():
    """CPU/RAM por cenário a partir de results/runs/stats-samples.csv (docker stats a cada ~7 s).
    Janela do patamar sustentado de cada rodada: [fim-11,5 min, fim-1,5 min]. Cenário A soma app-a + nginx-a."""
    from datetime import datetime
    amostras = list(csv.DictReader(open(RUNS / "stats-samples.csv")))
    res = {s: [] for s in NOMES}
    for fin in sorted(RUNS.glob("*-run*/finished_at")):
        s = fin.parent.name.split("-")[0]
        if not (fin.parent / "last-run.json").exists():
            continue
        t1 = datetime.fromisoformat(fin.read_text().strip()).timestamp() - 90
        t0 = t1 - 600
        por_ts = {}
        for r in amostras:
            ts = int(r["ts"])
            if not (t0 <= ts <= t1) or not r["name"].startswith(f"tcc-uema-app-{s}") and not (s == "a" and "nginx-a" in r["name"]):
                continue
            cpu = float(r["cpu_pct"].rstrip("%"))
            mem = r["mem_usage"].split("/")[0].strip()
            val = float(re.sub("[^0-9.]", "", mem)) * (1024 if "GiB" in mem else 1)
            c, m = por_ts.get(ts, (0, 0))
            por_ts[ts] = (c + cpu, m + val)
        if por_ts:
            cs = [v[0] for v in por_ts.values()]
            ms_ = [v[1] for v in por_ts.values()]
            res[s].append({"cpu": st.mean(cs), "ram": st.mean(ms_), "ram_pico": max(ms_)})
    return res


def ms(vals):
    vals = [v for v in vals if v == v]
    if not vals:
        return (float("nan"), float("nan"))
    return (st.mean(vals), st.stdev(vals) if len(vals) > 1 else 0.0)


def main():
    data = load()
    agg = {}
    for s, runs in data.items():
        if not runs:
            continue
        agg[s] = {k: ms([r[k] for r in runs if k in r]) for k in runs[0]}
        agg[s]["n"] = len(runs)

    # Tabela 1/2 (CSV + Markdown)
    linhas = ["| Cenário | n | RPS (média ± dp) | Latência p50 (ms) | p95 (ms) | p99 (ms) | Erros (%) |",
              "|---|---|---|---|---|---|---|"]
    with open(OUT / "global.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cenario", "n", "rps_media", "rps_dp", "p50", "p95", "p99", "erro_pct"])
        for s, a in agg.items():
            linhas.append(
                f"| {NOMES[s]} | {a['n']} | {a['rps'][0]:.1f} ± {a['rps'][1]:.1f} | {a['p50'][0]:.1f} | "
                f"{a['p95'][0]:.1f} | {a['p99'][0]:.1f} | {a['err'][0]*100:.2f} |")
            w.writerow([s, a["n"], a["rps"][0], a["rps"][1], a["p50"][0], a["p95"][0], a["p99"][0], a["err"][0] * 100])
    (OUT / "tabela_global.md").write_text("\n".join(linhas) + "\n")

    linhas = ["| Cenário | " + " | ".join(f"{e} avg / p95 (ms)" for e in ENDPOINTS) + " |",
              "|---|" + "---|" * len(ENDPOINTS)]
    for s, a in agg.items():
        cel = [f"{a[f'{e}_avg'][0]:.1f} / {a[f'{e}_p95'][0]:.1f}" for e in ENDPOINTS]
        linhas.append(f"| {NOMES[s]} | " + " | ".join(cel) + " |")
    (OUT / "tabela_endpoints.md").write_text("\n".join(linhas) + "\n")

    # Tabela 3: recursos
    rec = recursos()
    linhas = ["| Cenário | CPU média (%) | RAM média (MiB) | RAM pico (MiB) |", "|---|---|---|---|"]
    ragg = {}
    for s, rr in rec.items():
        if rr:
            ragg[s] = {k: ms([r[k] for r in rr]) for k in ("cpu", "ram", "ram_pico")}
            a = ragg[s]
            linhas.append(f"| {NOMES[s]} | {a['cpu'][0]:.1f} ± {a['cpu'][1]:.1f} | {a['ram'][0]:.1f} ± {a['ram'][1]:.1f} | {a['ram_pico'][0]:.1f} |")
    (OUT / "tabela_recursos.md").write_text("\n".join(linhas) + "\n")

    # Ganhos relativos de RPS
    ganhos = []
    for a_, b_ in [("b", "a"), ("c", "a"), ("c", "b"), ("c", "d"), ("d", "a")]:
        if a_ in agg and b_ in agg:
            g = (agg[a_]["rps"][0] / agg[b_]["rps"][0] - 1) * 100
            ganhos.append(f"{a_.upper()} vs {b_.upper()}: {g:+.1f}% RPS")
    (OUT / "ganhos.txt").write_text("\n".join(ganhos) + "\n")

    # Figuras
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib ausente: figuras não geradas")
        return
    plt.rcParams.update({"font.size": 11, "font.family": "DejaVu Sans"})

    ss = list(agg)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([NOMES[s].split(" — ")[0] for s in ss], [agg[s]["rps"][0] for s in ss],
           yerr=[agg[s]["rps"][1] for s in ss], color=[CORES[s] for s in ss], capsize=4)
    for i, s in enumerate(ss):
        ax.text(i, agg[s]["rps"][0], f"{agg[s]['rps'][0]:.0f}", ha="center", va="bottom")
    ax.set_ylabel("Requisições por segundo (média ± dp)")
    ax.set_xlabel("Cenário")
    fig.tight_layout()
    fig.savefig(OUT / "fig_rps.png", dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.2))
    w = 0.8 / len(ss)
    for i, s in enumerate(ss):
        ax.bar([j + i * w for j in range(len(ENDPOINTS))], [agg[s][f"{e}_p95"][0] for e in ENDPOINTS],
               w, label=NOMES[s].split(" — ")[0], color=CORES[s])
    ax.set_xticks([j + 0.4 - w / 2 for j in range(len(ENDPOINTS))])
    ax.set_xticklabels(ENDPOINTS)
    ax.set_ylabel("Latência p95 (ms)")
    ax.set_xlabel("Endpoint")
    ax.legend(title="Cenário")
    fig.tight_layout()
    fig.savefig(OUT / "fig_latencia_p95.png", dpi=200)
    plt.close(fig)
    if ragg:
        fig, axs = plt.subplots(1, 2, figsize=(9, 3.8))
        ks = list(ragg)
        for ax, k, t in ((axs[0], "cpu", "CPU média (%)"), (axs[1], "ram", "RAM média (MiB)")):
            ax.bar([NOMES[s].split(" — ")[0] for s in ks], [ragg[s][k][0] for s in ks],
                   yerr=[ragg[s][k][1] for s in ks], color=[CORES[s] for s in ks], capsize=4)
            ax.set_ylabel(t)
            ax.set_xlabel("Cenário")
        fig.tight_layout()
        fig.savefig(OUT / "fig_recursos.png", dpi=200)
        plt.close(fig)
    print("OK:", OUT)


if __name__ == "__main__":
    main()
```

### APÊNDICE E — Controlador dos endpoints (CodeIgniter 4)

**apps/ci4-base/app/Controllers/BenchmarkController.php**

```php
<?php

namespace App\Controllers;

use CodeIgniter\Controller;

class BenchmarkController extends Controller
{
    public function health(): void
    {
        $this->response->setHeader('Content-Type', 'application/json');
        echo json_encode([
            'status'   => 'ok',
            'scenario' => getenv('SCENARIO_NAME') ?: 'unknown',
        ]);
    }

    public function compute(): void
    {
        $size = (int) (getenv('COMPUTE_SIZE') ?: 1000);
        $data = [];

        for ($i = 0; $i < $size; $i++) {
            $data[] = [
                'id'    => $i + 1,
                'uuid'  => md5(uniqid((string) $i, true)),
                'value' => random_int(1, 999999),
                'label' => str_repeat('x', random_int(5, 20)),
            ];
        }

        $this->response->setHeader('Content-Type', 'application/json');
        echo json_encode([
            'count'    => $size,
            'scenario' => getenv('SCENARIO_NAME') ?: 'unknown',
            'data'     => $data,
        ]);
    }

    public function memory(): void
    {
        // Propriedade estática sobrevive ao loop do Worker Mode (mesma instância PHP)
        // Em PHP-FPM/Classic: reinicia a cada request (processo novo ou sem estado persistente)
        MemoryState::$counter++;

        $this->response->setHeader('Content-Type', 'application/json');
        echo json_encode([
            'counter'  => MemoryState::$counter,
            'pid'      => getmypid(),
            'scenario' => getenv('SCENARIO_NAME') ?: 'unknown',
        ]);
    }

    public function db(): void
    {
        $id = random_int(1, 10000);

        // pg_backend_pid() retorna o PID do processo PostgreSQL que serve esta conexão.
        // Worker Mode (C, D): pg_pid constante = mesma conexão reutilizada entre requests.
        // PHP-FPM/Classic (A, B): pg_pid varia = nova conexão estabelecida por request.
        // Incluído na mesma query — sem round-trip extra.
        $row = db_connect()
            ->query(
                'SELECT id, name, value, pg_backend_pid() AS pg_pid FROM benchmark_items WHERE id = ?',
                [$id]
            )
            ->getRow();

        $this->response->setHeader('Content-Type', 'application/json');
        echo json_encode([
            'item'     => $row,
            'php_pid'  => getmypid(),
            'scenario' => getenv('SCENARIO_NAME') ?: 'unknown',
        ]);
    }
}

class MemoryState
{
    public static int $counter = 0;
}
```

### APÊNDICE F — Resultados por execução

**Tabela F1 – Resultados de cada uma das 12 execuções**

| Execução | RPS | Latência p50 (ms) | Latência p95 (ms) | Erros (%) |
|---|---|---|---|---|
| A – execução 1 | 124.9 | 786.4 | 896.9 | 0.00 |
| A – execução 2 | 126.5 | 783.4 | 890.4 | 0.00 |
| A – execução 3 | 127.8 | 723.8 | 885.4 | 0.00 |
| B – execução 1 | 109.2 | 881.7 | 1005.9 | 0.00 |
| B – execução 2 | 109.2 | 878.6 | 1002.2 | 0.00 |
| B – execução 3 | 110.1 | 873.0 | 998.4 | 0.00 |
| C – execução 1 | 291.5 | 307.6 | 399.7 | 0.00 |
| C – execução 2 | 289.8 | 308.4 | 399.7 | 0.00 |
| C – execução 3 | 281.9 | 307.6 | 493.0 | 0.00 |
| D – execução 1 | 368.6 | 277.2 | 313.6 | 0.00 |
| D – execução 2 | 366.6 | 277.6 | 318.4 | 0.00 |
| D – execução 3 | 370.8 | 272.7 | 312.3 | 0.00 |

Fonte: elaborado pelo autor (2026).

