#!/usr/bin/env python3
"""Análise complementar para o artigo do COTB 2027 (não altera results/analysis nem os números do TCC).

Capacidade (carga fechada, 100 VUs): n = 5 por cenário = results/runs/<c>-run{1..3} (19/out) + results/cotb/<c>-rep{4,5} (20/out).
Latência sem saturação (taxa fixa, 100 req/s): results/cotb/<c>-rate{1..3}, métricas do patamar.
Saídas: results/cotb/analysis/*.md|csv e figuras em computeronthebeach/artigo/figuras/.

Uso: python3 scripts/analyze_cotb.py   (requer scipy e matplotlib)
"""
import csv
import json
import math
import re
import statistics as st
from datetime import datetime
from itertools import combinations
from pathlib import Path

from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "results" / "runs"
COTB = ROOT / "results" / "cotb"
OUT = COTB / "analysis"
FIG = ROOT / "computeronthebeach" / "artigo" / "figuras"
OUT.mkdir(parents=True, exist_ok=True)

CEN = ["a", "b", "e", "c", "d"]
NOMES = {"a": "A (PHP-FPM)", "b": "B (clássico)", "e": "E (clássico, padrão)", "c": "C (CI4 Worker)", "d": "D (Octane)"}
CORES = {"a": "#8c8c8c", "b": "#4c78a8", "c": "#e07b39", "d": "#59a14f", "e": "#b07aa1"}
ENDPOINTS = ["health", "compute", "memory", "db"]
PARES = [("b", "a"), ("e", "b"), ("c", "a"), ("c", "e"), ("d", "c")]


# ---------------------------------------------------------------- leitura
def metricas(d, sufixo=""):
    """Métricas de um last-run.json; sufixo '{phase:plateau}' seleciona o patamar."""
    m = json.load(open(d / "last-run.json"))["metrics"]
    dur = m[f"http_req_duration{sufixo}"]
    r = {"p50": dur["med"], "p95": dur["p(95)"], "p99": dur["p(99)"], "avg": dur["avg"],
         "rps": m["http_reqs"]["rate"], "err": m["http_req_failed"].get("value", m["http_req_failed"].get("rate", 0)),
         "dropped": m.get("dropped_iterations", {}).get("count", 0)}
    for e in ENDPOINTS:
        k = f"endpoint_{e}_duration{sufixo}"
        r[f"{e}_avg"], r[f"{e}_p95"] = m[k]["avg"], m[k]["p(95)"]
    return r


def amostras(csv_path):
    return list(csv.DictReader(open(csv_path)))


def recurso(am, s, fim, t0_off, t1_off):
    """CPU e RAM (médias) do contêiner da aplicação em [fim-t0_off, fim-t1_off]; cenário A soma app-a + nginx-a."""
    t0, t1 = fim - t0_off, fim - t1_off
    por_ts = {}
    for r in am:
        ts = int(r["ts"])
        if not (t0 <= ts <= t1):
            continue
        if not (r["name"].startswith(f"tcc-uema-app-{s}") or (s == "a" and "nginx-a" in r["name"])):
            continue
        mem = r["mem_usage"].split("/")[0].strip()
        val = float(re.sub("[^0-9.]", "", mem)) * (1024 if "GiB" in mem else 1)
        c, m = por_ts.get(ts, (0, 0))
        por_ts[ts] = (c + float(r["cpu_pct"].rstrip("%")), m + val)
    return {"cpu": st.mean(v[0] for v in por_ts.values()), "ram": st.mean(v[1] for v in por_ts.values())}


def fim_de(d):
    return datetime.fromisoformat((d / "finished_at").read_text().strip()).timestamp()


def carregar():
    """cap[s] = lista de execuções (carga fechada, n=5); rate[s] = lista (taxa fixa, n=3)."""
    am_runs, am_cotb = amostras(RUNS / "stats-samples.csv"), amostras(COTB / "stats-samples.csv")
    cap = {s: [] for s in CEN}
    rate = {s: [] for s in CEN}
    for s in CEN:
        for d, am, bloco in [(RUNS / f"{s}-run{i}", am_runs, "19/out") for i in (1, 2, 3)] + \
                            [(COTB / f"{s}-rep{i}", am_cotb, "20/out") for i in (4, 5)]:
            r = metricas(d)
            r.update(recurso(am, s, fim_de(d), 690, 90))  # patamar de 10 min, como em scripts/analyze.py
            r["bloco"], r["dir"] = bloco, d.name
            cap[s].append(r)
        for i in (1, 2, 3):
            d = COTB / f"{s}-rate{i}"
            r = metricas(d, "{phase:plateau}")
            r.update(recurso(am_cotb, s, fim_de(d), 450, 15))  # patamar de 8 min (menos margens)
            r["dir"] = d.name
            rate[s].append(r)
    return cap, rate


