# Regras ABNT usadas nesta skill

Extraídas do **Manual para Normalização de Trabalhos Acadêmicos da UEMA** (5ª ed., 2024,
Sistema Integrado de Bibliotecas da UEMA — baseado na NBR 14724/2011, NBR 10719/2011,
NBR 6024/2012, NBR 6023/2018), que por sua vez segue a ABNT "genérica". Ao aplicar esta
skill em outra instituição, **procure o manual de normalização próprio dela primeiro**
(busque `"<sigla da instituição>" manual normalização trabalhos acadêmicos ABNT filetype:pdf`
ou no site da biblioteca) — a maioria das universidades brasileiras publica um manual
assim, e ele pode divergir em detalhes (ex.: caixa alta vs. baixa no subtítulo da capa).
Use os valores abaixo como *default* razoável quando não houver manual específico.

## Formato e margens
- Papel A4 (21 × 29,7 cm).
- Margens: **superior 3 cm, esquerda 3 cm, inferior 2 cm, direita 2 cm.**
- Fonte: tamanho **12** para o texto corrido (Times New Roman ou Arial — mantenha uma só
  em todo o documento). Tamanho **10** para: citações com mais de 3 linhas, notas de
  rodapé, paginação, ficha catalográfica, legendas/fontes de ilustrações e tabelas.
- Parágrafo: recuo de primeira linha de **2 cm** a partir da margem esquerda.
- Espaçamento: **1,5** entre linhas no texto corrido. Espaçamento **simples** em:
  citações longas, notas, referências (e separadas entre si por uma linha em branco
  simples), natureza do trabalho/objetivo na folha de rosto, legendas, ficha catalográfica.

## Estrutura do trabalho
Parte externa: **capa** (obrigatória) [+ lombada, opcional].
Parte interna:
- **Pré-textuais**: folha de rosto (obrigatória), ficha catalográfica, errata, folha de
  aprovação, dedicatória, agradecimentos, epígrafe, resumo (obrigatório), listas,
  **sumário (obrigatório)**.
- **Textuais**: introdução, desenvolvimento, conclusão/considerações finais.
- **Pós-textuais**: **referências (obrigatórias)**, glossário, apêndice(s), anexo(s), índice.

## Capa (ordem dos elementos, tudo centralizado)
a) nome da instituição + centro/departamento (se houver) + curso — **caixa alta, sem negrito**
   (adapte: alguns cursos aceitam negrito; siga o padrão local se existir um exemplo prévio).
b) nome completo do(s) autor(es) — caixa alta, negrito.
c) título do trabalho — caixa alta, negrito.
d) subtítulo, se houver — caixa baixa, sem negrito, geralmente após dois-pontos.
   ⚠️ **Regra pode variar por instituição**: sempre confirme com o usuário/manual local
   se o subtítulo deve ir em maiúsculas ou minúsculas antes de gerar a versão final.
e) local (cidade) da instituição.
f) ano de depósito/entrega.

## Folha de rosto
Mesmos elementos do título, **mais**:
- natureza do trabalho (tipo: TCC, dissertação, tese, relatório técnico, projeto de
  pesquisa etc.), objetivo (aprovação em disciplina, grau pretendido), nome da
  instituição a que é submetido, área de concentração;
- nome do orientador/tutor (e coorientador, se houver).
- **Posicionamento**: autor e título — caixa alta, centralizados. O bloco de
  "natureza do trabalho + orientador" é **alinhado do meio da mancha até a margem
  direita** (na prática, um recuo à esquerda de ~8 cm numa mancha de 16 cm de largura
  útil), fonte 12, **espaço simples**, texto justificado.
- Local e ano ao final, centralizados.

## Sumário
- Título "SUMÁRIO" centralizado, sem numeração.
- Lista os títulos das seções textuais e pós-textuais na mesma ordem, grafia e
  grau de destaque (negrito/caixa alta) em que aparecem no corpo do texto.
- Idealmente com linha pontilhada até o número da página correspondente — **mas gerar
  o número de página exato exige saber a paginação final**; ver seção "Limitações"
  abaixo sobre como esta skill lida com isso.

## Títulos de seção (NBR 6024)
- Seções primárias (`1 INTRODUÇÃO`, `2 ...`) — **cada uma começa em folha nova**,
  negrito, **caixa alta**.
- Seções secundárias (`1.1 ...`) — negrito, caixa baixa (não força maiúsculas).
- Terciárias (`1.1.1`) — normal, caixa baixa; quaternárias — itálico; quinárias —
  itálico sublinhado (usadas raramente; a maioria dos trabalhos de graduação não passa
  de seção secundária/terciária).
- Títulos **sem** indicativo numérico (RESUMO, SUMÁRIO, REFERÊNCIAS, ANEXOS...) seguem
  o mesmo destaque tipográfico das primárias, mas sem número.

## Paginação
- A contagem de folhas começa na **folha de rosto** (a capa não é contada).
- Folhas pré-textuais (folha de rosto, sumário etc.) são **contadas, mas não numeradas**
  (o número não aparece impresso nelas).
- A numeração **aparece** a partir da primeira folha do texto (`1 INTRODUÇÃO`), no
  **canto superior direito, a 2 cm da borda superior**, fonte 10.
- Ou seja: se a folha de rosto e o sumário ocupam juntas *N* páginas, a primeira página
  do texto exibe o número **N+1** (não "1").

## Quadros e tabelas
- "Quadro" = dados qualitativos/textuais, bordas fechadas nos 4 lados (é o que se usa
  para especificações, cronogramas, comparativos — praticamente tudo em trabalhos de TI
  e negócios). "Tabela" = dados estatísticos, tradicionalmente sem bordas verticais.
- Identificação/legenda **acima**, com o rótulo (Quadro N / Tabela N), travessão e
  título, fonte 10, alinhado à esquerda (não centralizado, apesar de alguns modelos
  antigos centralizarem — siga o manual local se divergir).
- **Fonte obrigatória abaixo**, mesmo quando é produção própria: "Fonte: elaborado
  pelos autores (ano)." Fonte 10.
- Devem ser citados no texto antes de aparecer ("...conforme o Quadro 1.") e inseridos
  o mais próximo possível do trecho referenciado.

## Referências (NBR 6023)
- Alinhadas à **esquerda** (não justificadas), espaçamento **simples** dentro de cada
  referência, separadas entre si por **uma linha em branco simples**.
- Ordem alfabética pelo sobrenome/entidade do primeiro autor.
- Elemento de destaque (normalmente o título da obra) em **negrito**.

## Citações (NBR 10520)
- Citação direta curta (até 3 linhas): incorporada ao parágrafo, entre aspas.
- Citação direta longa (mais de 3 linhas): recuo de **4 cm** da margem esquerda, fonte
  10, espaço simples, sem aspas.
- Sistema autor-data é o mais comum em trabalhos de graduação: `(SOBRENOME, ano, p. X)`.

## O que esta skill assume por padrão (ajustável)
- Fonte: **Liberation Serif** (substituto metricamente compatível com Times New Roman,
  presente por padrão na maioria das distros Linux — `fc-list | grep -i "liberation serif"`
  para confirmar). Se a instituição não exigir Times New Roman especificamente, mantenha;
  senão, troque a `font-family` no CSS/DOCX pela fonte exigida.
- Título/subtítulo da capa **em caixa alta ambos** só quando o usuário pedir ou o
  manual da instituição exigir — a regra "clássica" da NBR 14724 é subtítulo em caixa
  baixa. Sempre confirme antes de decidir por conta própria.
