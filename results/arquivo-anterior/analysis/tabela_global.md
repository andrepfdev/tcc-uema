| Cenário | n | RPS (média ± dp) | Latência p50 (ms) | p95 (ms) | p99 (ms) | Erros (%) |
|---|---|---|---|---|---|---|
| A — CI4 + PHP-FPM | 3 | 126.4 ± 1.4 | 764.5 | 890.9 | nan | 0.00 |
| B — CI4 + FrankenPHP clássico | 3 | 109.5 ± 0.5 | 877.7 | 1002.2 | nan | 0.00 |
| C — CI4 + FrankenPHP Worker | 3 | 287.7 ± 5.1 | 307.9 | 430.8 | nan | 0.00 |
| D — Laravel Octane | 3 | 368.7 ± 2.1 | 275.8 | 314.8 | nan | 0.00 |
