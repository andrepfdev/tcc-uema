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
