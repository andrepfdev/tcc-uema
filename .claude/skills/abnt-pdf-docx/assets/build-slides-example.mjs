// EXEMPLO CONCRETO de deck de slides (não um template genérico) — mostra a estrutura
// a copiar/adaptar: @page paisagem, um <div class="slide"> por slide, contador de
// slide via CSS counter, sem capa/folha/sumário/paginação ABNT (isso é pitch, não texto
// corrido). Troque o conteúdo dos slides e o caminho de saída (OUT) para o seu caso.
import fs from "node:fs";
import puppeteer from "puppeteer-core";

const CHROME = "/usr/bin/google-chrome";
const OUT = "/caminho/absoluto/para/Nota X – Nome da Apresentação.pdf";

const CSS = `
@page { size: 297mm 167mm; margin: 0; }
* { box-sizing: border-box; }
html,body { margin:0; padding:0; }
body {
  font-family: 'Liberation Sans', Arial, sans-serif;
  color: #1a1a1a;
  counter-reset: slide;
}
.slide {
  width: 297mm;
  height: 167mm;
  page-break-after: always;
  position: relative;
  padding: 14mm 16mm;
  display: flex;
  flex-direction: column;
  background: #ffffff;
}
.slide:last-of-type { page-break-after: auto; }
.slide::after {
  counter-increment: slide;
  content: counter(slide) " / 10";
  position: absolute;
  bottom: 8mm;
  right: 14mm;
  font-size: 12pt;
  color: #888;
}
.kicker {
  font-size: 15pt;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #1f5fa8;
  text-transform: uppercase;
  margin: 0 0 5mm 0;
}
h1 {
  font-size: 36pt;
  margin: 0 0 9mm 0;
  color: #10233f;
  line-height: 1.15;
}
h2.slide-title {
  font-size: 28pt;
  margin: 0 0 9mm 0;
  color: #10233f;
  border-bottom: 2pt solid #1f5fa8;
  padding-bottom: 5mm;
}
.subtitle { font-size: 19pt; color: #444; margin: 0 0 5mm 0; }
ul { font-size: 19pt; line-height: 1.5; margin: 0; padding-left: 8mm; }
li { margin-bottom: 4mm; }
.grid2 { display: flex; gap: 12mm; flex: 1; }
.grid2 > div { flex: 1; }
.box {
  background: #f3f6fb;
  border-left: 3pt solid #1f5fa8;
  padding: 6mm 7mm;
  font-size: 17pt;
  margin-top: auto;
}
.team {
  margin-top: auto;
  font-size: 17pt;
  color: #444;
}
.center { display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; height:100%; }
.tag { display:inline-block; background:#1f5fa8; color:#fff; font-size:14pt; padding:3mm 6mm; border-radius: 3mm; margin-bottom:7mm; }
table.mini { border-collapse: collapse; font-size: 16pt; width: 100%; margin-top: 5mm; }
table.mini th, table.mini td { border: 0.5pt solid #ccc; padding: 3mm 5mm; text-align: left; }
table.mini th { background: #eef2f8; }
`;

const slides = [];

// Slide 1
slides.push(`
<div class="slide center">
  <div class="tag">TECNOLOGIA EM ANÁLISE E DESENVOLVIMENTO DE SISTEMAS — UEMA/GRAJAÚ</div>
  <h1 style="font-size:54pt;">InfinityQuote</h1>
  <p class="subtitle" style="font-size:21pt;">Sistema Web de Orçamentos para Comunicação Visual</p>
  <p style="margin-top:12mm; font-size:18pt; color:#333;">André Pereira Ferreira &nbsp;·&nbsp; Emerson dos Santos Silva &nbsp;·&nbsp; Jaqueline de Sousa Arruda</p>
  <p style="font-size:15pt; color:#888;">Vivências – Empreendedorismo · Pitch · 28/11/2026</p>
</div>`);

// Slide 2 - Contextualização
slides.push(`
<div class="slide">
  <p class="kicker">Contexto</p>
  <h2 class="slide-title">Onde nasceu essa proposta</h2>
  <ul>
    <li>Infinity Comunicação Visual: microempresa gráfica de Grajaú – MA, 4 colaboradores.</li>
    <li>Atende pessoas físicas, comércios, a prefeitura e candidatos políticos em período eleitoral.</li>
    <li>Observação (fev–mar/2025): tecnologia presente na produção, mas ausente na gestão comercial.</li>
  </ul>
  <div class="box">Orçamentos calculados mentalmente ou em planilha, comunicados por WhatsApp — sem padrão, sem histórico, sem acompanhamento.</div>
</div>`);

// Slide 3 - Problema
slides.push(`
<div class="slide">
  <p class="kicker">Problema / Oportunidade</p>
  <h2 class="slide-title">"A tecnologia chegou na produção, mas nunca chegou no balcão"</h2>
  <ul>
    <li>Orçamentos informais, sem documento padronizado.</li>
    <li>Nenhum histórico de propostas enviadas, aprovadas ou recusadas.</li>
    <li>Preços inconsistentes conforme o atendente.</li>
    <li>Retrabalho ao recalcular orçamentos repetidos.</li>
    <li>Orçamentos perdidos no fluxo de mensagens do WhatsApp.</li>
  </ul>
</div>`);

