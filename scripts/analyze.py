#!/usr/bin/env python3
"""Agrega as rodadas em results/runs/<cenário>-run<N>/last-run.json (k6 --summary-export)
e gera tabelas (Markdown/CSV) e figuras (PNG) em results/analysis/.

Uso: python3 scripts/analyze.py   (requer matplotlib para as figuras)
"""
import csv
import re
import json
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "results" / "runs"
OUT = ROOT / "results" / "analysis"
OUT.mkdir(parents=True, exist_ok=True)

NOMES = {
    "a": "A — CI4 + PHP-FPM",
    "b": "B — CI4 + FrankenPHP clássico",
    "c": "C — CI4 + FrankenPHP Worker",
    "d": "D — Laravel Octane",
    "e": "E — CI4 + FrankenPHP clássico (threads padrão)",
}
PLATEAU_S = 600  # duração do patamar (s) nas execuções de 15 min
ENDPOINTS = ["health", "compute", "memory", "db"]
CORES = {"a": "#8c8c8c", "b": "#4c78a8", "c": "#e07b39", "d": "#59a14f", "e": "#b07aa1"}


def load():
    data = {s: [] for s in NOMES}
    for p in sorted(RUNS.glob("*-run*/last-run.json")):
        s = p.parent.name.split("-")[0]
        m = json.load(open(p))["metrics"]
        sf = "{phase:plateau}"  # patamar de 10 min (aquecimento, rampa e descida excluídos)
        dur = m[f"http_req_duration{sf}"]
        run = {
            "rps": m[f"http_reqs{sf}"]["count"] / PLATEAU_S,   # o campo `rate` da submétrica divide pela duração total
            "reqs": m[f"http_reqs{sf}"]["count"],
            "err": m[f"http_req_failed{sf}"].get("value", m[f"http_req_failed{sf}"].get("rate", 0)),
            "avg": dur["avg"],
            "p50": dur["med"],
            "p95": dur["p(95)"],
            "p99": dur.get("p(99)", float("nan")),
        }
        for e in ENDPOINTS:
            k = f"endpoint_{e}_duration{sf}"
            if k in m:
                run[f"{e}_avg"] = m[k]["avg"]
                run[f"{e}_p95"] = m[k]["p(95)"]
        data[s].append(run)
    return data


def recursos():
    """CPU/RAM por cenário a partir de results/runs/stats-samples.csv (docker stats a cada ~7 s).
    Janela do patamar sustentado de cada rodada: [fim-11,5 min, fim-1,5 min]. Cenário A soma app-a + nginx-a."""
    from datetime import datetime
    amostras = list(csv.DictReader(open(RUNS / "stats-samples.csv")))
    res = {s: [] for s in NOMES}
    for fin in sorted(RUNS.glob("*-run*/finished_at")):
        s = fin.parent.name.split("-")[0]
        if not (fin.parent / "last-run.json").exists():
            continue
        t1 = datetime.fromisoformat(fin.read_text().strip()).timestamp() - 90
        t0 = t1 - 600
        por_ts = {}
        for r in amostras:
            ts = int(r["ts"])
            if not (t0 <= ts <= t1) or not r["name"].startswith(f"tcc-uema-app-{s}") and not (s == "a" and "nginx-a" in r["name"]):
                continue
            cpu = float(r["cpu_pct"].rstrip("%"))
            mem = r["mem_usage"].split("/")[0].strip()
            val = float(re.sub("[^0-9.]", "", mem)) * (1024 if "GiB" in mem else 1)
            c, m = por_ts.get(ts, (0, 0))
            por_ts[ts] = (c + cpu, m + val)
        if por_ts:
            cs = [v[0] for v in por_ts.values()]
            ms_ = [v[1] for v in por_ts.values()]
            res[s].append({"cpu": st.mean(cs), "ram": st.mean(ms_), "ram_pico": max(ms_)})
    return res


def estatistica(data):
    """ANOVA de um fator e testes t de Welch par a par (n=3 por cenário: poder baixo, ver ressalva no texto)."""
    try:
        from scipy import stats
    except ImportError:
        print("scipy ausente: estatística não gerada")
        return
    pares = [("b", "a"), ("e", "b"), ("c", "a"), ("c", "b"), ("c", "e"), ("d", "c")]
    out = ["# Testes estatísticos (n=3 por cenário)", ""]
    for chave, rot in (("rps", "RPS"), ("p95", "Latência p95"), ("p99", "Latência p99")):
        grupos = [[r[chave] for r in data[s]] for s in data if len(data[s]) > 1]
        f, p = stats.f_oneway(*grupos)
        out += [f"## {rot}", f"ANOVA: F = {f:.1f}, p = {p:.2e}", "", "| Comparação | diferença (%) | t (Welch) | p | p ajustado (Bonferroni) |", "|---|---|---|---|---|"]
        for a_, b_ in pares:
            xa, xb = [r[chave] for r in data[a_]], [r[chave] for r in data[b_]]
            t, pv = stats.ttest_ind(xa, xb, equal_var=False)
            dif = (st.mean(xa) / st.mean(xb) - 1) * 100
            out.append(f"| {a_.upper()} vs {b_.upper()} | {dif:+.1f} | {t:.1f} | {pv:.2e} | {min(1, pv * len(pares)):.2e} |")
        out.append("")
    (OUT / "estatistica.md").write_text("\n".join(out))


