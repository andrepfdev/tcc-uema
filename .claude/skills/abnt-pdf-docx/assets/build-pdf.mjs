import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { marked } from "marked";
import puppeteer from "puppeteer-core";
import { PDFDocument, StandardFonts, rgb } from "pdf-lib";
import { docs } from "./docs.config.mjs";

// Ajuste se o Chrome estiver em outro caminho (`which google-chrome` / `which chromium`).
const CHROME = "/usr/bin/google-chrome";
const CSS = fs.readFileSync(new URL("./abnt.css", import.meta.url), "utf8");
// Diretório de trabalho temporário para os PDFs intermediários (capa/folha/corpo
// antes de serem mesclados) — pode ficar em qualquer scratch dir, não precisa existir antes.
const OUTDIR = fs.mkdtempSync(path.join(os.tmpdir(), "abnt-pdf-build-"));

marked.use({ gfm: true, breaks: false });

function esc(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function buildFrontHtml(doc) {
  const autoresCapa = doc.autores
    .map((a) => `<p>${esc(a.nome)} – Matrícula: ${esc(a.matricula)}</p>`)
    .join("\n");

  const autoresFolha = doc.autores
    .map(
      (a) =>
        `<p>${esc(a.nome).toUpperCase()}</p><p style="font-weight:normal;text-transform:none;font-size:11pt;">Matrícula: ${esc(a.matricula)}</p>`
    )
    .join("<div style=\"height:0.8em\"></div>");

  const capa = `
  <div class="page">
    <div class="capa-top">
      ${doc.instituicao.map((l) => `<p>${esc(l)}</p>`).join("\n")}
    </div>
    <div class="capa-middle">
      <p class="titulo">${esc(doc.tituloObra)}</p>
      <p class="subtitulo">${esc(doc.subtituloTrabalho)}</p>
      <div class="capa-info">
        ${doc.capaInfo.map((l) => `<p>${esc(l)}</p>`).join("\n")}
      </div>
    </div>
    <div class="capa-info" style="margin-top:2.5em;">
      ${autoresCapa}
    </div>
    <div class="capa-bottom">
      <p>${esc(doc.cidade)}, ${esc(doc.ano)}</p>
    </div>
  </div>`;

  const folha = `
  <div class="page">
    <div class="folha-top">
      ${autoresFolha}
    </div>
    <div class="folha-middle">
      <p class="titulo">${esc(doc.tituloObra)}</p>
      <p class="subtitulo">${esc(doc.subtituloTrabalho)}</p>
      <div class="folha-natureza">
        ${doc.naturezaParagraphs.map((p) => `<p>${esc(p)}</p>`).join("\n")}
        <p class="docente">Tutor(a): ${esc(doc.docente)}.</p>
      </div>
    </div>
    <div class="folha-bottom">
      <p>${esc(doc.cidade)}</p>
      <p>${esc(doc.ano)}</p>
    </div>
  </div>`;

  return { capa, folha };
}

function buildSumarioHtml(headings) {
  const items = headings
    .map((h) => {
      if (h.level === 2) {
        return `<p class="sumario-item">${esc(h.text)}</p>`;
      }
      return `<p class="sumario-subitem">${esc(h.text)}</p>`;
    })
    .join("\n");
  return `
  <div class="page">
    <p class="sumario-titulo">SUMÁRIO</p>
    ${items}
  </div>`;
}

function extractHeadings(bodyMd) {
  const lines = bodyMd.split("\n");
  const headings = [];
  for (const line of lines) {
    const m2 = line.match(/^##\s+(.+)$/);
    const m3 = line.match(/^###\s+(.+)$/);
    if (m3) headings.push({ level: 3, text: m3[1].trim() });
    else if (m2) headings.push({ level: 2, text: m2[1].trim() });
  }
  return headings;
}

function buildBodyHtml(bodyMd) {
  // Replace quadro/fonte markers with raw HTML block lines before markdown parsing
  let md = bodyMd
    .replace(/^\[QUADRO:\s*(.+?)\][ \t]*$/gm, (_, t) => `<p class="quadro-titulo">${esc(t.trim())}</p>`)
    .replace(/^\[FONTE:\s*(.+?)\][ \t]*$/gm, (_, t) => `<p class="fonte">${esc(t.trim())}</p>`);

  let html = marked.parse(md);
  html = html.replace(/<table>/g, '<table class="quadro">');

  // Wrap the references section (from <h2>REFERÊNCIAS</h2> onward) for special styling
  const refMarker = "<h2>REFERÊNCIAS</h2>";
  const idx = html.indexOf(refMarker);
  if (idx !== -1) {
    const before = html.slice(0, idx);
    const after = html.slice(idx + refMarker.length);
    html = `${before}${refMarker}<div class="referencias">${after}</div>`;
  }

  return `<div class="corpo">${html}</div>`;
}

function wrapHtml(bodyContent) {
  return `<!doctype html><html><head><meta charset="utf-8"><style>${CSS}</style></head><body>${bodyContent}</body></html>`;
}

async function renderPdf(browser, html, outPath) {
  const page = await browser.newPage();
  await page.setContent(html, { waitUntil: "networkidle0" });
  await page.pdf({
    path: outPath,
    printBackground: true,
    preferCSSPageSize: true,
  });
  await page.close();
}

async function main() {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: "new",
    args: ["--no-sandbox", "--font-render-hinting=none"],
  });

  for (const doc of docs) {
    console.log(`\n=== ${doc.key} ===`);
    const raw = fs.readFileSync(doc.mdPath, "utf8");

    const sumarioIdx = raw.indexOf("## SUMÁRIO");
    const afterSumario = raw.slice(sumarioIdx + "## SUMÁRIO".length);
    // body starts at the next "## " heading after SUMÁRIO
    const nextHeadingMatch = afterSumario.match(/\n## /);
    const bodyMd = afterSumario.slice(nextHeadingMatch.index + 1).trim();

    const headings = extractHeadings(bodyMd);

    const { capa, folha } = buildFrontHtml(doc);
    const sumario = buildSumarioHtml(headings);
    const bodyHtml = buildBodyHtml(bodyMd);

    // Capa NÃO entra na contagem (a contagem inicia na folha de rosto).
    const capaHtml = wrapHtml(capa);
    const folhaSumarioHtml = wrapHtml(folha + sumario);
    const mainHtml = wrapHtml(`<div class="page">${bodyHtml}</div>`);

    const capaPdfPath = path.join(OUTDIR, `${doc.key}-capa.pdf`);
    const folhaSumarioPdfPath = path.join(OUTDIR, `${doc.key}-folha-sumario.pdf`);
    const mainPdfPath = path.join(OUTDIR, `${doc.key}-main.pdf`);

    await renderPdf(browser, capaHtml, capaPdfPath);
    await renderPdf(browser, folhaSumarioHtml, folhaSumarioPdfPath);
    await renderPdf(browser, mainHtml, mainPdfPath);

    const capaBytes = fs.readFileSync(capaPdfPath);
    const folhaSumarioBytes = fs.readFileSync(folhaSumarioPdfPath);
    const mainBytes = fs.readFileSync(mainPdfPath);

    const capaDoc = await PDFDocument.load(capaBytes);
    const folhaSumarioDoc = await PDFDocument.load(folhaSumarioBytes);
    const mainDoc = await PDFDocument.load(mainBytes);
    const finalDoc = await PDFDocument.create();
    const font = await finalDoc.embedFont(StandardFonts.TimesRoman);

    const capaPages = await finalDoc.copyPages(capaDoc, capaDoc.getPageIndices());
    capaPages.forEach((p) => finalDoc.addPage(p));

    const folhaSumarioPages = await finalDoc.copyPages(folhaSumarioDoc, folhaSumarioDoc.getPageIndices());
    folhaSumarioPages.forEach((p) => finalDoc.addPage(p));
    // Contagem oficial começa na folha de rosto (capa não é contada).
    const frontPageCount = folhaSumarioPages.length;

    const mainPages = await finalDoc.copyPages(mainDoc, mainDoc.getPageIndices());
    mainPages.forEach((p, i) => {
      const added = finalDoc.addPage(p);
      const pageNumber = frontPageCount + i + 1;
      const text = String(pageNumber);
      const size = 10;
      const textWidth = font.widthOfTextAtSize(text, size);
      const { width, height } = added.getSize();
      added.drawText(text, {
        x: width - (2 / 2.54) * 72 - textWidth, // 2cm from right edge (approx, cm->pt)
        y: height - (1.3 / 2.54) * 72,
        size,
        font,
        color: rgb(0, 0, 0),
      });
    });

    const finalBytes = await finalDoc.save();
    fs.writeFileSync(doc.outPath, finalBytes);
    console.log(`Gerado: ${doc.outPath} (capa + ${frontPageCount} pág. pré-textuais contadas + ${mainPages.length} pág. de texto, numeração a partir de ${frontPageCount + 1})`);
  }

  await browser.close();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
