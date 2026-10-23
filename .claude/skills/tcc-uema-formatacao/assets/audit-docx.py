#!/usr/bin/env python3
"""Audita um .docx de monografia contra as Diretrizes de Formatação (ABNT) e o Modelo – Monografia da UEMA.

Uso:  python3 -I audit-docx.py "arquivo.docx"
Saída: uma linha OK / FALHA / AVISO por regra; código de saída 1 se houver FALHA.
Depende só de python-docx (pip install python-docx) e da stdlib.
"""
import re
import sys
from docx import Document
from docx.oxml.ns import qn

CM = 567  # twips por cm
res = []  # (status, regra, detalhe)


def add(ok, regra, detalhe="", aviso=False):
    res.append(("OK" if ok else ("AVISO" if aviso else "FALHA"), regra, detalhe))


def sz(run, par=None):
    """Tamanho efetivo em pt (run -> parágrafo -> padrão do documento 12)."""
    if run.font.size:
        return run.font.size.pt
    return 12.0


def pf_line(p):
    """Entrelinhas em múltiplos de linha (None se não definido)."""
    pPr = p._p.pPr
    if pPr is None or pPr.find(qn("w:spacing")) is None:
        return None
    s = pPr.find(qn("w:spacing"))
    line = s.get(qn("w:line"))
    return int(line) / 240 if line else None


def first_line_cm(p):
    pPr = p._p.pPr
    if pPr is None or pPr.find(qn("w:ind")) is None:
        return None
    v = pPr.find(qn("w:ind")).get(qn("w:firstLine"))
    return int(v) / CM if v else None


def borders(tc):
    tcPr = tc._tc.tcPr
    b = tcPr.find(qn("w:tcBorders")) if tcPr is not None else None
    out = {}
    for side in ("top", "bottom", "left", "right"):
        el = b.find(qn("w:" + side)) if b is not None else None
        out[side] = bool(el is not None and el.get(qn("w:val")) not in (None, "nil", "none"))
    return out


