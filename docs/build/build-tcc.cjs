// Gera o TCC (DOCX nativo + PDF via LibreOffice) a partir dos .md em docs/.
// Uso: NODE_PATH=<dir com node_modules/docx> node docs/build/build-tcc.cjs <pasta-de-saida>
// Duas passagens: 1) gera com páginas "?" e converte para PDF; 2) lê as páginas dos títulos no PDF
// e regenera o DOCX com sumário/listas preenchidos; converte novamente para o PDF final.
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const D = require("docx");
const { Document, Packer, Paragraph, TextRun, AlignmentType, Table, TableRow, TableCell, WidthType, BorderStyle,
  ShadingType, Header, Footer, PageNumber, TabStopType, LeaderType, ImageRun } = D;

const DOCS = path.resolve(__dirname, "..");
const OUT = path.resolve(process.argv[2] || path.join(DOCS, "build/out"));
fs.mkdirSync(OUT, { recursive: true });
const NOME = "TCC UEMA - Desenvolvimento e Conclusao";

const cm = (v) => Math.round(v * 566.9291338583);
const FONT = "Times New Roman";
const S12 = 24, S10 = 20;

// ---------------- dados do trabalho ----------------
const T = {
  inst: ["UNIVERSIDADE ESTADUAL DO MARANHÃO", "CENTRO DE CIÊNCIAS TECNOLÓGICAS",
    "NÚCLEO DE TECNOLOGIAS PARA EDUCAÇÃO", "CURSO SUPERIOR DE TECNOLOGIA EM ANÁLISE E DESENVOLVIMENTO DE SISTEMAS"],
  autor: "ANDRÉ PEREIRA FERREIRA",
  titulo: "ANÁLISE COMPARATIVA DE DESEMPENHO EM AMBIENTES DE PERSISTÊNCIA EM MEMÓRIA",
  subtitulo: "o impacto da arquitetura Worker do FrankenPHP no framework CodeIgniter 4 frente ao ecossistema Laravel Octane",
  cidade: "Grajaú - MA", ano: "2026",
  orientador: "Me. Paulo Ericson Valentim Silva",
};

// ---------------- helpers de texto ----------------
function runs(text, o = {}) {
  const size = o.size || S12;
  const out = [];
  const re = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*\s][^*]*\*)/g;
  let last = 0, m;
  const push = (t, extra = {}) => t && out.push(new TextRun({ text: t, font: FONT, size, ...o, ...extra }));
  while ((m = re.exec(text))) {
    push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("`")) push(tok.slice(1, -1), { font: "Courier New", size: Math.max(size - 2, 18) });
    else if (tok.startsWith("**")) push(tok.slice(2, -2), { bold: true });
    else push(tok.slice(1, -1), { italics: true });
    last = m.index + tok.length;
  }
  push(text.slice(last));
  return out;
}
const para = (text, o = {}) => new Paragraph({
  children: runs(text, o.run || {}), alignment: o.align ?? AlignmentType.JUSTIFIED,
  indent: o.indent, spacing: { line: o.single ? 240 : 360, lineRule: "auto", before: o.before || 0, after: o.after || 0 },
  pageBreakBefore: o.pb, keepNext: o.keepNext, tabStops: o.tabStops,
});
const blank = (n = 1) => Array.from({ length: n }, () => new Paragraph({ children: [new TextRun({ text: "", font: FONT, size: S12 })] }));
const center = (text, o = {}) => para(text, { align: AlignmentType.CENTER, single: true, ...o });

// ---------------- parser Markdown ----------------
function stripComments(s) { return s.replace(/<!--[\s\S]*?-->/g, ""); }
function readMd(f) { return stripComments(fs.readFileSync(path.join(DOCS, f), "utf8")); }

function pngSize(p) {
  const b = fs.readFileSync(p);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}

