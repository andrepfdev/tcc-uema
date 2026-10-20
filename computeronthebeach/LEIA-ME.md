# COTB 2027: artigo (Trilha Principal)

Evento: XVIII Computer on the Beach, Florianópolis, 13–17/04/2027. Regras em
<https://computeronthebeach.com.br/trilha-principal.html> e `.../intrucoes-gerais.html`.

**Modalidade:** artigo completo (até **6 páginas**, todas as seções e referências incluídas), em português, com
título, abstract e keywords em inglês e dois títulos. Autor: André Pereira Ferreira. O mesmo trabalho **não** pode
ir também como resumo estendido (duplicidade desclassifica); por isso não há resumo estendido.

## Datas
| Etapa | Data |
|---|---|
| Submissão (JEMS: <https://jems3.sbc.org.br/ctt-cotb2027>) | **15/11/2026** |
| Notificação | 16/02/2027 |
| Inscrição de pelo menos um autor | 26/02/2027 |
| Versão final (camera-ready) | 07/03/2027 |

## Conteúdo
- `modelos/`: templates oficiais baixados do evento (`Template_COTB2027.docx`, `template_cotb2027.tex`, classe `acmart`).
  O `.tex` original vem com entidades HTML (`&ccedil;`), que o LaTeX não compila; por isso o artigo usa acentos normais.
- `artigo/corpo.tex`: texto do artigo. `referencias.tex`, `declaracao-ia.tex`: referências e declaração de IA.
- `artigo/gerar.py`: gera `cotb2027-cego.tex` (avaliação, anônimo) e `cotb2027-final.tex` (camera-ready).
- `artigo/figuras/`: figuras (de `docs/figuras/`, geradas por `scripts/analyze.py`).

## Como gerar os PDFs (Overleaf)
1. `python3 artigo/gerar.py`.
2. No Overleaf: novo projeto, enviar `cotb2027-cego.tex`, a pasta `figuras/` (e, se o Overleaf pedir, `acmart.cls` e
   `ACM-Reference-Format.bst` do evento). Compilador pdfLaTeX; arquivo principal `cotb2027-cego.tex`.
3. Conferir **≤ 6 páginas**. Baixar o PDF e submeter no JEMS. Repetir com `cotb2027-final.tex` só após o aceite.

A prévia local (compilador antigo, sem as opções de idioma do template) deu 4 páginas; o PDF oficial deve sair
parecido, mas **confira no Overleaf**.

## Pendências do autor
- Final: endereço do campus e e-mail institucional (campos `[...]` em `gerar.py`) e agradecimentos.
- Declaração de IA (`declaracao-ia.tex`): conferir se descreve fielmente o uso do Claude Code.
- Versão cega: sem nomes, UEMA, e-mail, agradecimentos ou link do GitHub (conferido por `pdftotext`).
- A organização pede PDF gerado do template; não editar classe, margens ou fontes.
