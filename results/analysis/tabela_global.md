| Cenário | n | RPS (média ± dp) | Latência p50 (ms) | p95 (ms) | p99 (ms) | Erros (%) |
|---|---|---|---|---|---|---|
| A — CI4 + PHP-FPM | 3 | 143.2 ± 0.6 | 698.2 | 789.7 | 807.2 | 0.00 |
| B — CI4 + FrankenPHP clássico | 3 | 155.8 ± 1.6 | 618.0 | 743.2 | 793.2 | 0.00 |
| C — CI4 + FrankenPHP Worker | 3 | 303.9 ± 2.1 | 309.8 | 397.9 | 408.3 | 0.00 |
| D — Laravel Octane | 3 | 336.9 ± 1.0 | 298.2 | 383.6 | 399.7 | 0.00 |
| E — CI4 + FrankenPHP clássico (threads padrão) | 3 | 176.4 ± 1.8 | 563.3 | 676.1 | 734.3 | 0.00 |
