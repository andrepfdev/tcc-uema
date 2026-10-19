// Modelo de configuração — copie para docs.config.mjs (mesma pasta dos build-*.mjs)
// e adapte por trabalho. Cada entrada do array `docs` gera UM PDF (build-pdf.mjs)
// e UM DOCX (build-docx.mjs) a partir do MESMO arquivo .md de origem (mdPath).

const BASE = "/caminho/absoluto/para/a/pasta/do/trabalho";

// Reaproveitado por todos os documentos do mesmo grupo/equipe.
const autores = [
  { nome: "Fulano de Tal", matricula: "00000000000" },
  { nome: "Ciclana da Silva", matricula: "00000000001" },
];

// Nome real do(a) professor(a)/tutor(a) — NUNCA invente; pergunte ao usuário se não souber
// e deixe algo como "[nome do(a) tutor(a)]" até ele confirmar.
const docente = "Nome do(a) Tutor(a)";

export const docs = [
  {
    key: "identificador-curto-do-documento", // só nomeia arquivos temporários, não aparece no PDF
    mdPath: `${BASE}/pasta/Nome do Documento.md`,
    outPath: `${BASE}/pasta/Nome do Documento.pdf`, // build-docx.mjs troca .pdf -> .docx sozinho

    // Linhas do topo da capa/folha de rosto (maiúsculas, negrito, centralizadas).
    instituicao: [
      "NOME DA UNIVERSIDADE",
      "NOME DO CAMPUS/NÚCLEO (se houver)",
      "NOME DO CURSO",
      "TURMA / PERÍODO",
    ],

    // Nome do trabalho/produto (capa e folha de rosto, sempre em CAIXA ALTA e negrito).
    tituloObra: "Nome do Produto/Projeto – Subtítulo Descritivo Curto",

    // Natureza específica desta entrega. Confira com o enunciado/manual da instituição
    // se deve ir em caixa alta (algumas pedem, ex.: UEMA pediu maiúsculas aqui) ou em
    // caixa baixa (regra "clássica" da NBR 14724, subtítulo sem negrito e minúsculo).
    subtituloTrabalho: "TIPO DESTE DOCUMENTO (EX.: RELATÓRIO TÉCNICO)",

    // Linha(s) extra abaixo do subtítulo, na capa (ex.: disciplina/nota).
    capaInfo: [
      "Disciplina: Nome da Disciplina – Etapa – Nota X",
    ],

    autores,
    cidade: "Cidade – UF",
    ano: "2026",

    // Parágrafo(s) da "natureza do trabalho" — bloco justificado, recuado à direita,
    // na folha de rosto (regra ABNT NBR 14724). Adapte a frase ao tipo de trabalho
    // (projeto de pesquisa, relatório técnico, TCC, artigo etc.).
    naturezaParagraphs: [
      "Trabalho apresentado à disciplina de X, do curso Y, da Instituição Z, como requisito parcial de avaliação (Nota N).",
    ],

    docente,
  },
  // ...repita um bloco por documento (Nota 1, Nota 2 etc.), reaproveitando `autores`/`docente`.
];
