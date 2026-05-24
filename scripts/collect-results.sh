#!/usr/bin/env bash
# ==============================================================================
# collect-results.sh — Captura snapshot de métricas dos containers
#
# Uso: ./scripts/collect-results.sh <cenário>
# Exemplo: ./scripts/collect-results.sh c
# ==============================================================================

set -euo pipefail

SCENARIO="${1:-}"

if [[ -z "$SCENARIO" || ! "$SCENARIO" =~ ^[abcd]$ ]]; then
  echo "Uso: $0 <a|b|c|d>"
  exit 1
fi

RESULTS_DIR="$(dirname "$0")/../results"
mkdir -p "$RESULTS_DIR"
OUTFILE="${RESULTS_DIR}/scenario-${SCENARIO}-stats-$(date '+%Y%m%d_%H%M%S').txt"

echo "Coletando docker stats para Cenário ${SCENARIO^^}..."
echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')" > "$OUTFILE"
echo "" >> "$OUTFILE"

docker stats --no-stream --format \
  "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}" \
  >> "$OUTFILE"

echo ""
cat "$OUTFILE"
echo ""
echo "Salvo em: $OUTFILE"