// Gera blocos a partir de markdown; coleta headings e legendas para sumário/listas.
function mdToBlocks(md, ctx) {
  const lines = md.split("\n");
  const blocks = [];
  let i = 0;
  let pendingFont = null;
  const cap = (kind, text) => ctx.lists[kind].push(text);
  const splitFonte = (t) => {
    const k = t.search(/\s(Fonte|Nota):/);
    return k < 0 ? [t, null] : [t.slice(0, k).trim(), t.slice(k).trim()];
  };
  while (i < lines.length) {
    let ln = lines[i];
    if (!ln.trim()) { i++; continue; }
    // código
    if (ln.startsWith("```")) {
      const buf = []; i++;
      while (i < lines.length && !lines[i].startsWith("```")) buf.push(lines[i++]);
      i++;
      for (const c of buf) blocks.push(new Paragraph({ children: [new TextRun({ text: c || " ", font: "Courier New", size: 16 })], spacing: { line: 240 }, alignment: AlignmentType.LEFT }));
      blocks.push(...blank(1));
      continue;
    }
    // headings
    let h = ln.match(/^(#{2,4})\s+(.*)$/);
    if (h) {
      const lvl = h[1].length - 1; // 1=primária
      let text = h[2].trim().replace(/\*/g, "");
      if (text === "APÊNDICES") { i++; continue; }
      const isApend = /^APÊNDICE [A-Z]/.test(text);
      const level1 = lvl === 1 || isApend;
      const id = "h" + ctx.headings.length;
      ctx.headings.push({ id, text: level1 ? text.toUpperCase() : text, level: level1 ? 1 : lvl });
      blocks.push(new Paragraph({
        children: [new TextRun({ text: level1 ? text.toUpperCase() : text, font: FONT, size: S12, bold: lvl <= 2 || level1, italics: lvl === 4 && !level1 })],
        pageBreakBefore: level1, keepNext: true,
        spacing: { before: level1 ? 0 : 360, after: 240, line: 360 }, alignment: AlignmentType.LEFT,
        bookmark: undefined,
      }));
      i++; continue;
    }
    // imagem
    let im = ln.match(/^!\[[^\]]*\]\(([^)]+)\)\s*$/);
    if (im) {
      const p = path.join(DOCS, im[1]);
      // legenda vem na linha seguinte (não vazia)
      let j = i + 1; while (j < lines.length && !lines[j].trim()) j++;
      let capText = lines[j] || ""; i = j + 1;
      capText = capText.replace(/^\*\*(.*?)\*\*/, "$1 ").replace(/\*\*/g, "").trim();
      const [titulo, fonte] = splitFonte(capText);
      const tt = titulo.replace(/\.$/, "");
      cap("Figura", tt);
      blocks.push(para(tt, { align: AlignmentType.LEFT, single: true, before: 240, after: 120, keepNext: true }));
      const { w, h: hh } = pngSize(p);
      const W = Math.min(16, 16), Hh = (W * hh) / w;
      const maxH = 17; let width = W, height = Hh;
      if (Hh > maxH) { height = maxH; width = (maxH * w) / hh; }
      blocks.push(new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { after: 60 },
        children: [new ImageRun({ type: "png", data: fs.readFileSync(p), transformation: { width: Math.round(width * 37.795), height: Math.round(height * 37.795) } })] }));
      if (fonte) blocks.push(para(fonte, { align: AlignmentType.LEFT, single: true, run: { size: S10 }, after: 240 }));
      continue;
    }
    // legenda de tabela/quadro: **Tabela N – ...**
    let tc = ln.match(/^\*\*((Tabela|Quadro) [^*]+)\*\*\s*$/);
    if (tc) {
      const kind = tc[2]; cap(kind, tc[1]);
      blocks.push(para(tc[1], { align: AlignmentType.LEFT, single: true, before: 240, after: 120, keepNext: true }));
      i++;
      while (i < lines.length && !lines[i].trim()) i++;
      // tabela
      const rows = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) { rows.push(lines[i]); i++; }
      blocks.push(buildTable(rows, kind === "Quadro"));
      continue;
    }
    // tabela solta
    if (ln.trim().startsWith("|")) {
      const rows = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) { rows.push(lines[i]); i++; }
      blocks.push(buildTable(rows, false));
      continue;
    }
    // fonte
    if (/^(Fonte|Nota):/.test(ln)) {
      blocks.push(para(ln.trim(), { align: AlignmentType.LEFT, single: true, run: { size: S10 }, after: 240 }));
      i++; continue;
    }
    // alínea "a) ..."
    if (/^[a-z]\)\s/.test(ln)) {
      blocks.push(para(ln.trim(), { indent: { left: cm(1.25), hanging: cm(0.63) }, before: 0 }));
      i++; continue;
    }
    // lista "- "
    if (/^-\s+/.test(ln)) {
      blocks.push(para("–  " + ln.replace(/^-\s+/, "").trim(), { indent: { left: cm(1.88), hanging: cm(0.63) } }));
      i++; continue;
    }
    // parágrafo (junta linhas contínuas)
    const buf = [ln.trim()]; i++;
    while (i < lines.length && lines[i].trim() && !/^(#{2,4}\s|!\[|\||```|- |[a-z]\)\s|\*\*(Tabela|Quadro))/.test(lines[i])) buf.push(lines[i++].trim());
    blocks.push(para(buf.join(" "), { indent: { firstLine: cm(1.25) } }));
  }
  return blocks;
}

