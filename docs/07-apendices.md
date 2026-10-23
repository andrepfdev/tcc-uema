## APÊNDICES

### APÊNDICE A – Orquestração dos contêineres (docker-compose.yml)

**docker-compose.yml**

```yaml
services:

  # ===========================================================================
  # CENÁRIO A — Legacy: CodeIgniter 4 + PHP-FPM + Nginx (base Debian 13, igual aos demais)
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
    image: nginx:1.31.7-trixie@sha256:bc4cad49969aaf95eb4eecec5572846f86e59f1e8332aba36ed64b91aff8b724
    ports:
      - "${BENCH_PORT:-8080}:8080"
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
      - "${BENCH_PORT:-8080}:8080"
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

  # Sensibilidade: FrankenPHP clássico com número PADRÃO de threads (sem num_threads)
  app-e:
    profiles: [scenario-e]
    build:
      context: .
      dockerfile: docker/scenario-b/Dockerfile
    ports:
      - "${BENCH_PORT:-8080}:8080"
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: "512M"
    volumes:
      - ./docker/scenario-b/Caddyfile.default:/etc/frankenphp/Caddyfile:ro
    environment:
      SCENARIO_NAME: scenario-e
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
      - "${BENCH_PORT:-8080}:8080"
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: "512M"
    environment:
      FRANKENPHP_WORKERS: "${FRANKENPHP_WORKERS:-4}"
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
    command: ["php", "artisan", "octane:frankenphp", "--workers=${OCTANE_WORKERS:-4}", "--port=8080", "--host=0.0.0.0"]
    ports:
      - "${BENCH_PORT:-8080}:8080"
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
    profiles: [scenario-a, scenario-b, scenario-c, scenario-d, scenario-e]
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
    profiles: [scenario-a, scenario-b, scenario-c, scenario-d, scenario-e]
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
    profiles: [scenario-a, scenario-b, scenario-c, scenario-d, scenario-e]
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
    profiles: [scenario-a, scenario-b, scenario-c, scenario-d, scenario-e]
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
    profiles: [scenario-a, scenario-b, scenario-c, scenario-d, scenario-e]
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

### APÊNDICE B – Imagens e configuração dos servidores

O cenário E usa o mesmo `Dockerfile` do cenário B, trocando apenas o `Caddyfile` por `Caddyfile.default`.

**docker/scenario-a/Dockerfile**

```dockerfile
FROM php:8.3.35-fpm-trixie@sha256:ed67b5fcd7600614dd651621a04214fbe16d373262cb31eb50bc224c18cf0e88

