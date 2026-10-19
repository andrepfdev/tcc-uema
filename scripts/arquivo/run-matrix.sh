#!/usr/bin/env bash
# run-matrix.sh — N rodadas em ordem rotativa (a,b,c,d). REGRA: sempre refaz TUDO.
# Não pula rodadas existentes e, se qualquer rodada falhar, ABORTA a bateria inteira (refazer do zero).
# Cada rodada é arquivada em results/runs/<cenário>-run<N>/.
# Uso: ./scripts/run-matrix.sh [rodadas=3]
set -uo pipefail
cd "$(dirname "$0")/.."
ROUNDS="${1:-3}"
if [[ -d results/runs && -n "$(ls -A results/runs 2>/dev/null)" ]]; then
  echo "ERRO: results/runs não está vazio. Arquive (mv results/runs results/runs-<rótulo>) antes; a bateria sempre recomeça do zero."; exit 1
fi
mkdir -p results/runs
for r in $(seq 1 "$ROUNDS"); do
  for s in a b c d; do
    dir="results/runs/${s}-run${r}"
    mkdir -p "$dir"
    rm -f results/last-run.json
    ./scripts/run-scenario.sh "$s" load 2>&1 | tee "$dir/console.log"
    if ! grep -q "Teste concluído" "$dir/console.log" || [[ ! -f results/last-run.json ]]; then
      echo "FALHA em $dir: bateria ABORTADA. Descarte results/runs e refaça TUDO."; exit 1
    fi
    docker stats --no-stream --format '{{.Name}},{{.CPUPerc}},{{.MemUsage}}' > "$dir/docker-stats-post.csv" 2>/dev/null || true
    mv results/last-run.json "$dir/"
    mv results/dashboard-scenario-${s}-load-*.html "$dir/" 2>/dev/null
    mv results/scenario-${s}-load-*.txt "$dir/" 2>/dev/null
    date -Is > "$dir/finished_at"
  done
done
docker compose --profile scenario-a --profile scenario-b --profile scenario-c --profile scenario-d down --remove-orphans