function buildTable(rows, closed) {
  const cells = rows.map((l) => l.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim()));
  const [header, , ...data] = cells;
  const n = header.length;
  const W = 9070;
  const colW = n === 2 ? [3000, 6070] : Array(n).fill(Math.floor(W / n));
  if (n >= 4) { colW[0] = 2800; for (let k = 1; k < n; k++) colW[k] = Math.floor((W - 2800) / (n - 1)); }
  if (n === 3) { colW[0] = 3200; colW[1] = 2935; colW[2] = 2935; }
  const line = { style: BorderStyle.SINGLE, size: 6, color: "000000" };
  const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  const mk = (cs, head, last) => new TableRow({ cantSplit: true, tableHeader: head, children: cs.map((c, k) => new TableCell({
    width: { size: colW[k] ?? Math.floor(W / n), type: WidthType.DXA },
    borders: closed ? { top: line, bottom: line, left: line, right: line }
      : { top: head ? line : none, bottom: head || last ? line : none, left: none, right: none },
    margins: { top: 40, bottom: 40, left: 80, right: 80 },
    children: [new Paragraph({ children: runs(c, { size: S10, bold: head }), spacing: { line: 240 }, alignment: k === 0 ? AlignmentType.LEFT : (closed ? AlignmentType.LEFT : AlignmentType.CENTER) })],
  })) });
  return new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: colW,
    rows: [mk(header, true), ...data.map((r, k) => mk(r, false, k === data.length - 1))] });
}