# ---------------------------------------------------------------- estatística
def ic95(x):
    n = len(x)
    m = st.mean(x)
    if n < 2:
        return m, 0.0
    return m, stats.t.ppf(0.975, n - 1) * st.stdev(x) / math.sqrt(n)


def welch(xa, xb):
    """Diferença de médias (a - b), IC95% (Satterthwaite), t, p."""
    va, vb = st.variance(xa) / len(xa), st.variance(xb) / len(xb)
    se = math.sqrt(va + vb)
    gl = (va + vb) ** 2 / (va ** 2 / (len(xa) - 1) + vb ** 2 / (len(xb) - 1))
    dif = st.mean(xa) - st.mean(xb)
    h = stats.t.ppf(0.975, gl) * se
    t, p = stats.ttest_ind(xa, xb, equal_var=False)
    return dif, dif - h, dif + h, t, p, gl


def holm(ps):
    ordem = sorted(range(len(ps)), key=lambda i: ps[i])
    aj, maxv = [0.0] * len(ps), 0.0
    for k, i in enumerate(ordem):
        maxv = max(maxv, min(1.0, (len(ps) - k) * ps[i]))
        aj[i] = maxv
    return aj


def razao_ic(xa, xb):
    """Razão de médias a/b e IC95% pelo método delta na escala log."""
    ma, mb = st.mean(xa), st.mean(xb)
    var = st.variance(xa) / (len(xa) * ma ** 2) + st.variance(xb) / (len(xb) * mb ** 2)
    gl = len(xa) + len(xb) - 2
    h = stats.t.ppf(0.975, gl) * math.sqrt(var)
    r = ma / mb
    return r, r * math.exp(-h), r * math.exp(h)


def fmt_p(p):
    return "<0,001" if p < 0.001 else f"{p:.3f}".replace(".", ",")


def vir(x, n=1):
    return f"{x:.{n}f}".replace(".", ",")


# ---------------------------------------------------------------- saídas
def tabela_capacidade(cap):
    L = ["# Capacidade (carga fechada, 100 VUs, n = 5 por cenário; média ± IC95% t de Student)", "",
         "| Cenário | n | RPS | p95 (ms) | p99 (ms) | CPU (%) | RAM (MiB) | erros (%) |", "|---|---|---|---|---|---|---|---|"]
    csvw = [["cenario", "n", "rps", "rps_ic", "rps_dp", "p95", "p95_ic", "p99", "p99_ic", "cpu", "ram"]]
    for s in CEN:
        c = {k: ic95([r[k] for r in cap[s]]) for k in ("rps", "p95", "p99", "cpu", "ram")}
        dp = st.stdev([r["rps"] for r in cap[s]])
        err = max(r["err"] for r in cap[s]) * 100
        L.append(f"| {NOMES[s]} | {len(cap[s])} | {c['rps'][0]:.1f} ± {c['rps'][1]:.1f} | {c['p95'][0]:.1f} ± {c['p95'][1]:.1f} | "
                 f"{c['p99'][0]:.1f} ± {c['p99'][1]:.1f} | {c['cpu'][0]:.1f} | {c['ram'][0]:.1f} | {err:.2f} |")
        csvw.append([s, len(cap[s]), c["rps"][0], c["rps"][1], dp, c["p95"][0], c["p95"][1], c["p99"][0], c["p99"][1], c["cpu"][0], c["ram"][0]])
    (OUT / "capacidade.md").write_text("\n".join(L) + "\n")
    csv.writer(open(OUT / "capacidade.csv", "w", newline="")).writerows(csvw)


