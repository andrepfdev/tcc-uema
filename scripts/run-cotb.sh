#!/usr/bin/env bash
# run-cotb.sh — Coleta complementar para o artigo do COTB 2027 (não altera results/runs nem os dados do TCC).
# REGRA: sempre refaz TUDO do zero; qualquer falha aborta a execução inteira (arquive results/cotb e recomece).
#
#  1) taxa de chegada fixa (modelo aberto, RATE req/s): A–E x 3, ordem rotativa -> results/cotb/<c>-rate<N>
#  2) repetições extras da carga fechada (100 VUs, 15 min): A–E x 2 (reps 4 e 5)  -> results/cotb/<c>-rep<N>
# Cada execução: contêineres anteriores derrubados, Prometheus zerado, cache do SO liberado, sem rebuild.
# Amostrador de CPU/RAM (docker stats, ~3 s) durante toda a coleta -> results/cotb/stats-samples.csv.
# Requisitos: sudo sem senha para `tee /proc/sys/vm/drop_caches`, imagens já construídas, porta 18080 livre,
# notebook na tomada e sem outros programas em uso (~7 h).
set -uo pipefail
cd "$(dirname "$0")/.."
export NO_BUILD=1
export BENCH_PORT="${BENCH_PORT:-18080}"
RATE="${RATE:-100}"
(echo >/dev/tcp/127.0.0.1/"$BENCH_PORT") 2>/dev/null && { echo "ERRO: porta $BENCH_PORT já está em uso."; exit 1; }
[[ -z "$(ls -A results/cotb 2>/dev/null)" ]] || { echo "ERRO: results/cotb não está vazio. Arquive antes (mv); a coleta sempre recomeça do zero."; exit 1; }
echo 3 | sudo -n tee /proc/sys/vm/drop_caches >/dev/null 2>&1 || { echo "ERRO: sudo -n tee /proc/sys/vm/drop_caches não funciona (sudoers)."; exit 1; }
for s in a b c d e; do docker image inspect "tcc-uema-app-$s" >/dev/null 2>&1 || { echo "ERRO: imagem tcc-uema-app-$s ausente (rode docker compose build)."; exit 1; }; done
mkdir -p results/cotb
FLAG=$(mktemp); trap 'rm -f "$FLAG"' EXIT
falha() { echo "FALHA: $1 — coleta ABORTADA. Arquive results/cotb e refaça TUDO."; rm -f "$FLAG"; exit 1; }
./scripts/sample-stats.sh results/cotb/stats-samples.csv "$FLAG" &

rodar() {  # <cenário> <teste> <rótulo>   (variáveis RATE/WARMUP_S/RAMP_S/PLATEAU_S vêm do ambiente)
  local s="$1" test="$2" dir="results/cotb/$3"
  mkdir -p "$dir"; rm -f results/last-run.json
  ./scripts/run-scenario.sh "$s" "$test" 2>&1 | tee "$dir/console.log"
  grep -q "Teste concluído" "$dir/console.log" && [[ -f results/last-run.json ]] || falha "$dir"
  docker stats --no-stream --format '{{.Name}},{{.CPUPerc}},{{.MemUsage}}' > "$dir/docker-stats-post.csv" 2>/dev/null || true
  mv results/last-run.json "$dir/"
  mv results/dashboard-scenario-${s}-${test}-*.html "$dir/" 2>/dev/null
  mv results/scenario-${s}-${test}-*.txt "$dir/" 2>/dev/null
  date -Is > "$dir/finished_at"
  # Validade do teste de taxa fixa: nenhuma iteração descartada (senão a taxa pedida não foi sustentada)
  if [[ "$test" == rate ]]; then
    python3 -I - "$dir/last-run.json" <<'PY' || falha "$dir: iterações descartadas (taxa não sustentada)"
import json, sys
m = json.load(open(sys.argv[1]))["metrics"]
dropped = m.get("dropped_iterations", {}).get("count", 0)
print(f"dropped_iterations = {dropped}")
sys.exit(1 if dropped > 0 else 0)
PY
  fi
}

echo "##### 1) TAXA FIXA ${RATE} req/s: A–E x 3 #####"
for r in 1 2 3; do for s in a b c d e; do
  RATE="$RATE" WARMUP_S=60 RAMP_S=0 PLATEAU_S=480 rodar "$s" rate "${s}-rate${r}"
done; done
echo "##### 2) REPETIÇÕES EXTRAS (carga fechada) A–E x 2 #####"
for r in 4 5; do for s in a b c d e; do
  PLATEAU_S=600 rodar "$s" load "${s}-rep${r}"
done; done
docker compose --profile scenario-a --profile scenario-b --profile scenario-c --profile scenario-d --profile scenario-e down --remove-orphans
rm -f "$FLAG"; echo "COLETA COTB COMPLETA"
