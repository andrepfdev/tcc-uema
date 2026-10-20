# Compatibilidade dos blocos temporais (execuções 1–3 de 19/out × 4–5 de 20/out), carga fechada

| Cenário | RPS 19/out | RPS 20/out | diferença (%) | p95 19/out | p95 20/out | diferença (%) |
|---|---|---|---|---|---|---|
| A (PHP-FPM) | 143.2 | 144.1 | +0.6 | 789.7 | 787.8 | -0.2 |
| B (clássico) | 155.8 | 155.6 | -0.2 | 743.2 | 763.8 | +2.8 |
| E (clássico, padrão) | 176.4 | 176.6 | +0.1 | 676.1 | 684.7 | +1.3 |
| C (CI4 Worker) | 303.9 | 305.2 | +0.4 | 397.9 | 397.1 | -0.2 |
| D (Octane) | 336.9 | 339.1 | +0.6 | 383.6 | 382.4 | -0.3 |
