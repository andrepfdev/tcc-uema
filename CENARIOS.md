# Cenários de Benchmark — Documentação Técnica

## Visão Geral

Cada cenário é executado de forma completamente isolada via Docker Compose profiles.
Antes de cada execução, o cache do SO é limpo para garantir medições independentes.

---

## Cenário A — Legacy: CI4 + PHP-FPM + Nginx

**Objetivo:** Baseline da arquitetura PHP tradicional em produção.

**Stack:**
- `php:8.3-fpm-alpine` com OPcache
- `nginx:alpine` como reverse proxy
- Pool FPM: `pm=static`, `pm.max_children=4`

**Comportamento do endpoint `/memory`:**
Cada request é atendido por um processo PHP diferente (ou o mesmo processo reutilizado
pelo pool, mas sem estado entre requests). O contador **reinicia a cada request**.

```
GET /memory → {"counter":1,"pid":12}
GET /memory → {"counter":1,"pid":14}  ← PID pode variar; contador sempre 1
```

**Limitações:** bootstrap completo do framework a cada request — autoload,
DI container, roteamento, instanciação de serviços.

---

## Cenário B — Modern Classic: CI4 + FrankenPHP Classic Mode

**Objetivo:** Isolar o ganho do motor FrankenPHP vs o Worker Mode.
FrankenPHP Classic é um substituto drop-in do PHP-FPM.

**Stack:**
- `dunglas/frankenphp:latest-php8.3-alpine`
- Caddyfile com `php_server` **sem** diretiva `worker`
- Cada request: novo contexto PHP (sem estado persistente)

**Por que este cenário existe:**
Se o Cenário C (Worker Mode) é mais rápido que o A, não fica claro
se o ganho vem do FrankenPHP em si ou do Worker Mode especificamente.
O Cenário B permite isolar essa variável.

**Comportamento do endpoint `/memory`:**
Idêntico ao Cenário A — sem persistência de estado.

---

## Cenário C — Vanguard: CI4 + FrankenPHP Worker Mode (suporte nativo 4.7+)

**Objetivo:** Demonstrar a vantagem de desempenho da persistência em memória
no CodeIgniter 4 com FrankenPHP Worker Mode usando o suporte nativo do framework.

**Stack:**
- `dunglas/frankenphp:latest-php8.3-alpine`
- Caddyfile com `worker { file public/frankenphp-worker.php; num 4 }`
- `public/frankenphp-worker.php` — entry point oficial gerado por `php spark worker:install`
- `app/Config/WorkerMode.php` — configuração de serviços persistentes

### Suporte Nativo do CI4 4.7.3.0

> **Added in version 4.7.0** — Worker Mode is currently experimental.
> Source: https://codeigniter.com/user_guide/installation/worker_mode.html

A partir da versão 4.7.0, o CI4 inclui suporte nativo ao Worker Mode via:

```bash
php spark worker:install
```

Este comando gera dois arquivos:
- `Caddyfile` — configuração FrankenPHP com worker mode habilitado
- `public/frankenphp-worker.php` — entry point com gerenciamento de estado oficial

### Como o CI4 Gerencia o Estado entre Requests

O CI4 4.7.3 resolve os problemas de state leakage automaticamente:

| Mecanismo             | Comportamento                                                       |
|-----------------------|---------------------------------------------------------------------|
| `Services::resetForWorkerMode()` | Destrói serviços não-persistentes; mantém os de `$persistentServices` |
| `Factories::reset()`  | Reseta Models e Config instances — instâncias frescas por request   |
| Superglobals isolation| `$_GET`, `$_POST`, `$_SERVER` etc. injetados isoladamente por request |
| `DatabaseConfig::reconnectForWorkerMode()` | Reconecta DB se necessário; rola back transações abertas |

### `app/Config/WorkerMode.php`

```php
public array $persistentServices = [
    'autoloader', 'locator', 'exceptions', 'commands',
    'codeigniter', 'superglobals', 'routes', 'cache',
];
public bool $forceGarbageCollection = true;
```