def comparacoes(cap):
    L = ["# Comparações par a par (carga fechada, n = 5): Welch, IC95% da diferença, Holm e Bonferroni, Mann–Whitney", ""]
    res = {}
    for chave, rot in (("rps", "RPS"), ("p95", "p95 (ms)"), ("p99", "p99 (ms)")):
        grupos = [[r[chave] for r in cap[s]] for s in CEN]
        f, p = stats.f_oneway(*grupos)
        L += [f"## {rot}", f"ANOVA: F = {f:.1f}, p = {p:.2e}", "",
              "| Comparação | média a | média b | variação (%) | IC95% da diferença | t (gl) | p | p Holm | p Bonferroni | p Mann–Whitney |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        linhas = []
        for a_, b_ in PARES:
            xa, xb = [r[chave] for r in cap[a_]], [r[chave] for r in cap[b_]]
            dif, lo, hi, t, p, gl = welch(xa, xb)
            mw = stats.mannwhitneyu(xa, xb, alternative="two-sided").pvalue
            linhas.append((a_, b_, xa, xb, dif, lo, hi, t, p, gl, mw))
        ps = [x[8] for x in linhas]
        aj = holm(ps)
        for (a_, b_, xa, xb, dif, lo, hi, t, p, gl, mw), ph in zip(linhas, aj):
            pct = (st.mean(xa) / st.mean(xb) - 1) * 100
            L.append(f"| {a_.upper()} vs {b_.upper()} | {st.mean(xa):.1f} | {st.mean(xb):.1f} | {pct:+.1f} | [{lo:+.1f}; {hi:+.1f}] | "
                     f"{t:.1f} ({gl:.1f}) | {p:.2e} | {ph:.2e} | {min(1, p * len(PARES)):.2e} | {mw:.4f} |")
            res[(chave, a_, b_)] = dict(pct=pct, dif=dif, lo=lo, hi=hi, p=p, holm=ph, bonf=min(1, p * len(PARES)), mw=mw)
        L.append("")
    r, lo, hi = razao_ic([x["rps"] for x in cap["c"]], [x["rps"] for x in cap["a"]])
    L += ["## Razão de vazão C/A", f"{r:.3f} (IC95% {lo:.3f}–{hi:.3f})", ""]
    (OUT / "comparacoes.md").write_text("\n".join(L) + "\n")
    return res


def bloco_temporal(cap):
    L = ["# Compatibilidade dos blocos temporais (execuções 1–3 de 19/out × 4–5 de 20/out), carga fechada", "",
         "| Cenário | RPS 19/out | RPS 20/out | diferença (%) | p95 19/out | p95 20/out | diferença (%) |", "|---|---|---|---|---|---|---|"]
    for s in CEN:
        a = [r for r in cap[s] if r["bloco"] == "19/out"]
        b = [r for r in cap[s] if r["bloco"] == "20/out"]
        ra, rb = st.mean(r["rps"] for r in a), st.mean(r["rps"] for r in b)
        pa, pb = st.mean(r["p95"] for r in a), st.mean(r["p95"] for r in b)
        L.append(f"| {NOMES[s]} | {ra:.1f} | {rb:.1f} | {(rb / ra - 1) * 100:+.1f} | {pa:.1f} | {pb:.1f} | {(pb / pa - 1) * 100:+.1f} |")
    (OUT / "blocos.md").write_text("\n".join(L) + "\n")


def tabela_taxa_fixa(rate):
    L = ["# Taxa fixa de 100 req/s (modelo aberto), patamar de 8 min, n = 3 por cenário; média ± IC95% (t, gl = 2)", "",
         "| Cenário | RPS realizado | descartadas | erros (%) | p50 (ms) | p95 (ms) | p99 (ms) | CPU (%) | RAM (MiB) |", "|---|---|---|---|---|---|---|---|---|"]
    for s in CEN:
        c = {k: ic95([r[k] for r in rate[s]]) for k in ("rps", "p50", "p95", "p99", "cpu", "ram")}
        L.append(f"| {NOMES[s]} | {c['rps'][0]:.1f} | {sum(r['dropped'] for r in rate[s]):.0f} | {max(r['err'] for r in rate[s]) * 100:.2f} | "
                 f"{c['p50'][0]:.1f} ± {c['p50'][1]:.1f} | {c['p95'][0]:.1f} ± {c['p95'][1]:.1f} | {c['p99'][0]:.1f} ± {c['p99'][1]:.1f} | "
                 f"{c['cpu'][0]:.1f} | {c['ram'][0]:.1f} |")
    L += ["", "## Por endpoint (média ± IC95%): latência média / p95 (ms)", "",
          "| Cenário | " + " | ".join(ENDPOINTS) + " |", "|---|" + "---|" * len(ENDPOINTS)]
    for s in CEN:
        cel = []
        for e in ENDPOINTS:
            a, p = ic95([r[f"{e}_avg"] for r in rate[s]]), ic95([r[f"{e}_p95"] for r in rate[s]])
            cel.append(f"{a[0]:.1f} ± {a[1]:.1f} / {p[0]:.1f} ± {p[1]:.1f}")
        L.append(f"| {NOMES[s]} | " + " | ".join(cel) + " |")
    L += ["", "## Comparações do p95 a 100 req/s (Welch, n = 3, Holm entre os 5 pares)", "",
          "| Comparação | média a | média b | variação (%) | IC95% da diferença (ms) | p | p Holm |", "|---|---|---|---|---|---|---|"]
    linhas = []
    for a_, b_ in PARES:
        xa, xb = [r["p95"] for r in rate[a_]], [r["p95"] for r in rate[b_]]
        dif, lo, hi, t, p, gl = welch(xa, xb)
        linhas.append((a_, b_, xa, xb, lo, hi, p))
    aj = holm([x[6] for x in linhas])
    for (a_, b_, xa, xb, lo, hi, p), ph in zip(linhas, aj):
        L.append(f"| {a_.upper()} vs {b_.upper()} | {st.mean(xa):.2f} | {st.mean(xb):.2f} | {(st.mean(xa) / st.mean(xb) - 1) * 100:+.1f} | "
                 f"[{lo:+.2f}; {hi:+.2f}] | {p:.2e} | {ph:.2e} |")
    (OUT / "taxa_fixa.md").write_text("\n".join(L) + "\n")


def figuras(cap, rate):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 11, "font.family": "DejaVu Sans"})
    FIG.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7, 4))
    ms_ = [ic95([r["rps"] for r in cap[s]]) for s in CEN]
    ax.bar([s.upper() for s in CEN], [m[0] for m in ms_], yerr=[m[1] for m in ms_], color=[CORES[s] for s in CEN], capsize=4)
    for i, m in enumerate(ms_):
        ax.text(i, m[0] + m[1], f"{m[0]:.0f}", ha="center", va="bottom")
    ax.set_ylabel("Requisições por segundo (média e IC95%)")
    ax.set_xlabel("Cenário")
    fig.tight_layout()
    fig.savefig(FIG / "fig_rps.png", dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.2))
    w = 0.8 / len(CEN)
    for i, s in enumerate(CEN):
        vals = [ic95([r[f"{e}_p95"] for r in rate[s]]) for e in ENDPOINTS]
        ax.bar([j + i * w for j in range(len(ENDPOINTS))], [v[0] for v in vals], w, yerr=[v[1] for v in vals],
               label=s.upper(), color=CORES[s], capsize=2)
    ax.set_xticks([j + 0.4 - w / 2 for j in range(len(ENDPOINTS))])
    ax.set_xticklabels(["/" + e for e in ENDPOINTS])
    ax.set_ylabel("Latência p95 a 100 req/s (ms)")
    ax.set_xlabel("Endpoint")
    ax.legend(title="Cenário", ncol=5, fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "fig_latencia_100rps.png", dpi=200)
    plt.close(fig)

    fig, axs = plt.subplots(1, 2, figsize=(9, 3.8))
    for ax, k, t in ((axs[0], "cpu", "CPU média (%)"), (axs[1], "ram", "RAM média (MiB)")):
        vals = [ic95([r[k] for r in cap[s]]) for s in CEN]
        ax.bar([s.upper() for s in CEN], [v[0] for v in vals], yerr=[v[1] for v in vals], color=[CORES[s] for s in CEN], capsize=4)
        ax.set_ylabel(t)
        ax.set_xlabel("Cenário")
    fig.tight_layout()
    fig.savefig(FIG / "fig_recursos.png", dpi=200)
    plt.close(fig)


def main():
    cap, rate = carregar()
    tabela_capacidade(cap)
    comparacoes(cap)
    bloco_temporal(cap)
    tabela_taxa_fixa(rate)
    figuras(cap, rate)
    print("OK:", OUT)


if __name__ == "__main__":
    main()
