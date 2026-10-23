import fs from "node:fs";
import {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, BorderStyle, ShadingType,
  Header, Footer, PageNumber, TabStopType, TabStopPosition,
  convertMillimetersToTwip,
} from "docx";
import { docs } from "./docs.config.mjs";

const cm = (v) => Math.round(v * 566.9291338583); // cm -> twips
const FONT = "Liberation Serif"; // Word substitui por Times New Roman se ausente; mantém compatibilidade métrica
const SIZE = 24; // 12pt (half-points)
const SIZE_SMALL = 20; // 10pt

const PAGE = {
  size: { width: cm(21), height: cm(29.7) },
  margin: { top: cm(3), right: cm(2), bottom: cm(2), left: cm(3) },
};

function run(text, opts = {}) {
  return new TextRun({ text, font: FONT, size: SIZE, ...opts });
}

// ---------- Inline markdown (bold) -> TextRun[] ----------
function inlineRuns(text, baseOpts = {}) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g).filter((s) => s !== "");
  return parts.map((p) => {
    if (p.startsWith("**") && p.endsWith("**")) {
      return run(p.slice(2, -2), { bold: true, ...baseOpts });
    }
    return run(p, baseOpts);
  });
}

function bodyParagraph(text) {
  return new Paragraph({
    children: inlineRuns(text),
    alignment: AlignmentType.JUSTIFIED,
    indent: { firstLine: cm(1.25) }, // Diretrizes UEMA: recuo de 1,25 cm
    spacing: { line: 360, lineRule: "auto" },
  });
}

function bulletParagraph(text) {
  return new Paragraph({
    children: inlineRuns(text),
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: 360, lineRule: "auto" },
    bullet: { level: 0 },
    indent: { left: cm(2.7) },
  });
}

function h2(text) {
  return new Paragraph({
    children: [run(text.toUpperCase(), { bold: true })],
    pageBreakBefore: true,
    spacing: { after: 240 },
  });
}

function h3(text) {
  return new Paragraph({
    children: [run(text, { bold: true })],
    spacing: { before: 240, after: 200 },
  });
}

function quadroTitulo(text) {
  return new Paragraph({
    children: [run(text)], // legenda: 12 pt, à esquerda, espaço simples (Diretrizes UEMA)
    alignment: AlignmentType.LEFT,
    keepNext: true,
    spacing: { before: 240, after: 120, line: 240, lineRule: "auto" },
  });
}

function fonteParagraph(text) {
  return new Paragraph({
    children: [run(text, { size: SIZE_SMALL })], // fonte: 10 pt, espaço simples, sem URL
    alignment: AlignmentType.LEFT,
    spacing: { after: 240, line: 240, lineRule: "auto" },
  });
}

function refParagraph(text) {
  return new Paragraph({
    children: inlineRuns(text),
    alignment: AlignmentType.LEFT,
    spacing: { after: 240, line: 240, lineRule: "auto" },
  });
}

const cellBorder = { style: BorderStyle.SINGLE, size: 4, color: "000000" };
const allBorders = { top: cellBorder, bottom: cellBorder, left: cellBorder, right: cellBorder };

function mdTableToDocx(lines) {
  // lines: array of raw "| a | b |" strings, including separator row
  const rows = lines
    .map((l) => l.trim())
    .filter((l) => l.startsWith("|"))
    .map((l) => l.replace(/^\||\|$/g, "").split("|").map((c) => c.trim()));
  const [header, sep, ...data] = rows;
  const colCount = header.length;
  const colWidth = Math.floor(9070 / colCount); // largura útil aproximada (twips) para 16cm

  const makeRow = (cells, isHeader) =>
    new TableRow({
      children: cells.map(
        (c) =>
          new TableCell({
            width: { size: colWidth, type: WidthType.DXA },
            shading: isHeader ? { type: ShadingType.CLEAR, fill: "E8E8E8" } : undefined,
            borders: allBorders,
            margins: { top: 60, bottom: 60, left: 100, right: 100 },
            children: [
              new Paragraph({
                children: inlineRuns(c, { size: SIZE_SMALL, bold: isHeader }),
                spacing: { line: 240, lineRule: "auto" },
              }),
            ],
          })
      ),
    });

  return new Table({
    width: { size: 9070, type: WidthType.DXA },
    rows: [makeRow(header, true), ...data.map((r) => makeRow(r, false))],
  });
}

