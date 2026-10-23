---
name: abnt-pdf-docx
description: Gera PDF e DOCX de trabalhos acadêmicos formatados em ABNT (capa, folha de rosto, sumário, quadros com legenda/fonte, referências, paginação correta) a partir de conteúdo em Markdown, sem depender de pandoc/LibreOffice/Word instalados — usa Chrome headless + puppeteer-core + pdf-lib para o PDF e a lib `docx` (Node) para o DOCX nativo editável. Também cobre deck de slides em PDF (pitch/apresentação) em formato paisagem. Use quando o usuário pedir para formatar/converter um trabalho, relatório, TCC, projeto de pesquisa ou apresentação em "ABNT", "normas da ABNT/da universidade", ou pedir a entrega em PDF/DOCX "pronta para postar".
---

# Formatação ABNT — PDF e DOCX a partir de Markdown

> Para a **monografia/TCC da UEMA** use a skill `tcc-uema-formatacao` (regras oficiais da UEMA, auditor de .docx e exportação para o Overleaf). Esta skill é a genérica; ela já usa recuo 1,25 cm, legenda 12 pt e fonte 10 pt conforme as Diretrizes da UEMA.

Esta skill documenta e empacota o pipeline usado para transformar relatórios acadêmicos
escritos em Markdown em PDFs e DOCXs formatados em ABNT (capa, folha de rosto, sumário,
quadros numerados com fonte, referências, paginação correta) — sem precisar de pandoc,
LibreOffice ou Word instalados no ambiente. Também cobre o caso de **slides de pitch**
(apresentação em paisagem, não é texto corrido — não usa capa/folha/paginação ABNT).

## Quando usar

- O usuário pede para "deixar em ABNT", "formatar academicamente", "gerar o PDF para
  postar no AVA", ou entrega um `.md`/rascunho e quer o arquivo final pronto.
- Também serve para gerar a versão `.docx` editável do mesmo conteúdo (útil quando o
  usuário vai continuar corrigindo/ajustando no Word, ou quando a instituição pede DOCX).
- Para slides de pitch/apresentação: mesmo pipeline de PDF, mas com template de slide
  (paisagem, sem capa/folha/sumário ABNT).

## Antes de começar: descubra as regras da instituição

**Não assuma que a NBR 14724 "genérica" é suficiente.** A maioria das universidades
brasileiras publica um manual de normalização próprio (geralmente pela biblioteca) com
detalhes específicos (ex.: caixa alta vs. baixa no subtítulo da capa, se a capa é
obrigatória para relatórios, etc.). Pesquise antes de formatar:

```
WebSearch: "<sigla ou nome da instituição>" manual normalização trabalhos acadêmicos ABNT
```

Abra o PDF resultante com a ferramenta de leitura de PDF (ela renderiza como imagem —
leia em blocos de ~10-15 páginas) e confira pelo menos: margens, fonte/tamanho,
espaçamento, modelo de capa e de folha de rosto, e regra de paginação. Um resumo já
consolidado (do manual da UEMA, mas com a maior parte válida como *default* genérico
para qualquer NBR 14724) está em `references/abnt-rules.md` — **leia esse arquivo antes
de gerar qualquer documento**, ele evita os erros mais comuns.

**Peça ao usuário, nunca invente:** nome do(a) orientador(a)/tutor(a), se a capa deve
levar matrícula (fora do padrão ABNT "puro", mas comum em cursos técnicos/tecnólogos —
siga o que já existir em documentos anteriores da mesma disciplina, se houver), e se o
subtítulo vai em caixa alta ou baixa. Se não souber, deixe um placeholder óbvio como
`[nome do(a) tutor(a)]` e avise no resumo final que precisa ser preenchido.

## Checklist de ambiente (rode uma vez por sessão/projeto)

```bash
command -v google-chrome || command -v chromium || command -v chromium-browser
command -v node && node --version
fc-list | grep -i "liberation serif"   # ou a fonte exigida pela instituição
```

- **Chrome/Chromium headless** é o motor de impressão para PDF (via `page.pdf()`).
  Se não houver `google-chrome` nem `chromium`, esta skill não funciona sem adaptação —
  avise o usuário e pergunte se pode instalar (`apt install chromium`) ou se há outra
  alternativa (pandoc+LaTeX, LibreOffice).
- **Node.js** (qualquer versão recente com suporte a ESM/`.mjs`) é necessário para os
  scripts em `assets/`.
- **Fonte serifada compatível com Times New Roman**: `Liberation Serif` está em quase
  toda distro Linux e é metricamente idêntica ao Times New Roman (mesmas larguras de
  caractere). Se a instituição exigir a fonte exata, seja explícito no CSS/DOCX.

Instale as dependências Node num diretório de scratch (nunca no projeto do usuário):

```bash
mkdir -p /tmp/abnt-build && cd /tmp/abnt-build
npm init -y
npm install puppeteer-core pdf-lib marked docx
```

