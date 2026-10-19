#!/usr/bin/env bash
# Sensibilidade do cenário E (FrankenPHP clássico com a quantidade PADRÃO de threads): 3 execuções, mesmas regras da bateria.
# Limpeza do cache do SO (sudo -n), sem rebuild, amostrador de CPU/RAM, aborta em falha (refazer as 3).
set -uo pipefail
cd "$(dirname "$0")/.."
export NO_BUILD=1
for r in 1 2 3; do [[ ! -e results/runs/e-run$r ]] || { echo "ERRO: results/runs/e-run$r já existe; arquive antes (sempre refazer as 3)."; exit 1; }; done
echo 3 | sudo -n tee /proc/sys/vm/drop_caches >/dev/null 2>&1 || { echo "ERRO: sudo -n tee /proc/sys/vm/drop_caches não funciona (sudoers)."; exit 1; }
FLAG=$(mktemp); trap 'rm -f "$FLAG"' EXIT
./scripts/sample-stats.sh results/runs/stats-samples-e.csv "$FLAG" &
for r in 1 2 3; do
  dir="results/runs/e-run$r"; mkdir -p "$dir"; rm -f results/last-run.json
  PLATEAU_S=600 ./scripts/run-scenario.sh e load 2>&1 | tee "$dir/console.log"
  if ! grep -q "Teste concluído" "$dir/console.log" || [[ ! -f results/last-run.json ]]; then
    echo "FALHA em $dir: ABORTADO. Descarte results/runs/e-run* e refaça as 3."; rm -f "$FLAG"; exit 1
  fi
  docker stats --no-stream --format '{{.Name}},{{.CPUPerc}},{{.MemUsage}}' > "$dir/docker-stats-post.csv" 2>/dev/null || true
  mv results/last-run.json "$dir/"
  mv results/dashboard-scenario-e-load-*.html "$dir/" 2>/dev/null
  mv results/scenario-e-load-*.txt "$dir/" 2>/dev/null
  date -Is > "$dir/finished_at"
done
docker compose --profile scenario-e down --remove-orphans
rm -f "$FLAG"; echo "SENSIBILIDADE E COMPLETA"