# libicu-dev: necessário para ext-intl (requerida pelo CI4)
# libpq-dev: necessário para ext-pgsql/pdo_pgsql
# git/unzip: necessários para o Composer
RUN apt-get update \
    && apt-get install -y --no-install-recommends libicu-dev libpq-dev git unzip \
    && docker-php-ext-install opcache intl pgsql pdo_pgsql \
    && rm -rf /var/lib/apt/lists/*

# OPcache para benchmark justo (Scenario A recebe todos os otimizadores que tem direito)
COPY docker/scenario-a/opcache.ini /usr/local/etc/php/conf.d/opcache.ini

# Instalar composer
COPY --from=composer:2@sha256:af98f42dfff7c68ba8d53c2164fd9fde1087b7d449514baa38c418b1f6bc4bac /usr/bin/composer /usr/bin/composer

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

```nginx
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

```nginx
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

**docker/scenario-a/opcache.ini**

```ini
opcache.enable=1
opcache.memory_consumption=128
opcache.interned_strings_buffer=8
opcache.max_accelerated_files=10000
opcache.validate_timestamps=0
opcache.revalidate_freq=0
opcache.save_comments=0
opcache.fast_shutdown=1
```

**docker/scenario-b/Dockerfile**

```dockerfile
FROM dunglas/frankenphp:1.13.0-php8.3.35@sha256:3a1dfb9404aceb016493f6c18989cc2b66ce62c6de2a79ae6e3b3dfe7f94094a

# git necessário para o Composer em imagens Debian
RUN apt-get update && apt-get install -y --no-install-recommends git unzip && rm -rf /var/lib/apt/lists/*

# Extensões para CI4
RUN install-php-extensions opcache intl pgsql pdo_pgsql

# OPcache — mesmo nível de otimização do Cenário A para comparação justa
COPY docker/scenario-b/opcache.ini /usr/local/etc/php/conf.d/opcache.ini

# Instalar composer
COPY --from=composer:2@sha256:af98f42dfff7c68ba8d53c2164fd9fde1087b7d449514baa38c418b1f6bc4bac /usr/bin/composer /usr/bin/composer

WORKDIR /app

# Copiar código da aplicação CI4
COPY apps/ci4-base/ .

# Instalar dependências
RUN composer install --no-dev --optimize-autoloader --no-interaction --no-scripts

# Permissões de escrita para o CI4
RUN mkdir -p writable/{cache,logs,session,uploads,debugbar} \
    && chmod -R 777 writable/

# Caddyfile para modo Classic (sem diretiva worker — comportamento igual ao PHP-FPM)
COPY docker/scenario-b/Caddyfile /etc/frankenphp/Caddyfile

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
    frankenphp {
        # 4 threads PHP: equivalente aos 4 processos do PHP-FPM (A) e aos 4 workers (C, D)
        num_threads 4
    }
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

**docker/scenario-b/Caddyfile.default**

```
{
    # FrankenPHP modo Classic — configuração PADRÃO de threads (sensibilidade; ~2x núcleos do hospedeiro)
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

```dockerfile
FROM dunglas/frankenphp:1.13.0-php8.3.35@sha256:3a1dfb9404aceb016493f6c18989cc2b66ce62c6de2a79ae6e3b3dfe7f94094a

# git necessário para o Composer em imagens Debian
RUN apt-get update && apt-get install -y --no-install-recommends git unzip && rm -rf /var/lib/apt/lists/*

# Extensões para CI4
RUN install-php-extensions opcache intl pgsql pdo_pgsql

# OPcache — mesmo nível dos outros cenários
COPY docker/scenario-c/opcache.ini /usr/local/etc/php/conf.d/opcache.ini

# Instalar composer
COPY --from=composer:2@sha256:af98f42dfff7c68ba8d53c2164fd9fde1087b7d449514baa38c418b1f6bc4bac /usr/bin/composer /usr/bin/composer

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
COPY docker/scenario-c/Caddyfile /etc/frankenphp/Caddyfile

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
            num {$FRANKENPHP_WORKERS:4}
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

```dockerfile
FROM dunglas/frankenphp:1.13.0-php8.3.35@sha256:3a1dfb9404aceb016493f6c18989cc2b66ce62c6de2a79ae6e3b3dfe7f94094a

# git necessário para o Composer em imagens Debian
RUN apt-get update && apt-get install -y --no-install-recommends git unzip && rm -rf /var/lib/apt/lists/*

# Extensões para Laravel
RUN install-php-extensions opcache pcntl pgsql pdo_pgsql

# OPcache — mesmo nível dos outros cenários
COPY docker/scenario-d/opcache.ini /usr/local/etc/php/conf.d/opcache.ini

# Instalar composer
COPY --from=composer:2@sha256:af98f42dfff7c68ba8d53c2164fd9fde1087b7d449514baa38c418b1f6bc4bac /usr/bin/composer /usr/bin/composer

WORKDIR /app

# Copiar app Laravel
COPY apps/laravel-octane/ .

# Instalar dependências
RUN composer install --no-dev --optimize-autoloader --no-interaction --no-scripts

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

### APÊNDICE C – Scripts de carga do k6

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
```

**k6/long.js**

```javascript
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

**k6/lib/endpoints.js**

```javascript
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
```

### APÊNDICE D – Scripts de automação e análise

**scripts/run-completo.sh**

```bash
#!/usr/bin/env bash
# run-completo.sh — Experimento completo, em uma única execução e sem intervenção.
# REGRA: sempre refaz TUDO do zero; qualquer falha aborta a execução inteira (descartar e recomeçar).
#
#  0) diagnóstico de persistência por worker (C e D, com 1 e 4 workers)
#  1) A, B, C, D x 3 (ordem rotativa)        -> results/runs/<c>-run<N>
#  2) E (B com threads padrão) x 3           -> results/runs/e-run<N>
#  3) testes longos (30 min no patamar): C e D -> results/runs/<c>-long
#  4) execuções de captura A-D com print do Grafana (tema claro, min 14:20, fora do patamar) -> results/captura
# Cada execução: contêineres anteriores derrubados, Prometheus zerado, cache do SO liberado (registro antes/depois), sem rebuild.
# Amostrador de CPU/RAM (docker stats, ~3 s) durante toda a coleta.
set -uo pipefail
cd "$(dirname "$0")/.."
export NO_BUILD=1
# Porta do hospedeiro para os testes manuais/diagnóstico (a 8080 pode estar ocupada por outro serviço da máquina)
export BENCH_PORT="${BENCH_PORT:-18080}"
(echo >/dev/tcp/127.0.0.1/"$BENCH_PORT") 2>/dev/null && { echo "ERRO: porta $BENCH_PORT já está em uso."; exit 1; }
for d in $( [[ -n "${CAPTURAS:-}" ]] && echo "" || echo "results/runs results/captura results/diagnostico" ); do
  [[ -z "$(ls -A "$d" 2>/dev/null)" ]] || { echo "ERRO: $d não está vazio. Arquive antes (mv); a coleta sempre recomeça do zero."; exit 1; }
done
echo 3 | sudo -n tee /proc/sys/vm/drop_caches >/dev/null 2>&1 || { echo "ERRO: sudo -n tee /proc/sys/vm/drop_caches não funciona (sudoers)."; exit 1; }
command -v google-chrome >/dev/null || { echo "ERRO: google-chrome ausente (necessário para os prints)."; exit 1; }
mkdir -p results/runs results/captura results/diagnostico docs/figuras
FLAG=$(mktemp); trap 'rm -f "$FLAG"' EXIT
falha() { echo "FALHA: $1 — coleta ABORTADA. Descarte results/ (arquive) e refaça TUDO."; rm -f "$FLAG"; exit 1; }
if [[ -z "${CAPTURAS:-}" ]]; then ./scripts/sample-stats.sh results/runs/stats-samples.csv "$FLAG" & fi

if [[ -z "${CAPTURAS:-}" ]]; then
echo "##### 0) DIAGNÓSTICO DE PERSISTÊNCIA #####"
for s in c d; do for w in 1 4; do ./scripts/diagnostico-persistencia.sh "$s" "$w" 200 || falha "diagnóstico $s w=$w"; done; done

rodar() {  # <cenário> <teste> <rótulo> <duração-patamar-s>
  local s="$1" test="$2" dir="results/runs/$3"
  mkdir -p "$dir"; rm -f results/last-run.json
  PLATEAU_S="$4" ./scripts/run-scenario.sh "$s" "$test" 2>&1 | tee "$dir/console.log"
  grep -q "Teste concluído" "$dir/console.log" && [[ -f results/last-run.json ]] || falha "$dir"
  docker stats --no-stream --format '{{.Name}},{{.CPUPerc}},{{.MemUsage}}' > "$dir/docker-stats-post.csv" 2>/dev/null || true
  mv results/last-run.json "$dir/"
  mv results/dashboard-scenario-${s}-${test}-*.html "$dir/" 2>/dev/null
  mv results/scenario-${s}-${test}-*.txt "$dir/" 2>/dev/null
  date -Is > "$dir/finished_at"
}
echo "##### 1) A,B,C,D x 3 #####"
for r in 1 2 3; do for s in a b c d; do rodar "$s" load "${s}-run${r}" 600; done; done
echo "##### 2) E x 3 #####"
for r in 1 2 3; do rodar e load "e-run${r}" 600; done
echo "##### 3) LONGOS C e D #####"
for s in c d; do rodar "$s" long "${s}-long" 1800; done

fi  # fim das etapas 0-3 (puladas ao retomar só as capturas com CAPTURAS="b c d")
echo "##### 4) CAPTURAS A-D #####"
URL='http://localhost:3000/d/tcc-uema-benchmark?kiosk&theme=light&from=now-16m&to=now'
for s in ${CAPTURAS:-a b c d}; do
  log=results/captura/console-$s.log
  ( until grep -q "running (14m2" "$log" 2>/dev/null; do sleep 2; done
    timeout 90 google-chrome --headless=new --no-sandbox --disable-gpu --user-data-dir=/tmp/claude-1000/chrome-prof \
      --window-size=1600,1140 --virtual-time-budget=20000 --screenshot="docs/figuras/grafana-$s.png" "$URL" >/dev/null 2>&1 ) &
  CAP_PID=$!
  rm -f results/last-run.json
  PLATEAU_S=600 ./scripts/run-scenario.sh "$s" load > "$log" 2>&1
  wait "$CAP_PID"
  grep -q "Teste concluído" "$log" && [[ -s docs/figuras/grafana-$s.png ]] || falha "captura $s"
  mkdir -p results/captura/$s
  mv results/dashboard-scenario-$s-load-*.html results/scenario-$s-load-*.txt results/last-run.json results/captura/$s/ 2>/dev/null
done
docker compose --profile scenario-a --profile scenario-b --profile scenario-c --profile scenario-d --profile scenario-e down --remove-orphans
rm -f "$FLAG"; echo "COLETA COMPLETA"
```

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
# Testes disponíveis:   smoke | load | long | rate (taxa de chegada fixa; ver k6/rate.js)
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

if [[ ! "$SCENARIO" =~ ^[abcde]$ ]]; then
  echo "Erro: cenário inválido '$SCENARIO'. Use: a, b, c, d ou e"
  exit 1
fi

if [[ ! "$TEST" =~ ^(smoke|load|long|rate)$ ]]; then
  echo "Erro: teste inválido '$TEST'. Use: smoke, load, long ou rate"
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
  --profile scenario-e \
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
    sync
    echo "   Antes:  $(free -m | awk 'NR==2 {print "buff/cache=" $6 " MiB, livre=" $4 " MiB"}')"
    # sudo -n: nunca pede senha; exige a regra NOPASSWD para /usr/bin/tee /proc/sys/vm/drop_caches.
    # Se falhar, ABORTA (a limpeza faz parte do protocolo experimental e não pode ser pulada em silêncio).
    if echo 3 | sudo -n tee /proc/sys/vm/drop_caches > /dev/null 2>&1; then
      echo "   Depois: $(free -m | awk 'NR==2 {print "buff/cache=" $6 " MiB, livre=" $4 " MiB"}')"
      echo "   Cache do SO liberado com sucesso."
    else
      echo "   ERRO: não foi possível limpar o cache do SO sem senha."
      echo "   Configure uma vez: echo \"$(whoami) ALL=(ALL) NOPASSWD: /usr/bin/tee /proc/sys/vm/drop_caches\" | sudo tee /etc/sudoers.d/drop-caches"
      echo "   (ou rode com --no-cache-clear para pular conscientemente)."
      exit 1
    fi
  elif [[ "$(uname)" == "Darwin" ]]; then
    sudo purge 2>/dev/null && echo "   Cache do macOS liberado (purge)." || { echo "   ERRO: purge falhou."; exit 1; }
  else
    echo "   ERRO: sistema não reconhecido para limpeza de cache."; exit 1
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
if [[ "${NO_BUILD:-0}" == "1" ]]; then
  docker compose --profile "$PROFILE" up -d
else
  docker compose --profile "$PROFILE" up -d --build
fi

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
  --summary-trend-stats="avg,min,med,max,p(90),p(95),p(99)" \
  -e TARGET_URL="$TARGET_URL" \
  -e SCENARIO_NAME="$PROFILE" \
  -e PLATEAU_S="${PLATEAU_S:-600}" \
  -e RATE="${RATE:-100}" \
  -e WARMUP_S="${WARMUP_S:-120}" \
  -e RAMP_S="${RAMP_S:-120}" \
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

**scripts/sample-stats.sh**

```bash
#!/usr/bin/env bash
# sample-stats.sh — amostra docker stats (ts,container,cpu%,mem) a cada ~5 s até o arquivo-sinalizador sumir.
# Uso: sample-stats.sh <saida.csv> <arquivo-sinalizador>
OUT="${1:-results/runs/stats-samples.csv}"; FLAG="${2:-/tmp/sampling.flag}"
echo "ts,name,cpu_pct,mem_usage" > "$OUT"
while [[ -f "$FLAG" ]]; do
  ts=$(date +%s)
  docker stats --no-stream --format '{{.Name}},{{.CPUPerc}},{{.MemUsage}}' 2>/dev/null | grep -E 'app-[a-f]|nginx-a' | sed "s/^/$ts,/" >> "$OUT"
  sleep 3
done
```

**scripts/diagnostico-persistencia.sh**

```bash
#!/usr/bin/env bash
# Diagnóstico de persistência por worker: N requisições sequenciais e concorrentes a /memory e /db.
# Uso: ./scripts/diagnostico-persistencia.sh <c|d> <workers> [N=200]  -> results/diagnostico/<cenário>-w<workers>.json
set -uo pipefail
cd "$(dirname "$0")/.."
S="$1"; W="$2"; N="${3:-200}"; OUT=results/diagnostico; mkdir -p "$OUT"
docker compose --profile scenario-a --profile scenario-b --profile scenario-c --profile scenario-d --profile scenario-e down --remove-orphans >/dev/null 2>&1
if [[ "$S" == c ]]; then FRANKENPHP_WORKERS=$W docker compose --profile scenario-c up -d >/dev/null 2>&1
else OCTANE_WORKERS=$W docker compose --profile scenario-d up -d >/dev/null 2>&1; fi
for i in $(seq 1 60); do curl -sf localhost:${BENCH_PORT:-8080}/health >/dev/null && break; sleep 1; done
curl -s localhost:${BENCH_PORT:-8080}/memory >/dev/null; curl -s localhost:${BENCH_PORT:-8080}/db >/dev/null   # aquecimento (descartado do reinício)
seqf=$(mktemp); conf=$(mktemp)
for i in $(seq 1 "$N"); do echo "$(curl -s localhost:${BENCH_PORT:-8080}/memory)"; echo "$(curl -s localhost:${BENCH_PORT:-8080}/db)"; done > "$seqf"
for i in $(seq 1 "$N"); do echo memory; echo db; done | xargs -P 16 -I{} curl -s -w '\n' localhost:${BENCH_PORT:-8080}/{} > "$conf"
python3 -I - "$seqf" "$conf" "$S" "$W" "$OUT/$S-w$W.json" <<'PY'
import sys,json,collections
sq,cf,s,w,out=sys.argv[1:6]
def parse(f):
    mem=collections.defaultdict(list); db=collections.defaultdict(set); n=0
    txt=open(f).read(); dec=json.JSONDecoder(); i=0
    while i<len(txt):
        while i<len(txt) and txt[i] in " \n": i+=1
        if i>=len(txt): break
        try: d,i=dec.raw_decode(txt,i)
        except Exception: i+=1; continue
        if not isinstance(d, dict): continue
        if 'counter' in d: mem[d['worker']].append(d['counter'])
        elif d.get('item'): db[d['worker']].add(d['item']['pg_pid'])
    return {k:{'n':len(v),'contador_min':min(v),'contador_max':max(v),'reinicios':sum(1 for a,b in zip(v,v[1:]) if b<=a)} for k,v in mem.items()}, {k:sorted(v) for k,v in db.items()}
r={}
for nome,f in (("sequencial",sq),("concorrente",cf)):
    m,d=parse(f); r[nome]={"workers_distintos_memory":len(m),"memory":m,"db_pg_pids_por_worker":d}
if not any(r[k]['memory'] for k in r): sys.exit('diagnóstico sem dados (aplicação não respondeu)')
json.dump({"cenario":s,"workers":int(w),**r},open(out,'w'),indent=1,ensure_ascii=False)
for nome in ("sequencial","concorrente"):
    x=r[nome]; print(f"{s.upper()} workers={w} {nome}: workers vistos={x['workers_distintos_memory']}; por worker:", {k:(v['n'],v['contador_max'],v['reinicios']) for k,v in x['memory'].items()}, "| pg_pids por worker:", {k:len(v) for k,v in x['db_pg_pids_por_worker'].items()})
PY
docker compose --profile scenario-c --profile scenario-d down --remove-orphans >/dev/null 2>&1
```

**scripts/analyze.py**

```python
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
    "e": "E — CI4 + FrankenPHP clássico (threads padrão)",
}
PLATEAU_S = 600  # duração do patamar (s) nas execuções de 15 min
ENDPOINTS = ["health", "compute", "memory", "db"]
CORES = {"a": "#8c8c8c", "b": "#4c78a8", "c": "#e07b39", "d": "#59a14f", "e": "#b07aa1"}


def load():
    data = {s: [] for s in NOMES}
    for p in sorted(RUNS.glob("*-run*/last-run.json")):
        s = p.parent.name.split("-")[0]
        m = json.load(open(p))["metrics"]
        sf = "{phase:plateau}"  # patamar de 10 min (aquecimento, rampa e descida excluídos)
        dur = m[f"http_req_duration{sf}"]
        run = {
            "rps": m[f"http_reqs{sf}"]["count"] / PLATEAU_S,   # o campo `rate` da submétrica divide pela duração total
            "reqs": m[f"http_reqs{sf}"]["count"],
            "err": m[f"http_req_failed{sf}"].get("value", m[f"http_req_failed{sf}"].get("rate", 0)),
            "avg": dur["avg"],
            "p50": dur["med"],
            "p95": dur["p(95)"],
            "p99": dur.get("p(99)", float("nan")),
        }
        for e in ENDPOINTS:
            k = f"endpoint_{e}_duration{sf}"
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


