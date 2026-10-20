# Compatibilidade dos blocos temporais (execuções 1–3 de 19/out × 4–5 de 20/out), carga fechada

| Cenário | RPS 19/out | RPS 20/out | diferença (%) | p95 19/out | p95 20/out | diferença (%) |
|---|---|---|---|---|---|---|
| A (PHP-FPM) | 143.7 | 144.3 | +0.4 | 785.6 | 783.3 | -0.3 |
| B (clássico) | 156.1 | 156.2 | +0.0 | 710.0 | 720.3 | +1.4 |
| E (clássico, padrão) | 175.5 | 175.5 | -0.0 | 660.6 | 668.6 | +1.2 |
| C (CI4 Worker) | 318.1 | 317.0 | -0.4 | 394.1 | 393.1 | -0.3 |
| D (Octane) | 351.3 | 352.1 | +0.2 | 374.6 | 371.5 | -0.8 |