Serviços fora de `$persistentServices` são destruídos após cada request.
O `MemoryState` do `BenchmarkController` usa uma propriedade `static` — não é um serviço
do CI4, portanto **não** é afetado pelo reset, sobrevivendo ao loop do worker.

**Comportamento do endpoint `/memory`:**
```
GET /memory → {"counter":1,"pid":7}
GET /memory → {"counter":2,"pid":7}  ← mesmo processo!
GET /memory → {"counter":3,"pid":7}  ← contador cresce continuamente
```

O PID constante prova que o mesmo processo PHP está atendendo múltiplas requests.
O contador crescente prova que o estado em memória persiste entre requests.

---

## Cenário D — Referência: Laravel + Laravel Octane + FrankenPHP

**Objetivo:** Benchmark de mercado. Laravel Octane suporta Worker Mode nativamente
sem necessidade de bridge customizada.

**Stack:**
- `dunglas/frankenphp:latest-php8.3-alpine`
- Laravel 13 + Laravel Octane 2.x
- `php artisan octane:frankenphp --workers=4 --port=8080`

**Por que incluir Laravel:**
Permite avaliar se a bridge CI4 atinge performance comparável ao ecossistema
que tem suporte nativo ao Worker Mode, e justifica ou não a complexidade de
implementação da bridge no contexto de projetos CI4 legados.

**Comportamento do endpoint `/memory`:**
Idêntico ao Cenário C — Octane preserva singletons do container entre requests.

---

## Variável de Controle: Número de Workers

Todos os cenários usam **4 workers/processos** para atendimento de requests:

| Cenário | Configuração                              |
|---------|-------------------------------------------|
| A       | `pm.max_children = 4` (FPM)              |
| B       | — (classic mode, sem workers fixos)       |
| C       | `worker { num 4 }` (Caddyfile)           |
| D       | `--workers=4` (Octane)                   |

Isso garante que diferenças de throughput não sejam explicadas por concorrência
diferente entre os cenários.

---

## Equilíbrio de Recursos entre Cenários

### Problema

O Cenário A é o único que usa **dois containers** (PHP-FPM + Nginx). Se ambos
recebessem `1.0 CPU / 512MB` cada, o stack total seria o dobro dos outros cenários,
tornando a comparação injusta.

### Solução adotada: orçamento total igualado

O limite de `1.0 CPU / 512MB` é aplicado ao **stack completo** de cada cenário,
dividido proporcionalmente no Cenário A:

| Container  | Cenário | CPU   | RAM   | Justificativa                              |
|------------|---------|-------|-------|--------------------------------------------|
| `app-a`    | A       | 0.85  | 448M  | Processo PHP-FPM (carga principal)         |
| `nginx-a`  | A       | 0.15  | 64M   | Reverse proxy (overhead arquitetural)      |
| **Total A**|         | **1.0** | **512M** | **Igual aos Cenários B, C, D**         |
| `app-b`    | B       | 1.0   | 512M  | FrankenPHP Classic (processo único)        |
| `app-c`    | C       | 1.0   | 512M  | FrankenPHP Worker (processo único)         |
| `app-d`    | D       | 1.0   | 512M  | Laravel Octane (processo único)            |

### Implicação metodológica

A divisão `0.85 / 0.15` entre PHP-FPM e Nginx é uma **variável controlada** do experimento.
O Nginx não é um componente de aplicação — é **overhead arquitetural** inerente à topologia
PHP-FPM. Portanto, seu custo de CPU/RAM faz parte do custo total do Cenário A.

Isso é uma das hipóteses que o TCC testa: arquiteturas que eliminam o reverse proxy
externo (FrankenPHP é um servidor web completo) têm menos overhead operacional.

---

## Isolamento dos Testes

### Cache do Sistema Operacional

Entre cada cenário, o cache do kernel é limpo:

```bash
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches
```

**O que isso libera:**
- **Page cache** (1): conteúdo de arquivos lidos recentemente (PHP, vendor)
- **Dentries + inodes** (2): cache de estrutura de diretórios
- **Ambos** (3): combinação dos anteriores

