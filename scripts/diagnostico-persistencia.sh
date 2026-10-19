#!/usr/bin/env bash
# Diagnóstico de persistência por worker: N requisições sequenciais e concorrentes a /memory e /db.
# Uso: ./scripts/diagnostico-persistencia.sh <c|d> <workers> [N=200]  -> results/diagnostico/<cenário>-w<workers>.json
set -uo pipefail
cd "$(dirname "$0")/.."
S="$1"; W="$2"; N="${3:-200}"; OUT=results/diagnostico; mkdir -p "$OUT"
docker compose --profile scenario-a --profile scenario-b --profile scenario-c --profile scenario-d --profile scenario-e down --remove-orphans >/dev/null 2>&1
if [[ "$S" == c ]]; then FRANKENPHP_WORKERS=$W docker compose --profile scenario-c up -d >/dev/null 2>&1
else OCTANE_WORKERS=$W docker compose --profile scenario-d up -d >/dev/null 2>&1; fi
for i in $(seq 1 60); do curl -sf localhost:${BENCH_PORT:-8080}/health >/dev/null && break; sleep 1; done
curl -s localhost:${BENCH_PORT:-8080}/memory >/dev/null; curl -s localhost:${BENCH_PORT:-8080}/db >/dev/null   # aquecimento (descartado do reinício)
seqf=$(mktemp); conf=$(mktemp)
for i in $(seq 1 "$N"); do echo "$(curl -s localhost:${BENCH_PORT:-8080}/memory)"; echo "$(curl -s localhost:${BENCH_PORT:-8080}/db)"; done > "$seqf"
for i in $(seq 1 "$N"); do echo memory; echo db; done | xargs -P 16 -I{} curl -s -w '\n' localhost:${BENCH_PORT:-8080}/{} > "$conf"
python3 -I - "$seqf" "$conf" "$S" "$W" "$OUT/$S-w$W.json" <<'PY'
import sys,json,collections
sq,cf,s,w,out=sys.argv[1:6]
def parse(f):
    mem=collections.defaultdict(list); db=collections.defaultdict(set); n=0
    txt=open(f).read(); dec=json.JSONDecoder(); i=0
    while i<len(txt):
        while i<len(txt) and txt[i] in " \n": i+=1
        if i>=len(txt): break
        try: d,i=dec.raw_decode(txt,i)
        except Exception: i+=1; continue
        if not isinstance(d, dict): continue
        if 'counter' in d: mem[d['worker']].append(d['counter'])
        elif d.get('item'): db[d['worker']].add(d['item']['pg_pid'])
    return {k:{'n':len(v),'contador_min':min(v),'contador_max':max(v),'reinicios':sum(1 for a,b in zip(v,v[1:]) if b<=a)} for k,v in mem.items()}, {k:sorted(v) for k,v in db.items()}
r={}
for nome,f in (("sequencial",sq),("concorrente",cf)):
    m,d=parse(f); r[nome]={"workers_distintos_memory":len(m),"memory":m,"db_pg_pids_por_worker":d}
if not any(r[k]['memory'] for k in r): sys.exit('diagnóstico sem dados (aplicação não respondeu)')
json.dump({"cenario":s,"workers":int(w),**r},open(out,'w'),indent=1,ensure_ascii=False)
for nome in ("sequencial","concorrente"):
    x=r[nome]; print(f"{s.upper()} workers={w} {nome}: workers vistos={x['workers_distintos_memory']}; por worker:", {k:(v['n'],v['contador_max'],v['reinicios']) for k,v in x['memory'].items()}, "| pg_pids por worker:", {k:len(v) for k,v in x['db_pg_pids_por_worker'].items()})
PY
docker compose --profile scenario-c --profile scenario-d down --remove-orphans >/dev/null 2>&1
