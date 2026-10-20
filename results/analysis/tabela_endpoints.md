| Cenário | health avg / p95 (ms) | compute avg / p95 (ms) | memory avg / p95 (ms) | db avg / p95 (ms) |
|---|---|---|---|---|
| A — CI4 + PHP-FPM | 529.0 / 775.2 | 536.8 / 781.0 | 527.8 / 775.6 | 565.3 / 794.5 |
| B — CI4 + FrankenPHP clássico | 482.2 / 697.3 | 492.1 / 700.9 | 484.2 / 697.3 | 525.4 / 754.5 |
| C — CI4 + FrankenPHP Worker | 241.3 / 392.0 | 251.1 / 397.1 | 241.3 / 392.1 | 242.2 / 392.7 |
| D — Laravel Octane | 217.5 / 331.1 | 228.1 / 382.7 | 217.2 / 328.7 | 219.7 / 367.4 |
| E — CI4 + FrankenPHP clássico (threads padrão) | 436.8 / 648.9 | 439.9 / 652.9 | 436.5 / 648.9 | 456.9 / 674.9 |