def estatistica(data):
    """ANOVA de um fator e testes t de Welch par a par (n=3 por cenário: poder baixo, ver ressalva no texto)."""
    try:
        from scipy import stats
    except ImportError:
        print("scipy ausente: estatística não gerada")
        return
    pares = [("b", "a"), ("e", "b"), ("c", "a"), ("c", "b"), ("c", "e"), ("d", "c")]
    out = ["# Testes estatísticos (n=3 por cenário)", ""]
    for chave, rot in (("rps", "RPS"), ("p95", "Latência p95"), ("p99", "Latência p99")):
        grupos = [[r[chave] for r in data[s]] for s in data if len(data[s]) > 1]
        f, p = stats.f_oneway(*grupos)
        out += [f"## {rot}", f"ANOVA: F = {f:.1f}, p = {p:.2e}", "", "| Comparação | diferença (%) | t (Welch) | p | p ajustado (Bonferroni) |", "|---|---|---|---|---|"]
        for a_, b_ in pares:
            xa, xb = [r[chave] for r in data[a_]], [r[chave] for r in data[b_]]
            t, pv = stats.ttest_ind(xa, xb, equal_var=False)
            dif = (st.mean(xa) / st.mean(xb) - 1) * 100
            out.append(f"| {a_.upper()} vs {b_.upper()} | {dif:+.1f} | {t:.1f} | {pv:.2e} | {min(1, pv * len(pares)):.2e} |")
        out.append("")
    (OUT / "estatistica.md").write_text("\n".join(out))


