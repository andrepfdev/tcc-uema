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
