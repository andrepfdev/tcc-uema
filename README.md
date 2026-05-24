# TCC UEMA — Benchmark PHP Architecture

**Análise Comparativa de Desempenho na Era da Persistência em Memória:**
O Impacto da Arquitetura Worker do FrankenPHP no Framework CodeIgniter 4 em Contraste com o Ecossistema Laravel

**Autor:** André Pereira Ferreira
**Instituição:** Universidade Estadual do Maranhão (UEMA)

---

## Pré-requisitos

| Ferramenta | Versão mínima |
|------------|--------------|
| Docker     | 24.x         |
| Docker Compose | 2.x      |
| sudo       | para limpeza de cache do SO |

---

## Estrutura do Projeto

```
tcc-uema/
├── apps/
│   ├── ci4-base/           # App CodeIgniter 4 (Cenários A, B, C)
│   └── laravel-octane/     # App Laravel + Octane (Cenário D)
├── docker/
│   ├── scenario-a/         # PHP-FPM + Nginx config
│   ├── scenario-b/         # FrankenPHP Classic Caddyfile
│   ├── scenario-c/         # FrankenPHP Worker Caddyfile
│   └── scenario-d/         # Laravel Octane Dockerfile
├── k6/                     # Scripts de carga (smoke + load)
├── monitoring/             # Prometheus + Grafana (auto-provisionado)
├── scripts/                # Automação dos testes
└── results/                # Resultados gerados (git-ignorado)
```

---

## Cenários

| # | Nome          | Stack                                          | Workers |
|---|---------------|------------------------------------------------|---------|
| A | Legacy        | CI4 4.7 + PHP-FPM Alpine + Nginx               | 4       |
| B | Classic       | CI4 4.7 + FrankenPHP Classic Mode              | —       |
| C | Vanguard      | CI4 4.7 + FrankenPHP Worker Mode (nativo 4.7+) | 4       |
| D | Referência    | Laravel + Laravel Octane + FrankenPHP          | 4       |

**Budget total por cenário: 1.0 CPU / 512MB RAM** — aplicado ao stack completo:
- Cenário A: `app-a` (0.85 CPU / 448MB) + `nginx-a` (0.15 CPU / 64MB) = 1.0 / 512MB
- Cenários B, C, D: 1 container único com 1.0 CPU / 512MB

Container k6 (injetor): **2.0 CPU / 512MB RAM**

Endpoints de teste (idênticos nos 4 cenários):

- `GET /health` — latência base, sem processamento
- `GET /compute` — serialização JSON de 1.000 elementos (CPU-bound)
- `GET /memory` — contador persistente + PID (prova estado entre requests)

---

## Execução Rápida

### 1. Build das imagens

```bash
docker compose build
```

### 2. Rodar um cenário completo

```bash
# Cenário A — smoke test (sanidade)
./scripts/run-scenario.sh a smoke

# Cenário A — load test (dados do TCC)
./scripts/run-scenario.sh a load

# Cenário B
./scripts/run-scenario.sh b load

# Cenário C
./scripts/run-scenario.sh c load

# Cenário D
./scripts/run-scenario.sh d load
```

O script `run-scenario.sh` automaticamente:
1. Derruba o cenário anterior
2. **Limpa o cache do SO** (page cache, dentries, inodes)
3. Aguarda 3s para a memória assentar
4. Sobe o novo cenário + observabilidade
5. Espera o app estar pronto
6. Executa o teste k6

### 3. Visualizar métricas em tempo real

Acesse **http://localhost:3000** (Grafana)
- Usuário: `admin`
- Senha: `benchmark`

Dashboard "TCC UEMA — PHP Architecture Benchmark" carregado automaticamente.

### 4. Encerrar o ambiente

```bash
docker compose --profile scenario-a down   # ou b, c, d
```

---

## Limpeza de Cache do SO (Manual)

Entre cenários, o cache do kernel pode enviesar os resultados.
O `run-scenario.sh` faz isso automaticamente, mas se precisar manualmente:

```bash
./scripts/clear-cache.sh
```

Ou diretamente:

```bash
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches
```

Para evitar prompt de senha (`sudo`), adicione ao `/etc/sudoers`:

```
seu_usuario ALL=(ALL) NOPASSWD: /usr/bin/tee /proc/sys/vm/drop_caches
```

---

## Comandos Detalhados por Cenário

### Cenário A — PHP-FPM + Nginx

```bash
# Subir
docker compose --profile scenario-a up -d

# Validar endpoints
curl http://localhost:8080/health
curl http://localhost:8080/compute
curl http://localhost:8080/memory

# Smoke test
docker compose --profile scenario-a run --rm k6 \
  run /scripts/smoke.js -e TARGET_URL=http://nginx-a:8080

# Load test
docker compose --profile scenario-a run --rm k6 \
  run /scripts/load.js -e TARGET_URL=http://nginx-a:8080

# Encerrar
docker compose --profile scenario-a down
```

### Cenário B — FrankenPHP Classic Mode

```bash
docker compose --profile scenario-b up -d

curl http://localhost:8080/health
# Esperado: {"status":"ok","scenario":"scenario-b"}

docker compose --profile scenario-b run --rm k6 \
  run /scripts/load.js -e TARGET_URL=http://app-b:8080

docker compose --profile scenario-b down
```

### Cenário C — FrankenPHP Worker Mode

```bash
docker compose --profile scenario-c up -d

# Validar persistência de estado (prova do Worker Mode)
curl http://localhost:8080/memory  # {"counter":1,"pid":7}
curl http://localhost:8080/memory  # {"counter":2,"pid":7}  ← mesmo PID!
curl http://localhost:8080/memory  # {"counter":3,"pid":7}  ← contador cresce!

# Em contraste, no Cenário A (PHP-FPM):
# {"counter":1,"pid":12}  ← sempre 1, PID pode variar

docker compose --profile scenario-c run --rm k6 \
  run /scripts/load.js -e TARGET_URL=http://app-c:8080

docker compose --profile scenario-c down
```

### Cenário D — Laravel Octane + FrankenPHP

```bash
docker compose --profile scenario-d up -d

curl http://localhost:8080/health
# Esperado: {"status":"ok","scenario":"scenario-d"}

docker compose --profile scenario-d run --rm k6 \
  run /scripts/load.js -e TARGET_URL=http://app-d:8080

docker compose --profile scenario-d down
```

---

## Coletar Snapshot de Recursos

Após o load test (com os containers ainda rodando):

```bash
./scripts/collect-results.sh a   # ou b, c, d
```

Gera um arquivo em `results/` com CPU%, RAM, I/O de rede e disco de cada container.

---

## Observabilidade

| Serviço    | URL                     | Credenciais        |
|------------|-------------------------|--------------------|
| Grafana    | http://localhost:3000   | admin / benchmark  |
| Prometheus | http://localhost:9090   | —                  |
| cAdvisor   | http://localhost:8081   | —                  |

Métricas coletadas:
- **k6** → push via Prometheus remote_write → Grafana
- **cAdvisor** → scrape por Prometheus → Grafana
- RPS, latência p50/p95/p99, taxa de erros, CPU%, RAM por container

---

## Detalhes Técnicos

Consulte [CENARIOS.md](CENARIOS.md) para documentação aprofundada de cada cenário,
decisões arquiteturais e a bridge `worker.php` do CI4.
