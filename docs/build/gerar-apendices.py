#!/usr/bin/env python3
"""Gera docs/07-apendices.md a partir dos arquivos reais do repositório e dos resultados da coleta.

Uso: python3 docs/build/gerar-apendices.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "docs" / "07-apendices.md"
LANG = {".yml": "yaml", ".sh": "bash", ".py": "python", ".js": "javascript", ".php": "php",
        ".conf": "nginx", ".ini": "ini"}


def arquivo(rel):
    p = ROOT / rel
    lang = LANG.get(p.suffix, "")
    if p.name == "Dockerfile":
        lang = "dockerfile"
    if p.name.startswith("Caddyfile"):
        lang = ""
    return f"**{rel}**\n\n```{lang}\n{p.read_text().rstrip()}\n```\n"


def secao(titulo, intro, arquivos):
    s = [f"### APÊNDICE {titulo}\n"]
    if intro:
        s.append(intro + "\n")
    s += [arquivo(a) for a in arquivos]
    return "\n".join(s)


def resultados():
    nomes = {"a": "A", "b": "B", "c": "C", "d": "D", "e": "E"}
    linhas = ["| Execução | RPS | Latência p50 (ms) | Latência p95 (ms) | Latência p99 (ms) | Erros (%) |",
              "|---|---|---|---|---|---|"]
    ordem = [f"{s}-run{r}" for s in "abcde" for r in (1, 2, 3)]
    for nome in ordem:
        m = json.load(open(ROOT / "results" / "runs" / nome / "last-run.json"))["metrics"]
        s, r = nome.split("-run")
        d = m["http_req_duration"]
        linhas.append(f"| {nomes[s]} – execução {r} | {m['http_reqs']['rate']:.1f} | {d['med']:.1f} | "
                      f"{d['p(95)']:.1f} | {d['p(99)']:.1f} | {m['http_req_failed']['value'] * 100:.2f} |")
    t1 = "\n".join(linhas)
    linhas = ["| Teste | RPS | Latência p50 (ms) | Latência p95 (ms) | Latência p99 (ms) | Erros (%) |",
              "|---|---|---|---|---|---|"]
    for s in "cd":
        m = json.load(open(ROOT / "results" / "runs" / f"{s}-long" / "last-run.json"))["metrics"]
        d = m["http_req_duration"]
        linhas.append(f"| {nomes[s]} – teste longo (30 min) | {m['http_reqs']['rate']:.1f} | {d['med']:.1f} | "
                      f"{d['p(95)']:.1f} | {d['p(99)']:.1f} | {m['http_req_failed']['value'] * 100:.2f} |")
    t2 = "\n".join(linhas)
    return (
        "### APÊNDICE F — Resultados por execução\n\n"
        "**Tabela F1 – Resultados de cada uma das 15 execuções de 15 minutos**\n\n" + t1 + "\n\n"
        "Fonte: elaborado pelo autor (2026). Nota: estatísticas sobre toda a execução, incluindo as rampas.\n\n"
        "**Tabela F2 – Resultados dos testes longos de 30 minutos de patamar**\n\n" + t2 + "\n\n"
        "Fonte: elaborado pelo autor (2026).\n")


def ambiente():
    txt = (ROOT / "results" / "ambiente-host.txt").read_text().rstrip()
    return ("### APÊNDICE G — Ambiente de execução\n\n"
            "Saída dos comandos de inspeção do hospedeiro, registrada pelo autor antes da coleta.\n\n"
            f"```\n{txt}\n```\n")


partes = [
    "## APÊNDICES\n",
    secao("A — Orquestração dos contêineres (docker-compose.yml)", "", ["docker-compose.yml"]),
    secao("B — Imagens e configuração dos servidores",
          "O cenário E usa o mesmo `Dockerfile` do cenário B, trocando apenas o `Caddyfile` por `Caddyfile.default`.",
          ["docker/scenario-a/Dockerfile", "docker/scenario-a/php-fpm.conf", "docker/scenario-a/nginx.conf",
           "docker/scenario-a/opcache.ini", "docker/scenario-b/Dockerfile", "docker/scenario-b/Caddyfile",
           "docker/scenario-b/Caddyfile.default", "docker/scenario-c/Dockerfile", "docker/scenario-c/Caddyfile",
           "docker/scenario-d/Dockerfile"]),
    secao("C — Scripts de carga do k6", "",
          ["k6/load.js", "k6/long.js", "k6/smoke.js", "k6/lib/endpoints.js"]),
    secao("D — Scripts de automação e análise", "",
          ["scripts/run-completo.sh", "scripts/run-scenario.sh", "scripts/sample-stats.sh",
           "scripts/diagnostico-persistencia.sh", "scripts/analyze.py"]),
    secao("E — Controladores dos endpoints", "",
          ["apps/ci4-base/app/Controllers/BenchmarkController.php",
           "apps/laravel-octane/app/Http/Controllers/BenchmarkController.php"]),
    resultados(),
    ambiente(),
]
OUT.write_text("\n".join(partes))
print("OK:", OUT, OUT.read_text().count("\n"), "linhas")