def longos():
    """Teste de 30 min (c-long, d-long): RAM e CPU em janelas de 5 min do patamar, a partir de stats-samples.csv."""
    from datetime import datetime
    amostras = list(csv.DictReader(open(RUNS / "stats-samples.csv")))
    out = ["| Cenário | RPS | p95 (ms) | p99 (ms) | RAM 1ª janela (MiB) | RAM última janela (MiB) | RAM pico (MiB) |", "|---|---|---|---|---|---|---|"]
    series = {}
    for s in ("c", "d"):
        d = RUNS / f"{s}-long"
        if not (d / "last-run.json").exists():
            continue
        m = json.load(open(d / "last-run.json"))["metrics"]
        fim = datetime.fromisoformat((d / "finished_at").read_text().strip()).timestamp()
        ini = fim - 35 * 60 + 4 * 60   # início do patamar (2 min + 2 min de rampa)
        fimp = fim - 60                # fim do patamar
        pts = []
        for r in amostras:
            ts = int(r["ts"])
            if r["name"] != f"tcc-uema-app-{s}-1" or not (ini <= ts <= fimp):
                continue
            mem = r["mem_usage"].split("/")[0].strip()
            pts.append(((ts - ini) / 60, float(re.sub("[^0-9.]", "", mem)) * (1024 if "GiB" in mem else 1),
                        float(r["cpu_pct"].rstrip("%"))))
        series[s] = pts
        if not pts:
            continue
        prim = [p[1] for p in pts if p[0] <= 5]
        ult = [p[1] for p in pts if p[0] >= 25]
        sf = "{phase:plateau}"  # patamar de 30 min
        out.append(f"| {NOMES[s]} | {m[f'http_reqs{sf}']['count'] / 1800:.1f} | {m[f'http_req_duration{sf}']['p(95)']:.1f} | "
                   f"{m[f'http_req_duration{sf}']['p(99)']:.1f} | {st.mean(prim):.1f} | {st.mean(ult):.1f} | {max(p[1] for p in pts):.1f} |")
    (OUT / "tabela_longos.md").write_text("\n".join(out) + "\n")
    with open(OUT / "longos_ram.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cenario", "minuto_patamar", "ram_mib", "cpu_pct"])
        for s, pts in series.items():
            for t, ram, cpu in pts:
                w.writerow([s, f"{t:.2f}", ram, cpu])
    globals()["_SERIES"] = series


def ms(vals):
    vals = [v for v in vals if v == v]
    if not vals:
        return (float("nan"), float("nan"))
    return (st.mean(vals), st.stdev(vals) if len(vals) > 1 else 0.0)


