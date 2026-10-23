---
name: tcc-uema-formatacao
description: Formata, audita e gera (DOCX, PDF e projeto LaTeX para o Overleaf) a monografia/TCC do curso da UEMA (Uemanet) conforme as "Diretrizes de Formatação (ABNT)" e o "Modelo – Monografia" fornecidos pela UEMA — margens, fonte, recuo 1,25 cm, alíneas, legendas, bordas de quadros e tabelas, capa, folha de rosto, ficha catalográfica, listas, sumário, apêndices. Use quando o usuário pedir para formatar, revisar a formatação, conferir se o TCC "está nas normas da UEMA" ou regenerar o DOCX/PDF/Overleaf do TCC deste repositório.
---

# Formatação de TCC da UEMA

Fontes de verdade (nesta ordem; se divergirem de qualquer outra skill ou da NBR genérica, **valem estas**):

1. `TRABALHO DE CONCLUSÃO DE CURSO (TCC)/Fornecidos pela UEMA/Diretrizes de Formatação (ABNT).pdf`
2. `TRABALHO DE CONCLUSÃO DE CURSO (TCC)/Fornecidos pela UEMA/Modelo – Monografia.docx`

Resumo das regras: `references/diretrizes-uema.md`. Estrutura e texto dos elementos do Modelo:
`references/modelo-monografia.md`. Leia os dois antes de mexer em qualquer coisa.

## Fluxo

1. **Auditar** o estado atual (não adivinhe, meça):
   `python3 .claude/skills/tcc-uema-formatacao/assets/audit-docx.py "<arquivo>.docx"`
   (precisa de `python-docx`; **não** use `python3 -I`, que esconde os pacotes do usuário). Cada regra sai como
   `OK`, `FALHA` ou `AVISO` (AVISO = pendência de conteúdo do autor, como placeholders).
2. **Corrigir na origem**, nunca no DOCX gerado: o conteúdo está em `docs/0*.md` e o layout em
   `docs/build/build-tcc.cjs` (lib `docx`; PDF via LibreOffice). Para o Overleaf, `docs/build/build-latex.py`.
3. **Regenerar**:
   ```bash
   mkdir -p ~/tcc-build-out   # PASTA NÃO OCULTA NO HOME: o LibreOffice (snap) não escreve em /tmp nem em ~/.cache
   NODE_PATH=<dir com node_modules/docx> node docs/build/build-tcc.cjs ~/tcc-build-out
   python3 docs/build/build-latex.py ~/tcc-build-out        # projeto Overleaf (+ .zip)
   ```
   O script faz duas passagens (descobre as páginas no PDF e preenche sumário/listas). Instale a lib `docx`
   num diretório de rascunho (`npm install docx@9`), nunca no repositório.
4. **Auditar de novo** o DOCX gerado (deve ficar sem FALHA) e **ler o PDF como imagem**: capa, rosto, ficha,
   aprovação, listas, sumário, uma página com quadro, uma com tabela, uma com figura, referências e um apêndice com código.
5. Só então copiar para `Orientação – .../` (mesmo nome do arquivo entregue). Não fazer commit sem pedido.

## Dados compartilhados e Overleaf

- Capa, rosto, aprovação, dedicatória, agradecimentos, resumo/abstract, siglas e examinadores ficam em
  `docs/build/frontmatter.json`, lido por `build-tcc.cjs` **e** `build-latex.py`. Edite lá, nunca nos dois scripts.
- O projeto Overleaf (`report` + `titlesec`/`setspace`/`fontspec`, XeLaTeX, fonte `texgyretermes` por arquivo `.otf`) sai em
  `<saída>/overleaf/` e no `.zip`. Para **compilar localmente** sem TeX instalado: baixar o binário do Tectonic para o
  diretório de rascunho (`tectonic -X compile main.tex` numa cópia da pasta `overleaf/`).
- Armadilhas de LaTeX já resolvidas: `\\` seguido de `[` vira argumento opcional (use `\\[0pt]`); `\noindent{…}` não zerou o
  recuo (use `\begingroup\setlength{\parindent}{0pt}…\par\endgroup`); `1ch` não é unidade do TeX; `babel` sobrescreve
  `\contentsname` (por isso o sumário usa `\pretitle{SUMÁRIO}` + `\@starttoc{toc}`).

## Regras que mais falham (verificadas no auditor)

- Recuo de parágrafo **1,25 cm**; entrelinhas **1,5** (resumo e abstract também); referências à esquerda, espaço simples.
- **Título e subtítulo no MESMO parágrafo**: título em negrito, `: ` e o subtítulo normal, sem quebra de linha (capa, rosto e aprovação).
- Capa só com UEMA / NÚCLEO / CURSO (sem "Centro de Ciências Tecnológicas"). Folha de rosto com o texto do Modelo
  ("Monografia de graduação apresentada ao curso de … como requisito para a obtenção do grau de …") e `Orientador: Prof. …`.
- **Verso da folha de rosto**: página **em branco, sem nenhum texto** (a biblioteca fornece a ficha antes da defesa; o autor pediu sem aviso).
- **Quadro** = moldura fechada (bordas nos 4 lados de todas as células). **Tabela** = padrão IBGE: bordas laterais
  abertas, traço no topo, sob o cabeçalho e no fim, sem linhas verticais.
- Legenda **acima**, à esquerda, `Tipo N – Título`, 12 pt, espaço simples; **Fonte** abaixo, 10 pt, **sem endereço
  eletrônico** (URL só nas Referências); produção própria = "elaborado pelo próprio autor (ano)". Numeração sequencial
  em arábicos — nunca `Tabela F1`: apêndice também segue a sequência.
- Alíneas `a)`, `b)`…: frase anterior termina em `:`, itens em minúscula terminam em `;`, o último em `.`. Símbolo
  (travessão) só para subdivisão **dentro** de alínea.
- Listas: **Lista de Ilustrações** (figuras e quadros, em ordem de aparição) e **Lista de Tabelas**.
- `APÊNDICE A – Título` (travessão `–`, não `—`), um por página; seções primárias começam em página nova.
- Número de página 10 pt, canto superior direito, contado desde a folha de rosto, impresso a partir da Introdução.
- Código nos apêndices: monoespaçado, quebrando linha **dentro** da margem direita de 2 cm.

## Armadilhas

- LibreOffice snap só escreve em pasta **visível** do home; `/tmp` e `~/.cache` falham em silêncio (PDF não sai).
- Dados numéricos em tabelas usam vírgula decimal (`143,2`), igual ao texto.
- Placeholders do autor (`[Nome e titulação do examinador]`, agradecimentos) são AVISO, não erro: avise o usuário em vez de inventar.
- A ordem de capítulos no build não é a ordem dos arquivos (`03` antes de `02`); confira `bodyFiles` antes de renomear.
