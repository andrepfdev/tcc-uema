| Cenário | n | RPS (média ± dp) | Latência p50 (ms) | p95 (ms) | p99 (ms) | Erros (%) |
|---|---|---|---|---|---|---|
| A — CI4 + PHP-FPM | 3 | 143.7 ± 0.5 | 687.4 | 785.6 | 800.5 | 0.00 |
| B — CI4 + FrankenPHP clássico | 3 | 156.1 ± 1.4 | 602.7 | 710.0 | 782.9 | 0.00 |
| C — CI4 + FrankenPHP Worker | 3 | 318.1 ± 6.1 | 300.2 | 394.1 | 405.7 | 0.00 |
| D — Laravel Octane | 3 | 351.3 ± 0.9 | 287.6 | 374.6 | 396.8 | 0.00 |
| E — CI4 + FrankenPHP clássico (threads padrão) | 3 | 175.5 ± 1.7 | 524.6 | 660.6 | 720.7 | 0.00 |
