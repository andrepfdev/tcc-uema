| Cenário | health avg / p95 (ms) | compute avg / p95 (ms) | memory avg / p95 (ms) | db avg / p95 (ms) |
|---|---|---|---|---|
| A — CI4 + PHP-FPM | 599.9 / 862.2 | 609.2 / 885.7 | 600.8 / 861.8 | 644.8 / 899.7 |
| B — CI4 + FrankenPHP clássico | 708.6 / 996.2 | 709.0 / 1000.0 | 707.2 / 997.5 | 719.8 / 1009.6 |
| C — CI4 + FrankenPHP Worker | 265.9 / 407.4 | 277.3 / 435.4 | 266.6 / 425.5 | 268.7 / 431.0 |
| D — Laravel Octane | 207.4 / 312.5 | 217.0 / 324.4 | 207.3 / 312.4 | 209.5 / 313.7 |