// ---------- Parse body markdown into docx elements ----------
function parseBody(bodyMd) {
  const lines = bodyMd.split("\n");
  const elements = [];
  let inReferences = false;
  let i = 0;

  while (i < lines.length) {
    const raw = lines[i];
    const line = raw.trim();

    if (line === "") { i++; continue; }

    const m2 = line.match(/^##\s+(.+)$/);
    const m3 = line.match(/^###\s+(.+)$/);
    const mQuadro = line.match(/^\[QUADRO:\s*(.+?)\][ \t]*$/);
    const mFonte = line.match(/^\[FONTE:\s*(.+?)\][ \t]*$/);

    if (m2) {
      const text = m2[1].trim();
      elements.push(h2(text));
      if (text === "REFERÊNCIAS") inReferences = true;
      i++;
      continue;
    }
    if (m3) {
      elements.push(h3(m3[1].trim()));
      i++;
      continue;
    }
    if (mQuadro) {
      elements.push(quadroTitulo(mQuadro[1].trim()));
      i++;
      continue;
    }
    if (mFonte) {
      elements.push(fonteParagraph(mFonte[1].trim()));
      i++;
      continue;
    }
    if (line.startsWith("|")) {
      const tableLines = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        tableLines.push(lines[i]);
        i++;
      }
      elements.push(mdTableToDocx(tableLines));
      elements.push(new Paragraph({ text: "", spacing: { after: 120 } }));
      continue;
    }
    if (line.startsWith("- ")) {
      elements.push(bulletParagraph(line.slice(2)));
      i++;
      continue;
    }

    // paragraph (possibly wrapped across lines until blank line)
    const buf = [line];
    i++;
    while (i < lines.length && lines[i].trim() !== "" && !/^(##|###|\[QUADRO:|\[FONTE:|\|)/.test(lines[i].trim())) {
      buf.push(lines[i].trim());
      i++;
    }
    const text = buf.join(" ");
    elements.push(inReferences ? refParagraph(text) : bodyParagraph(text));
  }

  return elements;
}

// ---------- Capa / folha de rosto / sumário ----------
function centered(children, opts = {}) {
  return new Paragraph({ children, alignment: AlignmentType.CENTER, ...opts });
}

function buildCapa(doc) {
  const paras = [];
  doc.instituicao.forEach((l) =>
    paras.push(centered([run(l, { bold: true })], { spacing: { after: 0 } }))
  );
  for (let k = 0; k < 8; k++) paras.push(new Paragraph({ text: "" }));
  paras.push(centered([run(doc.tituloObra.toUpperCase(), { bold: true })]));
  paras.push(centered([run(doc.subtituloTrabalho)]));
  paras.push(new Paragraph({ text: "" }));
  doc.capaInfo.forEach((l) => paras.push(centered([run(l)])));
  paras.push(new Paragraph({ text: "" }));
  paras.push(new Paragraph({ text: "" }));
  doc.autores.forEach((a) =>
    paras.push(centered([run(`${a.nome} – Matrícula: ${a.matricula}`)]))
  );
  for (let k = 0; k < 10; k++) paras.push(new Paragraph({ text: "" }));
  paras.push(centered([run(`${doc.cidade}, ${doc.ano}`)]));
  return paras;
}

function buildFolha(doc) {
  const paras = [];
  doc.autores.forEach((a) => {
    paras.push(centered([run(a.nome.toUpperCase(), { bold: true })], { spacing: { after: 0 } }));
    paras.push(centered([run(`Matrícula: ${a.matricula}`, { size: 22 })], { spacing: { after: 200 } }));
  });
  for (let k = 0; k < 6; k++) paras.push(new Paragraph({ text: "" }));
  paras.push(centered([run(doc.tituloObra.toUpperCase(), { bold: true })]));
  paras.push(centered([run(doc.subtituloTrabalho)]));
  paras.push(new Paragraph({ text: "" }));

  // bloco de natureza: recuo à esquerda de 8cm, justificado, espaço simples
  doc.naturezaParagraphs.forEach((p) => {
    paras.push(
      new Paragraph({
        children: inlineRuns(p),
        alignment: AlignmentType.JUSTIFIED,
        indent: { left: cm(8) },
        spacing: { line: 240, lineRule: "auto", after: 200 },
      })
    );
  });
  paras.push(
    new Paragraph({
      children: [run(`Tutor(a): ${doc.docente}.`)],
      indent: { left: cm(8) },
      spacing: { line: 240, lineRule: "auto" },
    })
  );

  for (let k = 0; k < 10; k++) paras.push(new Paragraph({ text: "" }));
  paras.push(centered([run(doc.cidade)], { spacing: { after: 0 } }));
  paras.push(centered([run(String(doc.ano))]));
  return paras;
}

function buildSumario(headings) {
  const paras = [centered([run("SUMÁRIO", { bold: true })], { spacing: { after: 400 } })];
  headings.forEach((h) => {
    if (h.level === 2) {
      paras.push(new Paragraph({ children: [run(h.text, { bold: true })], spacing: { after: 120 } }));
    } else {
      paras.push(
        new Paragraph({
          children: [run(h.text)],
          indent: { left: cm(1.2) },
          spacing: { after: 120 },
        })
      );
    }
  });
  return paras;
}

function extractHeadings(bodyMd) {
  const headings = [];
  for (const line of bodyMd.split("\n")) {
    const m2 = line.match(/^##\s+(.+)$/);
    const m3 = line.match(/^###\s+(.+)$/);
    if (m3) headings.push({ level: 3, text: m3[1].trim() });
    else if (m2) headings.push({ level: 2, text: m2[1].trim() });
  }
  return headings;
}

function pageNumberFooter(startAt) {
  return new Footer({
    children: [
      new Paragraph({
        alignment: AlignmentType.RIGHT,
        children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: SIZE_SMALL })],
      }),
    ],
  });
}

async function buildDoc(doc) {
  const raw = fs.readFileSync(doc.mdPath, "utf8");
  const sumarioIdx = raw.indexOf("## SUMÁRIO");
  const afterSumario = raw.slice(sumarioIdx + "## SUMÁRIO".length);
  const nextHeadingMatch = afterSumario.match(/\n## /);
  const bodyMd = afterSumario.slice(nextHeadingMatch.index + 1).trim();

  const headings = extractHeadings(bodyMd);
  const bodyElements = parseBody(bodyMd);

  const emptyFooter = new Footer({ children: [new Paragraph({ text: "" })] });

  const document = new Document({
    sections: [
      {
        properties: { page: PAGE, titlePage: false },
        footers: { default: emptyFooter },
        children: buildCapa(doc),
      },
      {
        properties: { page: PAGE },
        footers: { default: emptyFooter },
        children: [...buildFolha(doc), new Paragraph({ children: [], pageBreakBefore: true }), ...buildSumario(headings)],
      },
      {
        properties: {
          page: PAGE,
          pageNumberStart: 3,
        },
        footers: { default: pageNumberFooter(3) },
        children: bodyElements,
      },
    ],
    styles: {
      default: {
        document: { run: { font: FONT, size: SIZE } },
      },
    },
  });

  const buf = await Packer.toBuffer(document);
  fs.writeFileSync(doc.outPathDocx, buf);
  console.log(`Gerado: ${doc.outPathDocx}`);
}

async function main() {
  for (const doc of docs) {
    doc.outPathDocx = doc.outPath.replace(/\.pdf$/, ".docx");
    await buildDoc(doc);
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