def longos():
    """Teste de 30 min (c-long, d-long): RAM e CPU em janelas de 5 min do patamar, a partir de stats-samples.csv."""
    from datetime import datetime
    amostras = list(csv.DictReader(open(RUNS / "stats-samples.csv")))
    out = ["| Cenário | RPS | p95 (ms) | p99 (ms) | RAM 1ª janela (MiB) | RAM última janela (MiB) | RAM pico (MiB) |", "|---|---|---|---|---|---|---|"]
    series = {}
    for s in ("c", "d"):
        d = RUNS / f"{s}-long"
        if not (d / "last-run.json").exists():
            continue
        m = json.load(open(d / "last-run.json"))["metrics"]
        fim = datetime.fromisoformat((d / "finished_at").read_text().strip()).timestamp()
        ini = fim - 35 * 60 + 4 * 60   # início do patamar (2 min + 2 min de rampa)
        fimp = fim - 60                # fim do patamar
        pts = []
        for r in amostras:
            ts = int(r["ts"])
            if r["name"] != f"tcc-uema-app-{s}-1" or not (ini <= ts <= fimp):
                continue
            mem = r["mem_usage"].split("/")[0].strip()
            pts.append(((ts - ini) / 60, float(re.sub("[^0-9.]", "", mem)) * (1024 if "GiB" in mem else 1),
                        float(r["cpu_pct"].rstrip("%"))))
        series[s] = pts
        if not pts:
            continue
        prim = [p[1] for p in pts if p[0] <= 5]
        ult = [p[1] for p in pts if p[0] >= 25]
        sf = "{phase:plateau}"  # patamar de 30 min
        out.append(f"| {NOMES[s]} | {m[f'http_reqs{sf}']['count'] / 1800:.1f} | {m[f'http_req_duration{sf}']['p(95)']:.1f} | "
                   f"{m[f'http_req_duration{sf}']['p(99)']:.1f} | {st.mean(prim):.1f} | {st.mean(ult):.1f} | {max(p[1] for p in pts):.1f} |")
    (OUT / "tabela_longos.md").write_text("\n".join(out) + "\n")
    with open(OUT / "longos_ram.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cenario", "minuto_patamar", "ram_mib", "cpu_pct"])
        for s, pts in series.items():
            for t, ram, cpu in pts:
                w.writerow([s, f"{t:.2f}", ram, cpu])
    globals()["_SERIES"] = series


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
    for a_, b_ in [("b", "a"), ("e", "b"), ("c", "a"), ("c", "b"), ("c", "e"), ("d", "c"), ("d", "a")]:
        if a_ in agg and b_ in agg:
            g = (agg[a_]["rps"][0] / agg[b_]["rps"][0] - 1) * 100
            ganhos.append(f"{a_.upper()} vs {b_.upper()}: {g:+.1f}% RPS")
    (OUT / "ganhos.txt").write_text("\n".join(ganhos) + "\n")

    estatistica(data)
    longos()

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
    if globals().get("_SERIES"):
        fig, ax = plt.subplots(figsize=(7.5, 4))
        for s, pts in _SERIES.items():
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=CORES[s], label=NOMES[s].split(" — ")[0], lw=1.2)
        ax.set_xlabel("Tempo no patamar (min)")
        ax.set_ylabel("RAM do contêiner (MiB)")
        ax.set_ylim(bottom=0)
        ax.legend(title="Cenário")
        fig.tight_layout()
        fig.savefig(OUT / "fig_ram_longo.png", dpi=200)
        plt.close(fig)
    print("OK:", OUT)