def main(path):
    d = Document(path)

    # ---- página
    ok = True
    for i, s in enumerate(d.sections, 1):
        m = (round(s.top_margin.cm, 1), round(s.left_margin.cm, 1), round(s.bottom_margin.cm, 1), round(s.right_margin.cm, 1))
        if m != (3.0, 3.0, 2.0, 2.0) or round(s.page_width.cm, 1) != 21.0 or round(s.page_height.cm, 1) != 29.7:
            ok = False
            add(False, "Papel A4 e margens 3/3/2/2 cm", f"seção {i}: {m}")
    if ok:
        add(True, "Papel A4 e margens (sup/esq 3 cm; inf/dir 2 cm)")

    # ---- fonte: família e tamanhos permitidos (12 texto; 10 legendas/fontes/notas/paginação; código monoespaçado exempto)
    fams, bad_sizes = set(), {}
    for p in d.paragraphs:
        for r in p.runs:
            if not r.text.strip():
                continue
            name = r.font.name or "Times New Roman"
            if name in ("Courier New", "Liberation Mono", "Consolas"):
                continue
            fams.add(name)
            s_ = sz(r)
            if s_ not in (10.0, 12.0):
                bad_sizes.setdefault(s_, r.text[:40])
    add(fams <= {"Times New Roman", "Arial"} and len(fams) == 1, "Uma só fonte (Times New Roman ou Arial)", str(sorted(fams)))
    add(not bad_sizes, "Tamanhos de fonte só 12 (texto) e 10 (legendas/fontes/notas/paginação)", str(bad_sizes))

    # ---- parágrafos de corpo: recuo 1,25 cm e entrelinhas 1,5
    body_bad = []
    for p in d.paragraphs:
        t = p.text.strip()
        if len(t) > 120 and p.alignment is not None and p.alignment == 3 and not re.match(r"^[a-z]\)", t):  # JUSTIFY
            fl, ln = first_line_cm(p), pf_line(p)
            hang = p._p.pPr is not None and p._p.pPr.find(qn("w:ind")) is not None and p._p.pPr.find(qn("w:ind")).get(qn("w:hanging"))
            if hang or re.match(r"^[–\-•]\s", t):
                body_bad.append("subdivisão com símbolo onde cabe alínea a), b): " + t[:40]) if re.match(r"^[–\-•]\s", t) else None
                continue
            if ln == 1.5 and (fl is None or abs(fl - 1.25) > 0.05):
                body_bad.append(t[:50])
    add(not body_bad, "Recuo de parágrafo 1,25 cm no texto corrido", f"{len(body_bad)} violações: {body_bad[:2]}")

    # ---- legendas, tabelas e quadros
    caps = []  # (tipo, num, índice no corpo)
    body = d.element.body
    items = list(body.iterchildren())
    paras = {id(p._p): p for p in d.paragraphs}
    tables = {id(t._tbl): t for t in d.tables}
    seq = {"Quadro": 0, "Tabela": 0, "Figura": 0}
    cap_problems, border_problems, fonte_problems, num_problems = [], [], [], []
    for idx, el in enumerate(items):
        p = paras.get(id(el))
        if p is None:
            continue
        m = re.match(r"^(Quadro|Tabela|Figura) (\w+) – ", p.text)
        if not m or len(p.text) > 220:
            continue
        # ignora entradas das listas (têm tabulação com nº de página)
        if "\t" in p.text:
            continue
        tipo, num = m.group(1), m.group(2)
        seq[tipo] += 1
        if num != str(seq[tipo]):
            num_problems.append(f"{tipo} {num} (esperado {seq[tipo]})")
        if p.alignment not in (None, 0) or any(sz(r) != 12.0 for r in p.runs if r.text.strip()):
            cap_problems.append(f"{tipo} {num}: legenda deve ser à esquerda e 12 pt")
        # elemento seguinte: tabela/figura; depois a fonte
        nxt = items[idx + 1] if idx + 1 < len(items) else None
        if tipo in ("Quadro", "Tabela") and nxt is not None and id(nxt) in tables:
            t = tables[id(nxt)]
            cells = [c for r in t.rows for c in r.cells]
            bs = [borders(c) for c in cells]
            if tipo == "Quadro":
                if not all(all(b.values()) for b in bs):
                    border_problems.append(f"Quadro {num}: moldura deve ser fechada (todas as bordas)")
            else:
                if any(b["left"] or b["right"] for b in bs):
                    border_problems.append(f"Tabela {num}: bordas laterais devem ser abertas")
                if not all(b["top"] for b in [borders(c) for c in t.rows[0].cells]):
                    border_problems.append(f"Tabela {num}: falta traço superior")
                if not all(b["bottom"] for b in [borders(c) for c in t.rows[-1].cells]):
                    border_problems.append(f"Tabela {num}: falta traço inferior")
        else:
            nxt = None if tipo in ("Quadro", "Tabela") else nxt
        # procura a linha "Fonte:" nos próximos elementos
        found = None
        for el2 in items[idx + 1: idx + 6]:
            q = paras.get(id(el2))
            if q is not None and re.match(r"^(Fonte|FONTE):", q.text):
                found = q
                break
        if not found:
            fonte_problems.append(f"{tipo} {num}: sem linha 'Fonte:'")
        else:
            if re.search(r"https?://|www\.", found.text):
                fonte_problems.append(f"{tipo} {num}: endereço eletrônico na fonte (vai só nas Referências)")
            if any(sz(r) != 10.0 for r in found.runs if r.text.strip() and (r.font.name or "") not in ("Courier New",)):
                fonte_problems.append(f"{tipo} {num}: fonte deve ser 10 pt")
    add(not num_problems, "Numeração sequencial de Quadros/Tabelas/Figuras (algarismos arábicos)", "; ".join(num_problems))
    add(not cap_problems, "Legenda acima, à esquerda, 12 pt", "; ".join(cap_problems[:3]))
    add(not border_problems, "Bordas: Quadro fechado; Tabela (IBGE) com laterais abertas", "; ".join(border_problems[:4]))
    add(not fonte_problems, "Fonte (10 pt) abaixo de cada ilustração/quadro/tabela, sem URL", "; ".join(fonte_problems[:4]))
    add(sum(seq.values()) > 0, "Há ilustrações/quadros/tabelas identificados", str(seq), aviso=True)

    # ---- títulos
    txt = [p.text.strip() for p in d.paragraphs]
    bad_ap = [t for t in txt if re.match(r"^(APÊNDICE|ANEXO) [A-Z] ?[—-] ", t)]
    add(not bad_ap, "Apêndice/Anexo: 'APÊNDICE A – Título' (travessão)", str(bad_ap[:2]))
    bad_num = [t for t in txt if re.match(r"^\d+(\.\d+)*[.\-–—]\s", t) and len(t) < 90]
    add(not bad_num, "Seções sem ponto/hífen/travessão após o indicativo numérico", str(bad_num[:3]))

    # ---- capa/folha de rosto: título e subtítulo no mesmo parágrafo
    head = [t for t in txt[:60] if t]
    orfao = [t for t in head if t.endswith(":") and t.upper() == t and len(t) > 30]
    add(not orfao, "Título e subtítulo no mesmo parágrafo (subtítulo após ':')", str(orfao[:1]))
    add(not any("CENTRO DE CIÊNCIAS" in t for t in head[:6]), "Capa: UEMA / NÚCLEO / CURSO (modelo)", aviso=True)
    add(any(t.startswith("Monografia de graduação apresentada") for t in txt), "Folha de rosto com a natureza do trabalho do Modelo")

    # ---- placeholders (esperados até o autor preencher)
    ph = [t for t in txt if re.search(r"\[[^\]]{6,}\]|X{4,}", t)]
    add(not ph, "Sem placeholders pendentes", "; ".join(x[:60] for x in ph[:4]), aviso=True)

    # ---- resumo: 1,5 entre linhas, 150–500 palavras, 3–5 palavras-chave
    for rot, kw in (("RESUMO", "Palavras-chave:"), ("ABSTRACT", "Keywords:")):
        try:
            i = txt.index(rot)
        except ValueError:
            add(False, f"{rot} presente")
            continue
        corpo = next(p for p in d.paragraphs[i + 1:] if p.text.strip())
        n = len(corpo.text.split())
        add(150 <= n <= 500, f"{rot}: 150–500 palavras", f"{n} palavras")
        add(pf_line(corpo) == 1.5, f"{rot}: entrelinhas 1,5", str(pf_line(corpo)))
        k = next((t for t in txt[i:i + 6] if t.startswith(kw)), "")
        nk = len([x for x in k.replace(kw, "").strip(" .").split(";") if x.strip()])
        add(3 <= nk <= 5, f"{rot}: 3 a 5 palavras-chave separadas por ';'", f"{nk}")

    # ---- paginação: 10 pt, canto superior direito
    ok_pg = False
    for s in d.sections:
        h = s.header
        xml = h._element.xml
        if "PAGE" in xml:
            ok_pg = 'w:val="20"' in xml and 'w:jc w:val="right"' in xml
    add(ok_pg, "Número de página: 10 pt, canto superior direito (a partir do texto)")

    # ---- relatório
    falhas = 0
    for st, regra, det in res:
        print(f"[{st:5}] {regra}" + (f" — {det}" if det and st != "OK" else ""))
        falhas += st == "FALHA"
    print(f"\n{falhas} falha(s).")
    return 1 if falhas else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