// Slide 4 - Público-alvo
slides.push(`
<div class="slide">
  <p class="kicker">Público-alvo</p>
  <h2 class="slide-title">Quem usa e quem é impactado</h2>
  <div class="grid2">
    <div class="box" style="margin-top:0;"><strong>Uso direto</strong><br>Atendentes e gestores de microempresas gráficas, como a Infinity Comunicação Visual.</div>
    <div class="box" style="margin-top:0;"><strong>Impacto indireto</strong><br>Clientes dessas gráficas, que passam a receber orçamentos profissionais, padronizados e com aprovação digital.</div>
  </div>
</div>`);

// Slide 5 - Solução
slides.push(`
<div class="slide">
  <p class="kicker">Solução Proposta</p>
  <h2 class="slide-title">InfinityQuote</h2>
  <ul>
    <li>Monta o orçamento a partir de uma tabela de serviços pré-cadastrada.</li>
    <li>Gera um PDF profissional automaticamente.</li>
    <li>Envia ao cliente via WhatsApp com um clique.</li>
    <li>Cliente aprova ou recusa por link único, sem criar conta.</li>
  </ul>
  <div class="box">MVP: cadastro de clientes e serviços · geração de orçamentos em PDF · aprovação digital · dashboard gerencial.</div>
</div>`);

// Slide 6 - Proposta de valor
slides.push(`
<div class="slide">
  <p class="kicker">Proposta de Valor e Diferenciais</p>
  <h2 class="slide-title">Por que isso importa</h2>
  <ul>
    <li>De ~15 minutos para menos de 3 minutos por orçamento.</li>
    <li>Elimina inconsistência de preços; cria histórico consultável.</li>
    <li>Não existe, no mercado local de Grajaú, ferramenta digital acessível para esse porte de negócio.</li>
    <li>Custo de operação muito baixo: stack open source, hospedagem a partir de poucos reais/mês.</li>
  </ul>
</div>`);

// Slide 7 - Modelo de negócio
slides.push(`
<div class="slide">
  <p class="kicker">Modelo de Negócio</p>
  <h2 class="slide-title">Síntese do Business Model Canvas</h2>
  <table class="mini">
    <tr><th>Cliente</th><td>Microempresas de comunicação visual/gráfica</td></tr>
    <tr><th>Receita</th><td>Assinatura mensal (SaaS), acessível ao porte da microempresa</td></tr>
    <tr><th>Canais</th><td>Demonstração direta, indicação entre empresários, feiras do setor</td></tr>
    <tr><th>Recursos-chave</th><td>Equipe técnica + parceria de validação com a Infinity Comunicação Visual</td></tr>
  </table>
  <p style="font-size:14pt;color:#888;margin-top:4mm;">Detalhamento completo no Business Model Canvas — Nota 1.</p>
</div>`);

// Slide 8 - Viabilidade e impacto
slides.push(`
<div class="slide">
  <p class="kicker">Viabilidade e Impacto</p>
  <h2 class="slide-title">É viável e gera resultado</h2>
  <ul>
    <li><strong>Técnica:</strong> stack madura, gratuita e amplamente documentada (React, Node.js, PostgreSQL).</li>
    <li><strong>Econômica:</strong> custo de desenvolvimento nulo em licenciamento; hospedagem a partir de ~R$25/mês.</li>
    <li><strong>Impacto:</strong> mais profissionalismo no atendimento, mais conversão de orçamentos em vendas, base para digitalizar o controle de produção.</li>
  </ul>
</div>`);

// Slide 9 - Próximos passos
slides.push(`
<div class="slide">
  <p class="kicker">Próximos Passos</p>
  <h2 class="slide-title">O caminho a partir daqui</h2>
  <ul>
    <li>Deploy do sistema em ambiente de produção.</li>
    <li>Validação com os atendentes reais da Infinity Comunicação Visual.</li>
    <li>Desenvolvimento do módulo de pedidos de produção e do dashboard avançado.</li>
    <li>Estudo de replicação do modelo para outras gráficas da região.</li>
  </ul>
</div>`);

// Slide 10 - Encerramento
slides.push(`
<div class="slide center">
  <h1 style="font-size:44pt;">Obrigado(a)!</h1>
  <p class="subtitle">Perguntas e contribuições são bem-vindas.</p>
  <p style="margin-top:10mm; font-size:18pt; color:#333;">André Pereira Ferreira · Emerson dos Santos Silva · Jaqueline de Sousa Arruda</p>
  <p style="font-size:15pt; color:#888;">InfinityQuote — Vivências – Empreendedorismo</p>
</div>`);

const html = `<!doctype html><html><head><meta charset="utf-8"><style>${CSS}</style></head><body>${slides.join("\n")}</body></html>`;

async function main() {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: "new",
    args: ["--no-sandbox", "--font-render-hinting=none"],
  });
  const page = await browser.newPage();
  await page.setContent(html, { waitUntil: "networkidle0" });
  await page.pdf({ path: OUT, printBackground: true, preferCSSPageSize: true });
  await page.close();
  await browser.close();
  console.log(`Gerado: ${OUT}`);
}

main().catch((e) => { console.error(e); process.exit(1); });
