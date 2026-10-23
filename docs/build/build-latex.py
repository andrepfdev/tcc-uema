#!/usr/bin/env python3
"""Gera o projeto LaTeX do TCC para o Overleaf a partir dos mesmos docs/*.md e frontmatter.json do build-tcc.cjs.

Uso:  python3 docs/build/build-latex.py [pasta-de-saida]
Saída: <pasta>/overleaf/ (main.tex, capitulos/, figuras/, latexmkrc, LEIAME.md) e <pasta>/TCC UEMA - Overleaf.zip

Formatação conforme as Diretrizes da UEMA: A4, margens 3/3/2/2 cm, Times (TeX Gyre Termes) 12, entrelinhas 1,5,
recuo 1,25 cm, legendas 12 pt acima, fontes 10 pt abaixo, quadro com moldura fechada, tabela IBGE sem bordas laterais.
Compilar com XeLaTeX ou LuaLaTeX (o latexmkrc incluído já seleciona XeLaTeX no Overleaf).
"""
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent
OUT_ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else DOCS / "build" / "out"
PROJ = OUT_ROOT / "overleaf"
FM = json.loads((DOCS / "build" / "frontmatter.json").read_text(encoding="utf8"))
# mesma ordem do build-tcc.cjs (a fundamentação, arquivo 03, vem antes da metodologia, arquivo 02)
FILES = ["01-introducao.md", "03-fundamentacao-teorica.md", "02-metodologia-revisada.md",
         "04-resultados-e-discussao.md", "05-consideracoes-finais.md", "06-referencias.md", "07-apendices.md"]

# ---------------------------------------------------------------- escape / inline
SPECIAL = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "$": r"\$", "&": r"\&", "#": r"\#",
           "^": r"\^{}", "_": r"\_", "%": r"\%", "~": r"\textasciitilde{}"}
TOK = re.compile(r"(`[^`]+`|\*\*[^*]+\*\*|\*[^*\s][^*]*\*)")
URL = re.compile(r"https?://[^\s]+")


def esc(t):
    return "".join(SPECIAL.get(c, c) for c in t)


def quotes(t):
    return re.sub(r'"([^"]+)"', "“\\1”", t)


def plain(t):
    out, last = [], 0
    for m in URL.finditer(t):
        u, trail = m.group(0), ""
        while u and u[-1] in ".,;)":
            trail, u = u[-1] + trail, u[:-1]
        out += [quotes(esc(t[last:m.start()])), r"\url{" + u + "}", esc(trail)]
        last = m.end()
    out.append(quotes(esc(t[last:])))
    return "".join(out)


def code(t):
    return r"\texttt{" + re.sub(r"(\\_|[/.\-])", r"\1\\allowbreak{}", esc(t)) + "}"


def inline(t):
    out, last = [], 0
    for m in TOK.finditer(t):
        out.append(plain(t[last:m.start()]))
        tok = m.group(0)
        if tok.startswith("`"):
            out.append(code(tok[1:-1]))
        elif tok.startswith("**"):
            out.append(r"\textbf{" + plain(tok[2:-2]) + "}")
        else:
            out.append(r"\textit{" + plain(tok[1:-1]) + "}")
        last = m.end()
    out.append(plain(t[last:]))
    return "".join(out)