// ---------------- pré-textuais ----------------
function pre(ctx, pages) {
  const P = [];
  const pg = (t) => (pages && pages[t] != null ? String(pages[t]) : "?");
  // capa (seção 1)
  const capa = [];
  T.inst.forEach((t) => capa.push(center(t, { run: { bold: false } })));
  capa.push(...blank(7));
  capa.push(center(T.autor, { run: { bold: true } }));
  capa.push(...blank(6));
  capa.push(center(T.titulo + ":", { run: { bold: true } }));
  capa.push(center(T.subtitulo + ".", { before: 120 }));
  capa.push(...blank(9));
  capa.push(center(T.cidade));
  capa.push(center(T.ano));

  // folha de rosto
  const rosto = [];
  rosto.push(center(T.autor, { run: { bold: true } }));
  rosto.push(...blank(8));
  rosto.push(center(T.titulo + ":", { run: { bold: true } }));
  rosto.push(center(T.subtitulo + ".", { before: 120 }));
  rosto.push(...blank(4));
  const nat = ["Trabalho de Conclusão de Curso apresentado ao Curso Superior de Tecnologia em Análise e Desenvolvimento de Sistemas da Universidade Estadual do Maranhão para obtenção do título de Tecnólogo.", "Orientador: " + T.orientador];
  nat.forEach((t) => rosto.push(para(t, { single: true, indent: { left: cm(8) }, after: 120 })));
  rosto.push(...blank(8));
  rosto.push(center(T.cidade)); rosto.push(center(T.ano));

  // aprovação
  const aprov = [];
  aprov.push(center(T.autor, { run: { bold: true } }));
  aprov.push(...blank(2));
  aprov.push(center(T.titulo + ":", { run: { bold: true } }));
  aprov.push(center(T.subtitulo + ".", { before: 120 }));
  aprov.push(...blank(1));
  aprov.push(para("Monografia apresentada ao Curso Superior de Tecnologia em Análise e Desenvolvimento de Sistemas da Universidade Estadual do Maranhão para obtenção do título de Tecnólogo.", { single: true, indent: { left: cm(8) }, after: 240 }));
  aprov.push(para("Aprovado em: ____ / ____ / ________.", { align: AlignmentType.LEFT, single: true, after: 360 }));
  aprov.push(center("BANCA EXAMINADORA", { run: { bold: true }, after: 480 }));
  const memb = [["Prof. " + T.orientador + " (Orientador)", "Universidade Estadual do Maranhão"],
    ["[Nome e titulação do(a) examinador(a) 1]", "[Instituição]"], ["[Nome e titulação do(a) examinador(a) 2]", "[Instituição]"]];
  memb.forEach(([a, b]) => { aprov.push(center("________________________________________", { before: 360 })); aprov.push(center(a)); aprov.push(center(b)); });

  const ded = [...blank(18), para("Ao Senhor meu Deus; à minha esposa, Jéssica; e aos meus familiares, que depositam em mim uma confiança maior do que julgo merecer.", { single: true, indent: { left: cm(8) } })];
  const agr = [center("AGRADECIMENTOS", { run: { bold: true }, after: 360 }), para("[Texto de agradecimentos a ser redigido pelo autor.]", { indent: { firstLine: cm(1.25) } })];

  const resumoTxt = "Este trabalho analisa o impacto da execução persistente em memória no desempenho do framework CodeIgniter 4 (CI4). Compararam-se o PHP-FPM, o FrankenPHP em modo clássico e o FrankenPHP em modo Worker, com o Laravel Octane como referência de mercado, em contêineres Docker de mesma base (Debian 13) e com 1,0 CPU e 512 MB cada, sob carga gerada pelo k6 (100 usuários virtuais, 15 minutos) e monitoramento por Prometheus e Grafana. Em três execuções por cenário, a vazão média foi de 143 requisições por segundo (PHP-FPM), 156 (FrankenPHP clássico), 304 (CI4 em modo Worker) e 337 (Laravel Octane), medidas no patamar de 10 minutos e sem erros. O modo Worker mais que dobrou a vazão do CI4 (+112%) e reduziu à metade as latências p95 e p99, ao custo de 46 MiB adicionais de memória, enquanto o modo clássico trouxe ganho modesto (+9%). Verificou-se que o CI4 em modo Worker preserva o estado da aplicação e a conexão com o banco, como o Octane, e que a memória permaneceu estável em testes de 30 minutos. Conclui-se que o modo Worker compensa em vazão e latência para o CI4, aproximando-o do Laravel Octane.";
  const absTxt = "This work analyzes the impact of persistent in-memory execution on the performance of the CodeIgniter 4 (CI4) framework. PHP-FPM, FrankenPHP in classic mode and FrankenPHP in Worker mode were compared, with Laravel Octane as a market reference, in Docker containers sharing the same base image (Debian 13) and limited to 1.0 CPU and 512 MB each, under load generated by k6 (100 virtual users, 15 minutes) and monitored with Prometheus and Grafana. Over three runs per scenario, mean throughput at the 10-minute plateau was 143 requests per second (PHP-FPM), 156 (classic FrankenPHP), 304 (CI4 in Worker mode) and 337 (Laravel Octane), with no errors. Worker mode more than doubled CI4 throughput (+112%) and halved p95 and p99 latency, at the cost of 46 MiB of additional memory, whereas classic mode brought a modest gain (+9%). CI4 in Worker mode was found to preserve application state and the database connection, like Octane, and memory remained stable in 30-minute tests. It is concluded that Worker mode pays off in throughput and latency for CI4, bringing it close to Laravel Octane.";
  const resumo = [center("RESUMO", { run: { bold: true }, after: 360 }), para(resumoTxt, { single: true, indent: { firstLine: cm(1.25) } }),
    para("**Palavras-chave:** CodeIgniter 4; FrankenPHP; desempenho; benchmarking; PHP.", { single: true, before: 240, align: AlignmentType.LEFT })];
  const abs = [center("ABSTRACT", { run: { bold: true }, after: 360 }), para(absTxt, { single: true, indent: { firstLine: cm(1.25) } }),
    para("**Keywords:** CodeIgniter 4; FrankenPHP; performance; benchmarking; PHP.", { single: true, before: 240, align: AlignmentType.LEFT })];

  const tabs = [{ type: TabStopType.RIGHT, position: cm(16), leader: LeaderType.DOT }];
  const entry = (text, page, indentCm = 0, bold = false) => new Paragraph({
    children: [new TextRun({ text: text, font: FONT, size: S12, bold }), new TextRun({ text: "\t" + page, font: FONT, size: S12 })],
    tabStops: tabs, indent: { left: cm(indentCm), right: cm(0.8) , hanging: 0 }, spacing: { line: 276, after: 80 }, alignment: AlignmentType.LEFT,
  });
  const lista = (titulo, kind) => {
    const arr = ctx.lists[kind]; if (!arr.length) return [];
    return [new Paragraph({ children: [new TextRun({ text: titulo, font: FONT, size: S12, bold: true })], alignment: AlignmentType.CENTER, pageBreakBefore: true, spacing: { after: 360 } }),
      ...arr.map((t) => entry(t, pg("L:" + t)))];
  };
  const abrev = [new Paragraph({ children: [new TextRun({ text: "LISTA DE ABREVIATURAS E SIGLAS", font: FONT, size: S12, bold: true })], alignment: AlignmentType.CENTER, pageBreakBefore: true, spacing: { after: 360 } }),
    ...[["ANOVA", "Analysis of Variance (análise de variância)"], ["API", "Application Programming Interface"], ["CI4", "CodeIgniter 4"], ["CPU", "Central Processing Unit (unidade central de processamento)"], ["HTTP", "HyperText Transfer Protocol"],
      ["NTS", "Non-Thread-Safe"], ["PHP-FPM", "PHP FastCGI Process Manager"], ["RAM", "Random Access Memory (memória de acesso aleatório)"], ["REST", "Representational State Transfer"], ["RPS", "Requisições por segundo (requests per second)"], ["VU", "Virtual User (usuário virtual)"], ["ZTS", "Zend Thread Safety"]]
      .map(([a, b]) => new Paragraph({ children: [new TextRun({ text: a, font: FONT, size: S12, bold: true }), new TextRun({ text: "\t" + b, font: FONT, size: S12 })], tabStops: [{ type: TabStopType.LEFT, position: cm(3) }], indent: { left: cm(3), hanging: cm(3) }, spacing: { line: 276, after: 80 } }))];

  const sumario = [new Paragraph({ children: [new TextRun({ text: "SUMÁRIO", font: FONT, size: S12, bold: true })], alignment: AlignmentType.CENTER, pageBreakBefore: true, spacing: { after: 360 } }),
    ...ctx.headings.filter((h) => h.level <= 2).map((h) => entry(h.text, pg("H:" + h.text), h.level === 1 ? 0 : 0.6, h.level === 1))];

  return { capa, front: [...rosto, ...aprov.map((p, k) => k === 0 ? new Paragraph({ children: p.options?.children || [], pageBreakBefore: true }) : p)],
    rest: { rosto, aprov, ded, agr, resumo, abs, lista, abrev, sumario } };
}

