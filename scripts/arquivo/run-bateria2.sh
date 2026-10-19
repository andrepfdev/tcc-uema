#!/usr/bin/env bash
# Bateria completa (REGRA: sempre refaz TUDO; qualquer falha aborta a bateria inteira):
#  1) oficial: A,B,C,D x3 em ordem rotativa      2) sensibilidades: E (B padrão) e F (D sem reciclagem) x3
#  3) longos (30 min no patamar): C, D e F
# Cada execução limpa o cache do SO (sudo -n) e usa imagens já construídas (NO_BUILD=1).
set -uo pipefail
cd "$(dirname "$0")/.."
export NO_BUILD=1
if [[ -d results/runs && -n "$(ls -A results/runs 2>/dev/null)" ]]; then
  echo "ERRO: results/runs não está vazio. Arquive (mv results/runs results/runs-<rótulo>); a bateria sempre recomeça do zero."; exit 1
fi
echo 3 | sudo -n tee /proc/sys/vm/drop_caches >/dev/null 2>&1 || { echo "ERRO: sudo -n tee /proc/sys/vm/drop_caches não funciona (sudoers)."; exit 1; }
mkdir -p results/runs
FLAG=$(mktemp); trap 'rm -f "$FLAG"' EXIT
./scripts/sample-stats.sh results/runs/stats-samples.csv "$FLAG" &
rodar() {  # <cenário> <teste> <rótulo>
  local s="$1" test="$2" dir="results/runs/$3"
  mkdir -p "$dir"; rm -f results/last-run.json
  ./scripts/run-scenario.sh "$s" "$test" 2>&1 | tee "$dir/console.log"
  if ! grep -q "Teste concluído" "$dir/console.log" || [[ ! -f results/last-run.json ]]; then
    echo "FALHA em $dir: bateria ABORTADA. Descarte results/runs e refaça TUDO."; rm -f "$FLAG"; exit 1
  fi
  docker stats --no-stream --format '{{.Name}},{{.CPUPerc}},{{.MemUsage}}' > "$dir/docker-stats-post.csv" 2>/dev/null || true
  mv results/last-run.json "$dir/"
  mv results/dashboard-scenario-${s}-${test}-*.html "$dir/" 2>/dev/null
  mv results/scenario-${s}-${test}-*.txt "$dir/" 2>/dev/null
  date -Is > "$dir/finished_at"
}
for r in 1 2 3; do for s in a b c d; do PLATEAU_S=600 rodar "$s" load "${s}-run${r}"; done; done
for r in 1 2 3; do for s in e f; do PLATEAU_S=600 rodar "$s" load "${s}-run${r}"; done; done
for s in c d f; do PLATEAU_S=1800 rodar "$s" long "${s}-long"; done
docker compose --profile scenario-a --profile scenario-b --profile scenario-c --profile scenario-d --profile scenario-e --profile scenario-f down --remove-orphans
rm -f "$FLAG"; echo "BATERIA COMPLETA"
