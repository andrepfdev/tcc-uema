#!/usr/bin/env bash
# Rodada de captura (Grafana em tema claro, Chrome headless) no AMBIENTE FINAL, após a bateria.
# Uma execução por cenário (A-D); o print é tirado no minuto 14:20 (fora do patamar de 240-840 s).
# Não entra nas estatísticas. Mesmas regras da bateria: limpeza de cache (sudo -n), sem rebuild.
set -uo pipefail
cd "$(dirname "$0")/.."
export NO_BUILD=1
mkdir -p results/captura docs/figuras
[[ -z "$(ls -A results/captura 2>/dev/null)" ]] || { echo "ERRO: results/captura não está vazio; arquive antes."; exit 1; }
echo 3 | sudo -n tee /proc/sys/vm/drop_caches >/dev/null 2>&1 || { echo "ERRO: sudo -n tee drop_caches não funciona."; exit 1; }
URL='http://localhost:3000/d/tcc-uema-benchmark?kiosk&theme=light&from=now-16m&to=now'
for s in a b c d; do
  log=results/captura/console-$s.log
  ( until grep -q "running (14m2" "$log" 2>/dev/null; do sleep 2; done
    timeout 90 google-chrome --headless=new --no-sandbox --disable-gpu --user-data-dir=/tmp/claude-1000/chrome-prof \
      --window-size=1600,1140 --virtual-time-budget=20000 --screenshot="docs/figuras/grafana-$s.png" "$URL" >/dev/null 2>&1 ) &
  ./scripts/run-scenario.sh "$s" load > "$log" 2>&1
  wait
  grep -q "Teste concluído" "$log" || { echo "FALHA em $s: capture refazendo tudo."; exit 1; }
  mkdir -p results/captura/$s
  mv results/dashboard-scenario-$s-load-*.html results/scenario-$s-load-*.txt results/last-run.json results/captura/$s/ 2>/dev/null
done
docker compose --profile scenario-a --profile scenario-b --profile scenario-c --profile scenario-d --profile scenario-e --profile scenario-f down --remove-orphans