// ---------------- montagem ----------------
function build(pages) {
  const ctx = { headings: [], lists: { Figura: [], Quadro: [], Tabela: [] } };
  // corpo
  const bodyMd = [readMd("01-introducao.md"), readMd("03-fundamentacao-teorica.md"), readMd("02-metodologia-revisada.md"),
    readMd("04-resultados-e-discussao.md"), readMd("05-consideracoes-finais.md"), readMd("06-referencias.md"), readMd("07-apendices.md")];
  const blocks = [];
  bodyMd.forEach((md, idx) => {
    if (idx === 5) { // referências: estilo próprio
      const lines = md.split("\n").filter((l) => l.trim());
      ctx.headings.push({ id: "ref", text: "REFERÊNCIAS", level: 1 });
      blocks.push(new Paragraph({ children: [new TextRun({ text: "REFERÊNCIAS", font: FONT, size: S12, bold: true })], pageBreakBefore: true, spacing: { after: 240 } }));
      lines.filter((l) => !l.startsWith("## ")).forEach((l) => blocks.push(new Paragraph({ children: runs(l), alignment: AlignmentType.LEFT, spacing: { line: 240, after: 240 } })));
    } else blocks.push(...mdToBlocks(md, ctx));
  });
  // tabelas do apêndice F: legenda "Tabela F1" tratada como tabela — remove da lista principal
  const pre_ = pre(ctx, pages);
  const r = pre_.rest;
  const noNum = { page: { size: { width: cm(21), height: cm(29.7) }, margin: { top: cm(3), right: cm(2), bottom: cm(2), left: cm(3) } } };
  const brk = (arr) => arr;
  // seção 2: pré-textuais contados e não numerados (começa na folha de rosto)
  const sec2 = [...r.rosto,
    ...[r.aprov, r.ded, r.agr, r.resumo, r.abs].flatMap((arr) => [new Paragraph({ children: [], pageBreakBefore: true }), ...arr]),
    ...r.lista("LISTA DE FIGURAS", "Figura"), ...r.lista("LISTA DE QUADROS", "Quadro"), ...r.lista("LISTA DE TABELAS", "Tabela"), ...r.abrev, ...r.sumario];
  const startNum = pages && pages.__start ? pages.__start : 15;
  const header = new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: S10 })] })] });
  return new Document({
    creator: "André Pereira Ferreira", title: T.titulo,
    styles: { default: { document: { run: { font: FONT, size: S12 } } } },
    sections: [
      { properties: noNum, children: pre_.capa },
      { properties: noNum, children: sec2 },
      { properties: { page: { ...noNum.page, pageNumbers: { start: startNum } } }, headers: { default: header }, children: blocks },
    ],
  }), ctx;
}