def main():
    data = load()
    agg = {}
    for s, runs in data.items():
        if not runs:
            continue
        agg[s] = {k: ms([r[k] for r in runs if k in r]) for k in runs[0]}
        agg[s]["n"] = len(runs)

    # Tabela 1/2 (CSV + Markdown)
    linhas = ["| Cenário | n | RPS (média ± dp) | Latência p50 (ms) | p95 (ms) | p99 (ms) | Erros (%) |",
              "|---|---|---|---|---|---|---|"]
    with open(OUT / "global.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cenario", "n", "rps_media", "rps_dp", "p50", "p95", "p99", "erro_pct"])
        for s, a in agg.items():
            linhas.append(
                f"| {NOMES[s]} | {a['n']} | {a['rps'][0]:.1f} ± {a['rps'][1]:.1f} | {a['p50'][0]:.1f} | "
                f"{a['p95'][0]:.1f} | {a['p99'][0]:.1f} | {a['err'][0]*100:.2f} |")
            w.writerow([s, a["n"], a["rps"][0], a["rps"][1], a["p50"][0], a["p95"][0], a["p99"][0], a["err"][0] * 100])
    (OUT / "tabela_global.md").write_text("\n".join(linhas) + "\n")

    linhas = ["| Cenário | " + " | ".join(f"{e} avg / p95 (ms)" for e in ENDPOINTS) + " |",
              "|---|" + "---|" * len(ENDPOINTS)]
    for s, a in agg.items():
        cel = [f"{a[f'{e}_avg'][0]:.1f} / {a[f'{e}_p95'][0]:.1f}" for e in ENDPOINTS]
        linhas.append(f"| {NOMES[s]} | " + " | ".join(cel) + " |")
    (OUT / "tabela_endpoints.md").write_text("\n".join(linhas) + "\n")

    # Tabela 3: recursos
    rec = recursos()
    linhas = ["| Cenário | CPU média (%) | RAM média (MiB) | RAM pico (MiB) |", "|---|---|---|---|"]
    ragg = {}
    for s, rr in rec.items():
        if rr:
            ragg[s] = {k: ms([r[k] for r in rr]) for k in ("cpu", "ram", "ram_pico")}
            a = ragg[s]
            linhas.append(f"| {NOMES[s]} | {a['cpu'][0]:.1f} ± {a['cpu'][1]:.1f} | {a['ram'][0]:.1f} ± {a['ram'][1]:.1f} | {a['ram_pico'][0]:.1f} |")
    (OUT / "tabela_recursos.md").write_text("\n".join(linhas) + "\n")

    # Ganhos relativos de RPS
    ganhos = []
    for a_, b_ in [("b", "a"), ("e", "b"), ("c", "a"), ("c", "b"), ("c", "e"), ("d", "c"), ("d", "a")]:
        if a_ in agg and b_ in agg:
            g = (agg[a_]["rps"][0] / agg[b_]["rps"][0] - 1) * 100
            ganhos.append(f"{a_.upper()} vs {b_.upper()}: {g:+.1f}% RPS")
    (OUT / "ganhos.txt").write_text("\n".join(ganhos) + "\n")

    estatistica(data)
    longos()

    # Figuras
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib ausente: figuras não geradas")
        return
    plt.rcParams.update({"font.size": 11, "font.family": "DejaVu Sans"})

    ss = list(agg)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([NOMES[s].split(" — ")[0] for s in ss], [agg[s]["rps"][0] for s in ss],
           yerr=[agg[s]["rps"][1] for s in ss], color=[CORES[s] for s in ss], capsize=4)
    for i, s in enumerate(ss):
        ax.text(i, agg[s]["rps"][0], f"{agg[s]['rps'][0]:.0f}", ha="center", va="bottom")
    ax.set_ylabel("Requisições por segundo (média ± dp)")
    ax.set_xlabel("Cenário")
    fig.tight_layout()
    fig.savefig(OUT / "fig_rps.png", dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.2))
    w = 0.8 / len(ss)
    for i, s in enumerate(ss):
        ax.bar([j + i * w for j in range(len(ENDPOINTS))], [agg[s][f"{e}_p95"][0] for e in ENDPOINTS],
               w, label=NOMES[s].split(" — ")[0], color=CORES[s])
    ax.set_xticks([j + 0.4 - w / 2 for j in range(len(ENDPOINTS))])
    ax.set_xticklabels(ENDPOINTS)
    ax.set_ylabel("Latência p95 (ms)")
    ax.set_xlabel("Endpoint")
    ax.legend(title="Cenário")
    fig.tight_layout()
    fig.savefig(OUT / "fig_latencia_p95.png", dpi=200)
    plt.close(fig)
    if ragg:
        fig, axs = plt.subplots(1, 2, figsize=(9, 3.8))
        ks = list(ragg)
        for ax, k, t in ((axs[0], "cpu", "CPU média (%)"), (axs[1], "ram", "RAM média (MiB)")):
            ax.bar([NOMES[s].split(" — ")[0] for s in ks], [ragg[s][k][0] for s in ks],
                   yerr=[ragg[s][k][1] for s in ks], color=[CORES[s] for s in ks], capsize=4)
            ax.set_ylabel(t)
            ax.set_xlabel("Cenário")
        fig.tight_layout()
        fig.savefig(OUT / "fig_recursos.png", dpi=200)
        plt.close(fig)
    if globals().get("_SERIES"):
        fig, ax = plt.subplots(figsize=(7.5, 4))
        for s, pts in _SERIES.items():
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=CORES[s], label=NOMES[s].split(" — ")[0], lw=1.2)
        ax.set_xlabel("Tempo no patamar (min)")
        ax.set_ylabel("RAM do contêiner (MiB)")
        ax.set_ylim(bottom=0)
        ax.legend(title="Cenário")
        fig.tight_layout()
        fig.savefig(OUT / "fig_ram_longo.png", dpi=200)
        plt.close(fig)
    print("OK:", OUT)


if __name__ == "__main__":
    main()
