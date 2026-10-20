#!/usr/bin/env python3
"""Gera cotb2027-cego.tex (avaliação) e cotb2027-final.tex (camera-ready) a partir de corpo.tex e referencias.tex.

Uso: python3 artigo/gerar.py   (depois compile cada .tex no Overleaf ou com tectonic)
"""
from pathlib import Path

AQUI = Path(__file__).resolve().parent
corpo = (AQUI / "corpo.tex").read_text()
refs = (AQUI / "referencias.tex").read_text()
decl_ia = (AQUI / "declaracao-ia.tex").read_text()

CLASSE = r"\documentclass[sigconf, nonacm, screen{anon}, language=portuguese, language=spanish, language={main=english}]{acmart}"

PREAMBULO = r"""
\AtBeginDocument{%
  \providecommand\BibTeX{{%
    \normalfont B\kern-0.5em{\scshape i\kern-0.25em b}\kern-0.8em\TeX}}}
\usepackage{amsmath}
\usepackage{amsfonts}
\let\Bbbk\relax
\usepackage{amssymb}
\usepackage{booktabs}
\usepackage{multirow}
\usepackage{graphicx}
\settopmatter{printccs=false, printacmref=false}
\renewcommand\footnotetextcopyrightpermission[1]{}

\makeatletter
\newcounter{cotbNumAuthors}
\let\cotb@originalauthor\author
\renewcommand{\author}[1]{%
  \stepcounter{cotbNumAuthors}%
  \ifnum\value{cotbNumAuthors}=1
    \gdef\cotbFirstAuthorName{#1}%
  \fi
  \cotb@originalauthor{#1}%
}
\makeatother

\newcommand{\cotbEventInfo}{XVIII Computer on the Beach (COTB 2027)\\
  Florianópolis/SC --- 13 a 17 de abril de 2027}
\newcommand{\cotbHeaderAuthors}{%
  \ifnum\value{cotbNumAuthors}>3
    \cotbFirstAuthorName\ et al.%
  \else
    \shortauthors
  \fi
}
\setlength{\headheight}{24pt}
\AtBeginDocument{%
  \fancypagestyle{firstpagestyle}{%
    \fancyhf{}%
    \renewcommand{\headrulewidth}{0.4pt}%
    \renewcommand{\footrulewidth}{0pt}%
    \fancyhead[L]{\begin{minipage}[b]{0.62\textwidth}\raggedright
      \scriptsize\cotbEventInfo\end{minipage}}%
    \fancyhead[R]{\begin{minipage}[b]{0.34\textwidth}\raggedleft
      \scriptsize\cotbHeaderAuthors\end{minipage}}%
    \fancyfoot[C]{\if@ACM@printfolios\thepage\fi}%
  }%
  \fancypagestyle{standardpagestyle}{%
    \fancyhf{}%
    \renewcommand{\headrulewidth}{0.4pt}%
    \renewcommand{\footrulewidth}{0pt}%
    \fancyhead[L]{\begin{minipage}[b]{0.62\textwidth}\raggedright
      \scriptsize\cotbEventInfo\end{minipage}}%
    \fancyhead[R]{\begin{minipage}[b]{0.34\textwidth}\raggedleft
      \scriptsize\cotbHeaderAuthors\end{minipage}}%
    \fancyfoot[C]{\if@ACM@printfolios\thepage\fi}%
  }%
  \pagestyle{standardpagestyle}%
}
"""

TITULO = r"""
\title{Persistent In-Memory Execution for CodeIgniter 4: Impact of the FrankenPHP Worker Mode Compared with PHP-FPM and Laravel Octane}
\translatedtitle{portuguese}{Execução Persistente em Memória no CodeIgniter 4: Impacto do Modo Worker do FrankenPHP frente ao PHP-FPM e ao Laravel Octane}
"""

AUTOR = r"""
\author{André Pereira Ferreira}
\affiliation{%
  \institution{Universidade Estadual do Maranhão (UEMA)}
  \streetaddress{[ENDEREÇO DO CAMPUS]}
  \city{Grajaú}
  \state{MA}
  \country{Brasil}}
\email{[E-MAIL INSTITUCIONAL]}
"""

ABSTRACT = r"""
\begin{abstract}
Persistent in-memory execution removes the per-request framework bootstrap of traditional PHP, but CodeIgniter 4 only gained native support for the FrankenPHP Worker mode in version 4.7. This paper measures, under the same resource budget (1.0 CPU, 512~MB), the capacity, latency and CPU/memory use of CodeIgniter 4 under PHP-FPM, classic FrankenPHP and FrankenPHP Worker mode, with Laravel Octane as a reference, all on the same Debian 13 base image, using k6, Prometheus and Docker. Throughput under saturation was measured in a closed-loop test (100 virtual users, five 15-minute runs per scenario, 10-minute plateau) and latency below saturation in an open-loop test at a fixed 100 requests per second (three runs). At the plateau, mean throughput was 143.6 requests per second (PHP-FPM), 155.7 (classic FrankenPHP), 304.4 (CodeIgniter 4 Worker) and 337.8 (Laravel Octane), with no errors. Worker mode raised CodeIgniter 4 throughput by 112.1\% over PHP-FPM (95.5\% over classic FrankenPHP) and cut p95 latency at 100 requests per second by 57\% (15.3 to 6.6~ms), at the cost of about 46~MiB of additional memory; memory stayed stable in 30-minute tests. The PHP-FPM comparison involves different server architectures, and the gain combines persistent execution and database connection reuse, which the experiment does not separate, although per-endpoint data suggest the connection dominates the latency reduction. Classic mode brought a modest throughput gain (8.5\%) and no latency gain. In this environment, Worker mode pays off for CodeIgniter 4, approaching Laravel Octane.
\end{abstract}
\keywords{CodeIgniter 4, FrankenPHP, Worker mode, performance benchmarking, PHP}
"""

REPO_CEGO = r"\newcommand{\repoinfo}{Os \textit{scripts} de coleta e análise e os dados brutos serão disponibilizados publicamente na versão final do trabalho.}"
REPO_FINAL = r"\newcommand{\repoinfo}{Os \textit{scripts} de coleta e análise e os dados brutos estão disponíveis em \url{https://github.com/andrepfdev/tcc-uema}.}"

AGR_CEGO = "\\section*{Agradecimentos}\nAgradecimentos omitidos para fins de avaliação cega.\n"
AGR_FINAL = "\\section*{Agradecimentos}\n[AGRADECIMENTOS: ex.: ao orientador, à UEMA, a agências de fomento, se houver.]\n"


def montar(anonima):
    partes = [CLASSE.replace("{anon}", ", anonymous" if anonima else ""), PREAMBULO,
              REPO_CEGO if anonima else REPO_FINAL, "\\begin{document}", TITULO]
    if not anonima:
        partes.append(AUTOR)
    partes += [ABSTRACT, "\\maketitle", "\\selectlanguage{portuguese}", corpo,
               AGR_CEGO if anonima else AGR_FINAL, decl_ia, refs, "\\end{document}\n"]
    return "\n".join(partes)


(AQUI / "cotb2027-cego.tex").write_text(montar(True))
(AQUI / "cotb2027-final.tex").write_text(montar(False))
print("OK: cotb2027-cego.tex, cotb2027-final.tex")