if __name__ == "__main__":
    main()
```

### APÊNDICE E – Controladores dos endpoints

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
        MemoryState::$worker ??= bin2hex(random_bytes(4));

        $this->response->setHeader('Content-Type', 'application/json');
        echo json_encode([
            'counter'  => MemoryState::$counter,
            'worker'   => MemoryState::$worker,
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
            'worker'   => (MemoryState::$worker ??= bin2hex(random_bytes(4))),
            'scenario' => getenv('SCENARIO_NAME') ?: 'unknown',
        ]);
    }
}

class MemoryState
{
    public static int $counter = 0;
    public static ?string $worker = null; // identifica o worker (thread) que atende a requisição
}
```

**apps/laravel-octane/app/Http/Controllers/BenchmarkController.php**

```php
<?php

namespace App\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Routing\Controller;
use Illuminate\Support\Facades\DB;

class BenchmarkController extends Controller
{
    private static int $counter = 0;
    private static ?string $worker = null; // identifica o worker que atende a requisição

    public function health(): JsonResponse
    {
        return response()->json([
            'status'   => 'ok',
            'scenario' => env('SCENARIO_NAME', 'scenario-d'),
        ]);
    }

    public function compute(): JsonResponse
    {
        $size = (int) env('COMPUTE_SIZE', 1000);
        $data = [];

        for ($i = 0; $i < $size; $i++) {
            $data[] = [
                'id'    => $i + 1,
                'uuid'  => md5(uniqid((string) $i, true)),
                'value' => random_int(1, 999999),
                'label' => str_repeat('x', random_int(5, 20)),
            ];
        }

        return response()->json([
            'count'    => $size,
            'scenario' => env('SCENARIO_NAME', 'scenario-d'),
            'data'     => $data,
        ]);
    }

    public function memory(): JsonResponse
    {
        self::$counter++;
        self::$worker ??= bin2hex(random_bytes(4));

        return response()->json([
            'counter'  => self::$counter,
            'worker'   => self::$worker,
            'pid'      => getmypid(),
            'scenario' => env('SCENARIO_NAME', 'scenario-d'),
        ]);
    }

    public function db(): JsonResponse
    {
        $id = random_int(1, 10000);

        // pg_backend_pid() incluído na mesma query — sem round-trip extra.
        // Mesmo papel do endpoint /memory: prova persistência, mas agora
        // no nível da conexão PostgreSQL em vez do estado PHP em memória.
        $row = DB::selectOne(
            'SELECT id, name, value, pg_backend_pid() AS pg_pid FROM benchmark_items WHERE id = ?',
            [$id]
        );

        return response()->json([
            'item'     => $row,
            'php_pid'  => getmypid(),
            'worker'   => (self::$worker ??= bin2hex(random_bytes(4))),
            'scenario' => env('SCENARIO_NAME', 'scenario-d'),
        ]);
    }
}
```