## Fluxo de trabalho

1. **Leia `references/abnt-rules.md`** para relembrar as regras (margens, fonte,
   paginação, capa/folha de rosto, quadros, referências).
2. **Prepare o(s) `.md` de origem.** Estrutura esperada pelos scripts (ver exemplo
   completo nos comentários de `assets/build-pdf.mjs`):
   - Um cabeçalho livre no topo (capa "informal" em texto) até a linha `## SUMÁRIO`
     — essa parte é **ignorada** pelos scripts (a capa real é gerada a partir do
     `docs.config.mjs`, não do texto do `.md`); mantenha-a só como referência legível
     para quem abrir o `.md` puro.
   - Depois de `## SUMÁRIO`, o próximo heading `## ` marca o início do corpo real.
   - Seções primárias como `## 1 INTRODUÇÃO`, secundárias como `### 5.1 Objetivo Geral`.
   - A seção de referências deve se chamar exatamente `## REFERÊNCIAS` (maiúsculas,
     sem número) — os scripts usam essa string literal para aplicar o estilo de
     referência (alinhado à esquerda, espaço simples).
   - **Quadros/tabelas**: toda tabela Markdown deve vir precedida de uma linha
     `[QUADRO: Quadro N – Título do quadro]` e seguida de `[FONTE: Elaborado pelos
     autores (ano).]`, cada uma em sua própria linha, **com linha em branco** antes e
     depois da tabela. Ver "Armadilhas" abaixo — esse marcador tem uma pegadinha de
     regex que já foi corrigida nos scripts fornecidos, não reintroduza o bug.
3. **Copie os templates** de `assets/` para o diretório de scratch:
   `abnt.css`, `build-pdf.mjs`, `build-docx.mjs`, `docs.config.example.mjs` (renomeie
   para `docs.config.mjs`). Para slides, copie também `build-slides-example.mjs`.
4. **Adapte `docs.config.mjs`**: um objeto por documento final (capa, título, autores,
   matrícula se aplicável, natureza do trabalho, tutor, caminhos de entrada/saída).
   Reaproveite `autores`/`docente` como constantes compartilhadas entre os documentos
   da mesma equipe/disciplina.
5. **Rode os builds**:
   ```bash
   node build-pdf.mjs      # gera um .pdf por entrada de docs.config.mjs
   node build-docx.mjs     # gera o .docx correspondente (troca .pdf por .docx)
   node build-slides.mjs   # se houver deck de apresentação (adapte do exemplo)
   ```
6. **Verifique visualmente, sempre.** Leia o PDF gerado com a ferramenta de leitura de
   PDF (ela renderiza páginas como imagem) — confira pelo menos: capa, folha de rosto
   (autor, título, natureza do trabalho, tutor), sumário, 2-3 páginas do corpo com pelo
   menos um quadro/tabela, e a página de referências. Erros de conversão Markdown→PDF
   (ver "Armadilhas") aparecem como texto cru (`##`, `|---|---|`, `[QUADRO: ...]`)
   solto no meio do texto — se ver isso, **não entregue**, corrija primeiro.
7. Para o `.docx`, é suficiente validar estruturalmente (não há renderizador de DOCX
   disponível neste ambiente): abra com `python-docx` (`pip install python-docx`) e
   confira número de seções (3: capa / folha+sumário / corpo), número de tabelas, e que
   nenhum parágrafo começa com `#` ou `[` (resíduo de Markdown não parseado):
   ```python
   from docx import Document
   d = Document("arquivo.docx")
   texts = [p.text for p in d.paragraphs if p.text.strip()]
   bad = [t for t in texts if t.strip().startswith(("#", "[QUADRO", "[FONTE"))]
   print(len(d.sections), len(d.tables), bad)  # bad deve ser []
   ```

## Como a paginação ABNT é resolvida (PDF)

