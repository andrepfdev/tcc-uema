#!/usr/bin/env bash
# Testes longos (30 min no patamar de 100 usuários) dos cenários C e D, para observar a memória ao longo do tempo.
# Mesmas regras da bateria: limpeza do cache do SO (sudo -n), sem rebuild, amostrador de CPU/RAM, aborta em falha.
set -uo pipefail
cd "$(dirname "$0")/.."
export NO_BUILD=1
for s in c d; do [[ ! -e results/runs/$s-long ]] || { echo "ERRO: results/runs/$s-long já existe; arquive antes (a bateria recomeça do zero)."; exit 1; }; done
echo 3 | sudo -n tee /proc/sys/vm/drop_caches >/dev/null 2>&1 || { echo "ERRO: sudo -n tee /proc/sys/vm/drop_caches não funciona (sudoers)."; exit 1; }
FLAG=$(mktemp); trap 'rm -f "$FLAG"' EXIT
./scripts/sample-stats.sh results/runs/stats-samples-longos.csv "$FLAG" &
for s in c d; do
  dir="results/runs/$s-long"; mkdir -p "$dir"; rm -f results/last-run.json
  PLATEAU_S=1800 ./scripts/run-scenario.sh "$s" long 2>&1 | tee "$dir/console.log"
  if ! grep -q "Teste concluído" "$dir/console.log" || [[ ! -f results/last-run.json ]]; then
    echo "FALHA em $dir: ABORTADO. Descarte results/runs/*-long e refaça os dois."; rm -f "$FLAG"; exit 1
  fi
  docker stats --no-stream --format '{{.Name}},{{.CPUPerc}},{{.MemUsage}}' > "$dir/docker-stats-post.csv" 2>/dev/null || true
  mv results/last-run.json "$dir/"
  mv results/dashboard-scenario-${s}-long-*.html "$dir/" 2>/dev/null
  mv results/scenario-${s}-long-*.txt "$dir/" 2>/dev/null
  date -Is > "$dir/finished_at"
done
docker compose --profile scenario-c --profile scenario-d down --remove-orphans
rm -f "$FLAG"; echo "LONGOS COMPLETOS"
