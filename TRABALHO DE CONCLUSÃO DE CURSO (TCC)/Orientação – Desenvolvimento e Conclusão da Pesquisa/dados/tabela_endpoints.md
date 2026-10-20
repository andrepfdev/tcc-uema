| Cenário | health avg / p95 (ms) | compute avg / p95 (ms) | memory avg / p95 (ms) | db avg / p95 (ms) |
|---|---|---|---|---|
| A — CI4 + PHP-FPM | 684.2 / 780.2 | 691.3 / 784.7 | 683.7 / 780.5 | 721.3 / 798.2 |
| B — CI4 + FrankenPHP clássico | 625.3 / 702.9 | 634.2 / 706.4 | 625.0 / 702.6 | 669.2 / 763.2 |
| C — CI4 + FrankenPHP Worker | 324.3 / 396.1 | 336.2 / 400.4 | 324.1 / 396.2 | 326.1 / 396.7 |
| D — Laravel Octane | 291.6 / 379.1 | 304.4 / 388.9 | 291.4 / 378.6 | 294.1 / 381.2 |
| E — CI4 + FrankenPHP clássico (threads padrão) | 558.7 / 667.2 | 562.9 / 670.6 | 558.9 / 666.5 | 579.4 / 688.5 |