async function writeDoc(pages, file) {
  const ctxHolder = {};
  const ctx = { headings: [], lists: { Figura: [], Quadro: [], Tabela: [] } };
  // build() devolve Document; precisamos também do ctx -> reimplementa chamando função interna
  const doc = (() => { const d = build(pages); return d; })();
  return doc;
}

(async () => {
  // build() retorna o Document (vírgula acima descarta ctx); expomos ctx por closure simples:
  let lastCtx;
  const origBuild = build;
  const mk = (pages) => {
    const ctx = { headings: [], lists: { Figura: [], Quadro: [], Tabela: [] } };
    const bodyFiles = ["01-introducao.md", "03-fundamentacao-teorica.md", "02-metodologia-revisada.md", "04-resultados-e-discussao.md", "05-consideracoes-finais.md", "06-referencias.md", "07-apendices.md"];
    const blocks = [];
    bodyFiles.forEach((f, idx) => {
      const md = readMd(f);
      if (idx === 5) {
        ctx.headings.push({ text: "REFERÊNCIAS", level: 1 });
        blocks.push(new Paragraph({ children: [new TextRun({ text: "REFERÊNCIAS", font: FONT, size: S12, bold: true })], pageBreakBefore: true, spacing: { after: 240 } }));
        md.split("\n").filter((l) => l.trim() && !l.startsWith("## ")).forEach((l) => blocks.push(new Paragraph({ children: runs(l), alignment: AlignmentType.LEFT, spacing: { line: 240, after: 240 } })));
      } else blocks.push(...mdToBlocks(md, ctx));
    });
    const pre_ = pre(ctx, pages); const r = pre_.rest;
    const pageProps = { size: { width: cm(21), height: cm(29.7) }, margin: { top: cm(3), right: cm(2), bottom: cm(2), left: cm(3) } };
    const sec2 = [...r.rosto, ...[r.aprov, r.ded, r.agr, r.resumo, r.abs].flatMap((arr) => [new Paragraph({ children: [], pageBreakBefore: true }), ...arr]),
      ...r.lista("LISTA DE FIGURAS", "Figura"), ...r.lista("LISTA DE QUADROS", "Quadro"), ...r.lista("LISTA DE TABELAS", "Tabela"), ...r.abrev, ...r.sumario];
    const header = new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: S10 })] })] });
    const doc = new Document({
      creator: "André Pereira Ferreira", title: T.titulo,
      styles: { default: { document: { run: { font: FONT, size: S12 } } } },
      sections: [
        { properties: { page: pageProps }, children: pre_.capa },
        { properties: { page: pageProps }, children: sec2 },
        { properties: { page: { ...pageProps, pageNumbers: { start: (pages && pages.__start) || 15 } } }, headers: { default: header }, children: blocks },
      ],
    });
    return { doc, ctx };
  };

  const soffice = "libreoffice";
  const conv = (docx) => execFileSync(soffice, ["--headless", "--convert-to", "pdf", "--outdir", OUT, docx], { stdio: "pipe" });
  const save = async (doc, file) => fs.writeFileSync(file, await Packer.toBuffer(doc));
  const pdfText = (pdf, p) => execFileSync("pdftotext", ["-f", String(p), "-l", String(p), "-layout", pdf, "-"], { encoding: "utf8" });
  const nPages = (pdf) => Number(execFileSync("pdfinfo", [pdf], { encoding: "utf8" }).match(/Pages:\s+(\d+)/)[1]);

  const docxPath = path.join(OUT, NOME + ".docx"), pdfPath = path.join(OUT, NOME + ".pdf");
  let { doc, ctx } = mk(null);
  await save(doc, docxPath); conv(docxPath);

  // pass 2: descobrir páginas
  const total = nPages(pdfPath);
  const texts = []; for (let p = 1; p <= total; p++) texts.push(pdfText(pdfPath, p));
  // início do corpo: primeira página cujo texto tem "1 INTRODUÇÃO" sem pontilhado/numeração de sumário
  let bodyStart = texts.findIndex((t) => /^\s*1\s+INTRODUÇÃO\s*$/m.test(t)) + 1;
  const pages = { __start: bodyStart - 1 }; // páginas contadas desde a folha de rosto (capa não conta)
  const norm = (s) => s.replace(/\s+/g, " ").trim();
  const findPage = (title, from) => {
    const key = norm(title).slice(0, 24);
    for (let p = from; p <= total; p++) if (texts[p - 1].split("\n").some((l) => norm(l).toUpperCase().startsWith(key.toUpperCase()) && !/\.{3,}/.test(l))) return p;
    return null;
  };
  const disp = (p) => (p ? p - 1 : "?");
  ctx.headings.filter((h) => h.level <= 2).forEach((h) => { pages["H:" + h.text] = disp(findPage(h.text, bodyStart)); });
  ["Figura", "Quadro", "Tabela"].forEach((k) => ctx.lists[k].forEach((t) => { pages["L:" + t] = disp(findPage(t, bodyStart)); }));
  ({ doc } = mk(pages));
  await save(doc, docxPath); conv(docxPath);
  // pass 3: confere que a paginação não mudou (sumário ocupa o mesmo espaço)
  const total2 = nPages(pdfPath);
  console.log("páginas:", total, "->", total2, "| corpo começa na pág. física", bodyStart, "| numeração inicial", pages.__start);
  console.log("PDF:", pdfPath); console.log("DOCX:", docxPath);
})().catch((e) => { console.error(e); process.exit(1); });