A regra ("contagem começa na folha de rosto, capa não conta, número só aparece a
partir do texto") não dá pra fazer só com CSS — o Chrome headless não suporta os
"page margin boxes" do CSS Paged Media (não tem `counter(page)` funcionando em
cabeçalho/rodapé impresso). A solução usada em `build-pdf.mjs`:

1. Renderiza a **capa sozinha** para um PDF temporário (não entra na contagem).
2. Renderiza **folha de rosto + sumário juntos** para outro PDF temporário — cada um
   forçado a ocupar exatamente 1 página via `page-break-after: always` no CSS (por
   isso o conteúdo da capa/folha/sumário precisa ser curto o bastante para não
   estourar uma página; se estourar, ajuste o texto ou o layout antes de prosseguir).
3. Renderiza o **corpo** (introdução → referências) para um terceiro PDF.
4. Usa `pdf-lib` para: copiar as páginas da capa (sem número), copiar as páginas de
   folha+sumário (sem número, mas contadas), e **desenhar manualmente** o número da
   página em cada página do corpo, começando em `(nº de páginas de folha+sumário) + 1`,
   no canto superior direito (a 2 cm da borda, fonte 10).
5. Concatena os três PDFs num único arquivo final.

**Erro comum a evitar**: contar a capa como página numerada faz a numeração começar
"errada" (ex.: primeira página do texto mostrando "4" em vez de "3"). A capa **nunca**
entra no cálculo de offset — só folha de rosto + sumário.

## Como a paginação ABNT é resolvida (DOCX)

O DOCX nativo usa **3 Sections** (`docx.Document({ sections: [...] })`), cada uma com
seu próprio `Header`/`Footer`:
1. Section 1 = capa, sem footer com número.
2. Section 2 = folha de rosto + sumário (um `Paragraph({ pageBreakBefore: true })`
   separa as duas), sem footer com número.
3. Section 3 = corpo, com `properties.page.pageNumberStart` setado explicitamente para
   o mesmo número calculado no PDF (nº de páginas de folha+sumário + 1) e footer com
   `PageNumber.CURRENT`.

Isso funciona porque, tal como no PDF, capa/folha/sumário são forçados a exatamente
1 página cada via quebra de página manual — não dá para confiar no Word paginar
"sozinho" e acertar o número, porque o layout final só é calculado quando o arquivo é
aberto (fontes diferentes = paginação diferente). Forçar 1 página por elemento
pré-textual é o que torna o número inicial do corpo previsível e correto.

## Armadilhas já encontradas (não repita)

1. **Regex do marcador `[QUADRO: ...]`/`[FONTE: ...]` comendo a linha em branco
   seguinte.** Um regex como `/^\[QUADRO:\s*(.+?)\]\s*$/gm` parece inofensivo, mas
   `\s` inclui `\n` — em modo multiline, `\s*$` pode consumir a quebra de linha em
   branco logo depois do marcador, colando o `<p>` gerado direto na tabela sem
   separação. Isso quebra o parser CommonMark (que exige linha em branco antes de uma
   tabela) e faz **tudo** a partir dali sair como texto cru. Use `[ \t]*$` (sem `\s`)
   para consumir só espaços/tabs no fim da linha, nunca a quebra de linha.
2. **Capa entrando na contagem de páginas numeradas** (ver seção de paginação acima) —
   sempre separar capa do cálculo de offset.
3. **Fonte "Times New Roman" pode não existir no Linux.** Use `Liberation Serif`
   (metricamente compatível) e declare fallback (`'Times New Roman', Times, serif`)
   no CSS — no DOCX, o Word/LibreOffice do usuário final vai substituir pela fonte que
   tiver instalada mesmo assim, então isso não é um problema real no `.docx`.
4. **Chrome headless não imprime headers/footers customizados via CSS puro** (não
   suporta `@page { @top-right { ... } }` do CSS Paged Media nível 3). Não perca tempo
   tentando — use a técnica de render-e-mesclar com `pdf-lib` descrita acima, ou (se
   Node com `puppeteer` completo + Chromium baixado estiver disponível) a API
   `page.pdf({ displayHeaderFooter: true, headerTemplate, footerTemplate })` do
   Puppeteer "de verdade" — mas isso não permite offset custom por seção, então a
   técnica de merge com pdf-lib continua sendo necessária de qualquer forma.
5. **`docx` (npm) não suporta Markdown** — é preciso converter manualmente. Os
   templates fornecidos já têm um parser simples (headings `##`/`###`, parágrafos com
   `**negrito**`, listas `- item`, tabelas `| a | b |`) suficiente para relatórios
   técnicos comuns; se o Markdown de origem usar recursos além disso (itálico `*x*`,
   links, citações em bloco `>`), estenda `parseBody()`/`inlineRuns()` em
   `build-docx.mjs` antes de gerar.
6. **Verifique sempre visualmente antes de entregar.** Erros de layout (tabela
   estourando a margem, capa com texto cortado, quebra de página no meio de uma lista)
   só aparecem no PDF renderizado — não são detectáveis lendo o HTML/CSS/JS fonte.

## Slides de pitch (formato diferente)

Para apresentações (pitch, defesa, seminário) o formato **não** é ABNT de texto
corrido — é paisagem, sem capa/folha de rosto/sumário/paginação por seção. Use
`assets/build-slides-example.mjs` como referência de estrutura: `@page` em paisagem
(ex.: `297mm 167mm` para 16:9), um `<div class="slide">` por slide com
`page-break-after: always`, contador de slide via CSS `counter()`. Depois que o
usuário revisar o conteúdo, pergunte se as fontes/tamanhos ficaram adequados para
projeção — texto de apresentação costuma precisar ser bem maior que texto de leitura
(bullets ~18-20pt, títulos ~26-30pt, título de capa ~44-54pt são bons pontos de
partida; ajuste depois de ver o resultado renderizado).