Sem essa limpeza, o 2º e 3º cenários se beneficiam de arquivos já carregados
na RAM do host pelo cenário anterior, inflando artificialmente os resultados.

### OPcache

O OPcache **vive dentro do processo PHP** do container — não é afetado pela
limpeza de cache do SO. Cada cenário compila e cacheia os opcodes
independentemente durante sua execução.

### Limites de Recursos Docker

```yaml
deploy:
  resources:
    limits:
      cpus: "1.0"
      memory: "512M"
```

`deploy.resources.limits` garante que nenhum cenário monopolize CPU ou RAM do host,
tornando os resultados comparáveis mesmo em máquinas com mais recursos.

---

## Banco de Dados — PostgreSQL 16

### Por que PostgreSQL (e não MySQL)

O PostgreSQL usa um **processo do SO por conexão** (~5–10 MB RAM cada), tornando o
custo de abrir uma nova conexão significativamente maior que o MySQL (thread-based).

Isso amplifica exatamente o diferencial que o Worker Mode demonstra:

| Cenário | Comportamento com PostgreSQL |
|---------|------------------------------|
| A (PHP-FPM) | Nova conexão PG estabelecida a cada request → overhead de handshake TCP + autenticação + alocação de processo no servidor |
| B (FrankenPHP Classic) | Mesmo comportamento do A — sem persistência de conexão |
| C (FrankenPHP Worker) | Conexão estabelecida uma vez no bootstrap, reutilizada em todos os requests subsequentes |
| D (Laravel Octane) | Mesmo comportamento do C — Octane gerencia reconexão automaticamente |

### Tabela de benchmark

```sql
CREATE TABLE benchmark_items (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100),
    value       INTEGER,
    description TEXT
);
-- 10.000 registros pré-populados via docker/postgres/init.sql
```

A query usa `WHERE id = random_int(1, 10000)` — ID aleatório por request
para evitar que o cache do query planner oculte o custo real de conexão.

---

## Endpoints de Teste

### `GET /health`
- Retorna: `{"status":"ok","scenario":"scenario-X"}`
- Propósito: medir latência base sem processamento
- Esperado: < 10ms em todos os cenários

### `GET /compute`
- Gera array de 1.000 elementos com `md5(uniqid())`, `random_int`, `str_repeat`
- Serializa para JSON e retorna
- Propósito: CPU-bound, sem I/O — mede throughput puro
- Tamanho configurável via env `COMPUTE_SIZE`

### `GET /memory`
- Incrementa contador estático + retorna PID do processo
- Propósito: demonstrar persistência de estado no Worker Mode
- Em PHP-FPM/Classic: counter sempre retorna 1 (sem estado)
- Em Worker Mode: counter cresce continuamente

### `GET /db`
- Executa `SELECT id, name, value FROM benchmark_items WHERE id = ?` com ID aleatório
- Retorna o item + PID do processo
- Propósito: **demonstrar persistência de conexão PostgreSQL no Worker Mode**
- Em PHP-FPM/Classic: nova conexão PG a cada request
- Em Worker Mode: conexão reutilizada — apenas o tempo de query é pago

### Distribuição no load test (`k6/load.js`)

| Endpoint  | Peso | O que mede |
|-----------|------|------------|
| `/health` | 10%  | Overhead base da stack |
| `/compute`| 30%  | Throughput CPU-bound |
| `/memory` | 30%  | Persistência de estado em memória |
| `/db`     | 30%  | Persistência de conexão PG |

---

## Scripts de Carga (k6)

### `smoke.js` — Sanidade
- 1 VU, 1 minuto
- Executa os 3 endpoints em sequência com 100ms de pausa
- Threshold: p95 < 500ms, erros < 1%
- Use antes de qualquer load test

### `load.js` — Carga Principal
- Rampa: 10 → 100 VUs em 5 minutos
- Pico sustentado: 100 VUs por 10 minutos
- Distribuição: 20% health / 40% compute / 40% memory
- Threshold: p99 < 2s, erros < 5%
- Output: Prometheus remote_write → Grafana em tempo real