### APÊNDICE F – Resultados por execução

**Tabela 6 – Resultados de cada uma das 15 execuções de 15 minutos**

| Execução | RPS | Latência p50 (ms) | Latência p95 (ms) | Latência p99 (ms) | Erros (%) |
|---|---|---|---|---|---|
| A – execução 1 | 144,1 | 686,5 | 782,9 | 797,3 | 0,00 |
| A – execução 2 | 143,2 | 688,2 | 787,5 | 802,7 | 0,00 |
| A – execução 3 | 143,9 | 687,6 | 786,4 | 801,4 | 0,00 |
| B – execução 1 | 154,7 | 605,3 | 710,4 | 792,6 | 0,00 |
| B – execução 2 | 157,5 | 600,3 | 704,2 | 766,5 | 0,00 |
| B – execução 3 | 156,3 | 602,5 | 715,5 | 789,5 | 0,00 |
| C – execução 1 | 314,3 | 301,4 | 394,8 | 406,8 | 0,00 |
| C – execução 2 | 314,9 | 301,2 | 394,1 | 405,4 | 0,00 |
| C – execução 3 | 325,2 | 297,9 | 393,4 | 404,7 | 0,00 |
| D – execução 1 | 350,4 | 287,6 | 375,2 | 397,0 | 0,00 |
| D – execução 2 | 352,2 | 287,9 | 375,5 | 396,8 | 0,00 |
| D – execução 3 | 351,3 | 287,2 | 373,2 | 396,5 | 0,00 |
| E – execução 1 | 175,8 | 524,3 | 658,5 | 710,1 | 0,00 |
| E – execução 2 | 173,6 | 525,4 | 675,8 | 742,1 | 0,00 |
| E – execução 3 | 177,0 | 524,2 | 647,4 | 709,8 | 0,00 |

