#!/usr/bin/env bash
# sample-stats.sh — amostra docker stats (ts,container,cpu%,mem) a cada ~5 s até o arquivo-sinalizador sumir.
# Uso: sample-stats.sh <saida.csv> <arquivo-sinalizador>
OUT="${1:-results/runs/stats-samples.csv}"; FLAG="${2:-/tmp/sampling.flag}"
echo "ts,name,cpu_pct,mem_usage" > "$OUT"
while [[ -f "$FLAG" ]]; do
  ts=$(date +%s)
  docker stats --no-stream --format '{{.Name}},{{.CPUPerc}},{{.MemUsage}}' 2>/dev/null | grep -E 'app-[a-f]|nginx-a' | sed "s/^/$ts,/" >> "$OUT"
  sleep 3
done
