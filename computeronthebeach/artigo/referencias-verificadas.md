# Referências novas (verificadas em 19/10/2026, abertas e lidas)

Buscas feitas (WebSearch): servidores PHP persistentes / modo Worker / estado compartilhado; benchmarks de Laravel Octane,
Swoole, RoadRunner e FrankenPHP; modelos de carga aberto × fechado. **Resultado: não apareceu estudo revisado por pares que isole o
efeito do modo Worker em um mesmo framework PHP**; só blogs, issues e repositórios de benchmark, com resultados que se contradizem
entre si. Isso sustenta a frase da lacuna, escrita com cautela ("nas buscas realizadas não encontramos...").

| Uso no artigo | Fonte | O que sustenta (conferido na página) |
|---|---|---|
| Modelo aberto × fechado; por que a latência no modelo fechado acompanha a vazão | Schroeder, Wierman, Harchol-Balter. *Open Versus Closed: A Cautionary Tale.* NSDI '06, San Jose, 8–10 mai. 2006. https://static.usenix.org/events/nsdi06/tech/full_papers/schroeder/schroeder_html/index.html | Há "uma vasta diferença de comportamento entre os modelos aberto e fechado em cenários reais", mesmo sob a mesma carga; o modelo fechado dispara novas requisições após as conclusões, o aberto as dispara independentemente delas. |
| Teste de taxa fixa no k6 (`constant-arrival-rate`) | Grafana Labs. *Open and closed models* (k6 docs). https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/ | No modelo fechado, um sistema lento reduz a taxa de chegada; no aberto, "os tempos de resposta do alvo não influenciam mais a carga"; o `constant-arrival-rate` inicia iterações a taxa fixa. Descreve o problema também chamado de *coordinated omission*. |
| Estado da arte (literatura cinzenta) | Lino, T. *Laravel Octane Benchmark: Swoole vs RoadRunner vs FrankenPHP.* https://terrylinooo.github.io/laravel-octane-benchmark/ (já na Estrutura Inicial do TCC) | Compara servidores com Octane (p50–p99, vazão, RSS), mas a página não informa versões, hardware nem ferramenta de carga; `--max-requests` não aplicado. Usar apenas para dizer que as comparações existentes são de relatos de profissionais com metodologia pouco detalhada. |

Não usar (não são verificáveis como referência científica): posts de blog de fornecedores (Deploynix, PHPBenchLab, DEV, Medium)
e a issue do GitHub, cujos resultados se contradizem sobre qual servidor é mais rápido.

## Decisão final (20/10/2026)
No artigo entraram Schroeder et al. (NSDI 2006) e a documentação do k6 (modelos aberto e fechado). O benchmark do Lino **não** foi
citado: é literatura cinzenta sem autoria identificável com certeza e sem metodologia detalhada. A lacuna foi escrita como
"nas buscas que realizamos, não encontramos estudo revisado por pares…".

## Atualização (23/10/2026): Dhaniswara, Kusumasari e Alam (2025)
Dhaniswara, A.; Kusumasari, T. F.; Alam, E. N. *Performance Evaluation of Laravel Application Deployment on Docker.* ICITCOM 2025, IEEE, p. 170-175.
DOI 10.1109/ICITCOM66635.2025.11265204 (PDF lido por inteiro, páginas 170-175).

- **Sustenta:** IPC e reinicialização do PHP-FPM + Nginx; modelo integrado do FrankenPHP; desenho (Laravel 12, Docker, limites idênticos, JMeter, 100 usuários, 10 min);
  endpoint leve: tempo médio −15,8%, vazão +18,6%, p99 574 × 794 ms, memória ~155 × ~69 MB; endpoint pesado: CPU saturada nas duas, gargalo na aplicação.
- **Não citar** os números do endpoint pesado (`/api/clos`): vazão relatada 2,3-2,4 req/s com 140-150 amostras em 600 s (≈ 0,25 req/s) e RAM 2 GB (método) × 2,5 GB (resultados).
- **A frase da lacuna foi reescrita.** A versão anterior ("não encontramos estudo revisado por pares que compare o modo Worker em um mesmo framework sob orçamento idêntico") deixou de valer:
  esse estudo faz isso para o Laravel. A lacuna passou a ser: (i) nenhum estudo inclui o modo clássico do FrankenPHP como cenário intermediário (separar servidor e modo Worker) e (ii) nenhum usa o CodeIgniter 4.
- Cenário E: o "número padrão de threads" do FrankenPHP é 2 × núcleos visíveis; com `--cpus 1.0` o log de inicialização mostrou `total_threads: 2` (B: 4; sem limite: 32). Corrigido no texto.
