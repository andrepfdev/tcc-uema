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
  run --quiet --no-summary \
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
RESULTS_FILE="${RESULTS_DIR}/scenario-${SCENARIO}-${TEST}-$(date '+%Y%m%d_%H%M%S').json"

docker compose --profile "$PROFILE" run --rm k6 \
  run \
  --out "experimental-prometheus-rw=${TARGET_URL}" \
  --summary-export /scripts/../results/last-run.json \
  -e TARGET_URL="$TARGET_URL" \
  -e SCENARIO_NAME="$PROFILE" \
  "/scripts/${TEST}.js" \
  | tee "${RESULTS_FILE%.json}.txt"

echo ""
echo "======================================================================"
echo " Teste concluído!"
echo " Resultados: ${RESULTS_FILE%.json}.txt"
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