Fonte: elaborado pelo próprio autor (2026). Nota: estatísticas sobre toda a execução, incluindo as rampas.

**Tabela 7 – Resultados dos testes longos de 30 minutos de patamar**

| Teste | RPS | Latência p50 (ms) | Latência p95 (ms) | Latência p99 (ms) | Erros (%) |
|---|---|---|---|---|---|
| C – teste longo (30 min) | 310,1 | 306,3 | 396,1 | 406,7 | 0,00 |
| D – teste longo (30 min) | 346,8 | 293,9 | 376,5 | 397,0 | 0,00 |

Fonte: elaborado pelo próprio autor (2026).

### APÊNDICE G – Ambiente de execução

Saída dos comandos de inspeção do hospedeiro, registrada pelo autor antes da coleta.

```
Linux andre-vaio 7.0.0-38-generic #38-Ubuntu SMP PREEMPT_DYNAMIC Fri Sep  4 09:10:14 UTC 2026 x86_64 GNU/Linux
CPU(s):                                    16
Nome do modelo:                            AMD Ryzen 7 5700U with Radeon Graphics
               total       usada       livre    compart.  buff/cache  disponível
Mem.:           14Gi       8,0Gi       5,1Gi       347Mi       2,1Gi       6,5Gi
Swap:          4,0Gi       2,7Gi       1,3Gi
Docker version 28.1.1, build 4eba377
Docker Compose version v2.31.0-desktop.2
FrankenPHP v1.13.0 PHP 8.3.35 Caddy v2.11.7 h1:yj0Y4fYZGPkSv
PHP 8.3.35 (cli) (built: Oct  6 2026 01:29:10) (ZTS)
PHP 8.3.35 (cli) (built: Sep 25 2026 17:44:10) (NTS)
```