# ---------------------------------------------------------------- tabelas
def col_fracs(n):
    W = 9070  # mesmas larguras relativas do build-tcc.cjs
    if n == 2:
        w = [3000, 6070]
    elif n == 3:
        w = [3200, 2935, 2935]
    elif n >= 4:
        w = [2800] + [(W - 2800) // (n - 1)] * (n - 1)
    else:
        w = [W // n] * n
    return [x / sum(w) for x in w]


def table(rows, closed):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    header, _, *data = cells
    n = len(header)
    fr = col_fracs(n)
    sub = r"-2\tabcolsep-\arrayrulewidth" if closed else r"-2\tabcolsep"
    cols = []
    for k, f in enumerate(fr):
        w = r"p{\dimexpr %.4f\linewidth%s\relax}" % (f, sub)
        if closed or k == 0:
            w = r">{\raggedright\arraybackslash}" + w
        else:
            w = r">{\centering\arraybackslash}" + w
        cols.append(w)
    spec = ("|" + "|".join(cols) + "|") if closed else "".join(cols)
    line = lambda cs, head=False: " & ".join((r"\textbf{%s}" % inline(c)) if head else inline(c) for c in cs) + r" \\[0pt]"
    out = [r"{\footnotesize\singlespacing\renewcommand{\arraystretch}{1.15}", r"\noindent\begin{tabular}{%s}" % spec]
    if closed:
        out += [r"\hline", line(header, True), r"\hline"] + [line(r) + r" \hline" for r in data]
    else:
        out += [r"\toprule", line(header, True), r"\midrule"] + [line(r) for r in data] + [r"\bottomrule"]
    out += [r"\end{tabular}}"]
    return "\n".join(out)


# ---------------------------------------------------------------- md -> tex
class Ctx:
    def __init__(self):
        self.ilu, self.tab, self.fig_files, self.n = [], [], [], 0

    def label(self, kind, title):
        self.n += 1
        lab = f"ilu:{self.n}"
        (self.tab if kind == "Tabela" else self.ilu).append((title, lab))
        return lab


def split_fonte(t):
    m = re.search(r"\s(Fonte|Nota):", t)
    return (t, None) if not m else (t[:m.start()].strip(), t[m.start():].strip())


def fonte_tex(f):
    return r"\begingroup\setlength{\parindent}{0pt}\footnotesize\singlespacing " + inline(f) + r"\par\endgroup" if f else ""


def md_to_tex(md, ctx):
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    L = md.split("\n")
    out, i, in_ref = [], 0, False
    while i < len(L):
        ln = L[i]
        if not ln.strip():
            i += 1
            continue
        if ln.startswith("```"):  # código: Verbatim com quebra de linha dentro da margem
            buf = []
            i += 1
            while i < len(L) and not L[i].startswith("```"):
                buf.append(L[i])
                i += 1
            i += 1
            out += [r"\begingroup\singlespacing",
                    r"\begin{Verbatim}[fontsize=\scriptsize,breaklines=true,breakanywhere=true,breaksymbolleft={},breakautoindent=true,breakindent=2ex]",
                    *buf, r"\end{Verbatim}", r"\endgroup", ""]
            continue
        h = re.match(r"^(#{2,4})\s+(.*)$", ln)
        if h:
            lvl, text = len(h.group(1)) - 1, h.group(2).strip().replace("*", "")
            i += 1
            if text == "APÊNDICES":
                continue
            if lvl == 1 and text == "REFERÊNCIAS":
                out += [r"\phantomsection\chapter*{REFERÊNCIAS}\addcontentsline{toc}{chapter}{REFERÊNCIAS}",
                        r"\begingroup\singlespacing\raggedright\setlength{\parindent}{0pt}\setlength{\parskip}{12pt}"]
                in_ref = True
                continue
            if re.match(r"^APÊNDICE [A-Z]", text):
                t = esc(text.upper())
                out += [r"\phantomsection\chapter*{%s}\addcontentsline{toc}{chapter}{%s}" % (t, t)]
                continue
            title = re.sub(r"^\d+(\.\d+)*\s+", "", text)
            cmd = {1: "chapter", 2: "section", 3: "subsection"}[lvl]
            out.append("\\%s{%s}" % (cmd, inline(title)))
            continue
        im = re.match(r"^!\[[^\]]*\]\(([^)]+)\)\s*$", ln)
        if im:
            j = i + 1
            while j < len(L) and not L[j].strip():
                j += 1
            cap = re.sub(r"^\*\*(.*?)\*\*", r"\1 ", L[j] if j < len(L) else "").replace("**", "").strip()
            i = j + 1
            titulo, fonte = split_fonte(cap)
            titulo = titulo.rstrip(".")
            lab = ctx.label("Figura", titulo)
            ctx.fig_files.append(im.group(1))
            out += [r"\begin{samepage}", r"\begingroup\setlength{\parindent}{0pt}\singlespacing\label{%s}%s\par\endgroup\nopagebreak\vspace{6pt}" % (lab, inline(titulo)),
                    r"\begin{center}\includegraphics[width=\linewidth,height=0.62\textheight,keepaspectratio]{%s}\end{center}" % im.group(1),
                    fonte_tex(fonte), r"\end{samepage}", ""]
            continue
        tc = re.match(r"^\*\*((Tabela|Quadro) [^*]+)\*\*\s*$", ln)
        if tc:
            kind, titulo = tc.group(2), tc.group(1)
            lab = ctx.label(kind, titulo)
            i += 1
            while i < len(L) and not L[i].strip():
                i += 1
            rows = []
            while i < len(L) and L[i].strip().startswith("|"):
                rows.append(L[i])
                i += 1
            k = i
            while k < len(L) and not L[k].strip():
                k += 1
            fonte = None
            if k < len(L) and re.match(r"^(Fonte|Nota):", L[k]):
                fonte, i = L[k].strip(), k + 1
            out += [r"\begin{samepage}", r"\begingroup\setlength{\parindent}{0pt}\singlespacing\label{%s}%s\par\endgroup\nopagebreak\vspace{6pt}" % (lab, inline(titulo)),
                    table(rows, kind == "Quadro"), r"\par\vspace{2pt}", fonte_tex(fonte), r"\end{samepage}", ""]
            continue
        if ln.strip().startswith("|"):
            rows = []
            while i < len(L) and L[i].strip().startswith("|"):
                rows.append(L[i])
                i += 1
            out += [table(rows, False), ""]
            continue
        if re.match(r"^(Fonte|Nota):", ln):
            out += [fonte_tex(ln.strip()), ""]
            i += 1
            continue
        if re.match(r"^[a-z]\)\s", ln):  # alíneas a), b), … (terminam em ; e a última em .)
            items = []
            while i < len(L) and (re.match(r"^[a-z]\)\s", L[i]) or not L[i].strip()):
                if L[i].strip():
                    items.append(re.sub(r"^[a-z]\)\s+", "", L[i].strip()))
                i += 1
            out += [r"\begin{alineas}"] + [r"\item\relax " + inline(t) for t in items] + [r"\end{alineas}", ""]
            continue
        if re.match(r"^\*\*[^*]+\*\*\s*$", ln):
            out += [r"\noindent\textbf{%s}\par\nopagebreak\smallskip" % plain(ln.strip()[2:-2]), ""]
            i += 1
            continue
        buf = [ln.strip()]
        i += 1
        while i < len(L) and L[i].strip() and not re.match(r"^(#{2,4}\s|!\[|\||```|- |[a-z]\)\s|\*\*(Tabela|Quadro))", L[i]):
            buf.append(L[i].strip())
            i += 1
        out += [inline(" ".join(buf)), ""]
    if in_ref:
        out.append(r"\endgroup")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- pré-textuais
def front(ctx):
    F = FM
    titulo = r"{\bfseries %s: }%s." % (esc(F["titulo"]), esc(F["subtitulo"]))
    nat = lambda: (r"\noindent\hfill\begin{minipage}{\dimexpr\textwidth-8cm\relax}\singlespacing\setlength{\parindent}{0pt}"
                   + esc(F["natureza"]) + r"\par\vspace{6pt}" + (r"Orientador: Prof. %s." % esc(F["orientador"])) + r"\end{minipage}")
    nat_ap = lambda: (r"\noindent\hfill\begin{minipage}{\dimexpr\textwidth-8cm\relax}\singlespacing\setlength{\parindent}{0pt}"
                      + esc(F["natureza"]) + r"\end{minipage}")
    P = []
    # capa (página 0: não entra na contagem)
    P += [r"\pagestyle{empty}\pagenumbering{arabic}\setcounter{page}{0}", r"\begin{center}\singlespacing\setlength{\parindent}{0pt}"]
    P += [esc(t) + r"\\[0pt]" for t in F["inst"]]
    P += [r"\vspace{7\baselineskip}", r"{\bfseries %s}\\[0pt]" % esc(F["autor"]), r"\vspace{6\baselineskip}", titulo + r"\\[0pt]",
          r"\vfill", esc(F["cidade"]) + r"\\[0pt]", esc(F["ano"]), r"\end{center}"]
    # folha de rosto
    P += [r"\newpage", r"\begin{center}\singlespacing\setlength{\parindent}{0pt}", r"{\bfseries %s}\\[0pt]" % esc(F["autor"]),
          r"\vspace{8\baselineskip}", titulo, r"\end{center}", r"\vspace{4\baselineskip}", nat(), r"\vfill",
          r"\begin{center}\singlespacing %s\\[0pt] %s\end{center}" % (esc(F["cidade"]), esc(F["ano"]))]
    # verso da folha de rosto: página em branco (ficha catalográfica inserida pela biblioteca antes da defesa)
    P += [r"\newpage", r"\mbox{}"]
    # folha de aprovação
    P += [r"\newpage", r"\begin{center}\singlespacing\setlength{\parindent}{0pt}", r"{\bfseries %s}\\[0pt]" % esc(F["autor"]),
          r"\vspace{2\baselineskip}", titulo, r"\end{center}", r"\vspace{\baselineskip}", nat_ap(), r"\vspace{12pt}",
          r"\begingroup\setlength{\parindent}{0pt}\singlespacing Aprovado em: \underline{\hspace{1cm}} / \underline{\hspace{1cm}} / \underline{\hspace{2cm}}.\par\endgroup\vspace{18pt}",
          r"\begin{center}\singlespacing\bfseries BANCA EXAMINADORA\end{center}\vspace{12pt}"]
    membros = [["Prof. %s (Orientador)" % F["orientador"], "Universidade Estadual do Maranhão"]] + F["examinadores"]
    for a, b in membros:
        P += [r"\begin{center}\singlespacing\setlength{\parindent}{0pt}\rule{8.5cm}{0.4pt}\\[0pt] %s\\[0pt] %s\end{center}\vspace{10pt}" % (esc(a), esc(b))]
    # dedicatória, agradecimentos
    P += [r"\newpage", r"\null\vfill",
          r"\noindent\hfill\begin{minipage}{\dimexpr\textwidth-8cm\relax}\singlespacing\setlength{\parindent}{0pt}%s\end{minipage}" % esc(F["dedicatoria"])]
    P += [r"\newpage", r"\pretitle{AGRADECIMENTOS}", esc(F["agradecimentos"])]
    P += [r"\newpage", r"\pretitle{RESUMO}", esc(F["resumo"]), r"\par\vspace{12pt}\begingroup\setlength{\parindent}{0pt}\singlespacing\textbf{Palavras-chave:} %s\par\endgroup" % esc(F["palavrasChave"])]
    P += [r"\newpage", r"\pretitle{ABSTRACT}", esc(F["abstract"]), r"\par\vspace{12pt}\begingroup\setlength{\parindent}{0pt}\singlespacing\textbf{Keywords:} %s\par\endgroup" % esc(F["keywords"])]
    # listas
    if ctx.ilu:
        P += [r"\newpage", r"\pretitle{LISTA DE ILUSTRAÇÕES}"] + [r"\listentry{%s}{%s}" % (inline(t), lab) for t, lab in ctx.ilu]
    if ctx.tab:
        P += [r"\newpage", r"\pretitle{LISTA DE TABELAS}"] + [r"\listentry{%s}{%s}" % (inline(t), lab) for t, lab in ctx.tab]
    P += [r"\newpage", r"\pretitle{LISTA DE ABREVIATURAS E SIGLAS}",
          r"{\singlespacing\setlength{\parindent}{0pt}\noindent\begin{tabular}{@{}p{3cm}@{}p{\dimexpr\linewidth-3cm\relax}@{}}"]
    P += [r"\textbf{%s} & %s \\[4pt]" % (esc(a), esc(b)) for a, b in F["siglas"]]
    P += [r"\end{tabular}}"]
    P += [r"\newpage", r"\pretitle{SUMÁRIO}", r"\makeatletter\@starttoc{toc}\makeatother", r"\newpage", r"\fancypagestyle{plain}{\fancyhf{}\fancyhead[R]{\footnotesize\thepage}\renewcommand{\headrulewidth}{0pt}}", r"\pagestyle{fancy}"]
    return "\n".join(P) + "\n"


PREAMBLE = r"""% Gerado por docs/build/build-latex.py — não edite à mão; altere os .md / frontmatter.json e gere de novo.
% Compilador: XeLaTeX (ou LuaLaTeX). Diretrizes de Formatação da UEMA (ABNT).
\documentclass[12pt,a4paper,oneside]{report}
\usepackage{fontspec}
\setmainfont{texgyretermes}[Extension=.otf,UprightFont=*-regular,BoldFont=*-bold,ItalicFont=*-italic,BoldItalicFont=*-bolditalic]% Times New Roman não existe no Overleaf; Termes é o clone métrico do Times
\IfFontExistsTF{DejaVu Sans Mono}{\setmonofont{DejaVu Sans Mono}[Scale=MatchLowercase,Ligatures=NoCommon]}{\setmonofont{Latin Modern Mono}[Ligatures=NoCommon]}
\usepackage[brazilian]{babel}
\usepackage[a4paper,top=3cm,left=3cm,bottom=2cm,right=2cm,headheight=12pt,headsep=0.58cm,footskip=0.9cm]{geometry}
\usepackage{setspace,indentfirst,titlesec,tocloft,fancyhdr,booktabs,array,enumitem,graphicx,fvextra,xurl}
\usepackage[hidelinks]{hyperref}

\setlength{\parindent}{1.25cm}\setlength{\parskip}{0pt}
\setstretch{1.5}\emergencystretch=2em

% títulos: primária em negrito e caixa alta (o próprio texto já vem em maiúsculas), secundária em negrito, terciária negrito-itálico
\titleformat{\chapter}[hang]{\normalfont\bfseries}{\thechapter}{1em}{}
\titlespacing*{\chapter}{0pt}{0pt}{12pt}
\titleformat{\section}{\normalfont\bfseries}{\thesection}{1em}{}
\titlespacing*{\section}{0pt}{18pt}{12pt}
\titleformat{\subsection}{\normalfont\bfseries\itshape}{\thesubsection}{1em}{}
\titlespacing*{\subsection}{0pt}{12pt}{8pt}

% numeração: 10 pt, canto superior direito, a 2 cm da borda; contada desde a folha de rosto, impressa a partir da Introdução
\pagestyle{fancy}\fancyhf{}\fancyhead[R]{\footnotesize\thepage}\renewcommand{\headrulewidth}{0pt}
\fancypagestyle{plain}{\fancyhf{}\renewcommand{\headrulewidth}{0pt}}% sem número nas pré-textuais; ganha número ao entrar no texto (ver main.tex)

% sumário
\addto\captionsbrazilian{\renewcommand{\contentsname}{SUMÁRIO}}
\renewcommand{\cfttoctitlefont}{\hfill\bfseries}\renewcommand{\cftaftertoctitle}{\hfill}
\setcounter{tocdepth}{1}\cftsetrmarg{3.2em plus 1fil}
\renewcommand{\cftchapfont}{\bfseries}\renewcommand{\cftchappagefont}{\mdseries}
\renewcommand{\cftchapleader}{\cftdotfill{\cftdotsep}}
\setlength{\cftbeforechapskip}{3pt}\setlength{\cftbeforesecskip}{0pt}
\setlength{\cftchapnumwidth}{1.2em}\setlength{\cftsecindent}{1.2em}\setlength{\cftsecnumwidth}{2.2em}
\renewcommand{\cftdotsep}{1}

% alíneas a), b), … (itens terminam em ';' e o último em '.', como no texto de origem)
\newlist{alineas}{enumerate}{1}
\setlist[alineas]{label=\alph*),leftmargin=1.9cm,labelsep=0.4cm,itemsep=0pt,parsep=0pt,topsep=0pt}

% títulos das páginas pré-textuais (sem numeração, centralizados, negrito) e entradas das listas
\newcommand{\pretitle}[1]{\begin{center}\bfseries #1\end{center}\vspace{12pt}}
\newcommand{\listentry}[2]{\noindent\begin{minipage}[t]{\linewidth}\singlespacing\raggedright #1\nobreak\leaders\hbox to 0.7em{\hss.\hss}\hfill\nobreak\hbox to 2em{\hfill\pageref{#2}}\end{minipage}\par\vspace{3pt}}

\begin{document}
"""


def main():
    PROJ.mkdir(parents=True, exist_ok=True)
    cap_dir, fig_dir = PROJ / "capitulos", PROJ / "figuras"
    cap_dir.mkdir(exist_ok=True)
    fig_dir.mkdir(exist_ok=True)
    ctx, bodies = Ctx(), []
    for f in FILES:
        md = (DOCS / f).read_text(encoding="utf8")
        name = Path(f).stem + ".tex"
        (cap_dir / name).write_text(md_to_tex(md, ctx), encoding="utf8")
        bodies.append(name)
    for fig in sorted(set(ctx.fig_files)):
        shutil.copy(DOCS / fig, fig_dir / Path(fig).name)
    main_tex = PREAMBLE + front(ctx) + "\n".join(r"\input{capitulos/%s}" % n[:-4] for n in bodies) + "\n\\end{document}\n"
    main_tex = main_tex.replace("{figuras/", "{figuras/")
    (PROJ / "main.tex").write_text(main_tex, encoding="utf8")
    (PROJ / "latexmkrc").write_text("# Overleaf: compila com XeLaTeX\n$pdf_mode = 5;\n$dvi_mode = 0;\n$postscript_mode = 0;\n", encoding="utf8")
    (PROJ / "LEIAME.md").write_text(
        "# TCC UEMA — projeto Overleaf\n\n"
        "1. No Overleaf: **New Project → Upload Project** e envie o `.zip`.\n"
        "2. **Menu → Compiler: XeLaTeX** (o `latexmkrc` já pede XeLaTeX; LuaLaTeX também serve). Documento principal: `main.tex`.\n"
        "3. Compile **duas vezes** (sumário, listas e referências cruzadas de página).\n\n"
        "Fonte do texto: `TeX Gyre Termes` (equivalente ao Times New Roman). Placeholders pendentes: "
        "agradecimentos e examinadores 1 e 2 (`docs/build/frontmatter.json`).\n"
        "Arquivo gerado por `docs/build/build-latex.py` — edite os `.md`/`frontmatter.json` e gere de novo.\n", encoding="utf8")
    zpath = OUT_ROOT / "TCC UEMA - Overleaf.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(PROJ.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(PROJ).as_posix())
    print("Overleaf:", PROJ)
    print("ZIP:", zpath, f"| {len(ctx.ilu)} ilustrações, {len(ctx.tab)} tabelas, {len(set(ctx.fig_files))} figuras")


if __name__ == "__main__":
    main()
