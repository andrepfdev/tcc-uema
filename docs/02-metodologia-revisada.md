## 3 METODOLOGIA

A presente pesquisa caracteriza-se como um estudo experimental e quantitativo, de natureza comparativa, que mede o desempenho de diferentes arquiteturas de execução para aplicações PHP em condições controladas.

### 3.1 Objeto de estudo e cenários

Foram avaliados quatro cenários, todos com o mesmo orçamento de recursos, de 1,0 CPU e 512 MB de RAM por cenário (no cenário A, dividido entre PHP-FPM, com 0,85 CPU e 448 MB, e Nginx, com 0,15 CPU e 64 MB):

- **Cenário A (legado):** CodeIgniter 4.7.3 sobre PHP 8.3-FPM, com 4 processos estáticos e Nginx como servidor web.
- **Cenário B (clássico moderno):** o mesmo aplicativo sobre FrankenPHP em modo clássico, como substituto direto do PHP-FPM.
- **Cenário C (vanguarda):** o mesmo aplicativo sobre FrankenPHP em modo Worker, com 4 *workers* e o suporte nativo do CodeIgniter 4.7 ao modo Worker (arquivo `public/frankenphp-worker.php`, gerado pelo próprio *framework*). Esta versão corrige o texto da etapa anterior, que mencionava uma *bridge* customizada.
- **Cenário D (referência):** Laravel 13 com Laravel Octane sobre FrankenPHP, com 4 *workers*.

Todos usam OPcache com a mesma configuração e o mesmo banco PostgreSQL 16 (contêiner separado, fora do orçamento dos cenários).

### 3.2 Endpoints de teste

Os quatro cenários expõem os mesmos endpoints: `/health` (resposta mínima, mede a latência base), `/compute` (gera e serializa em JSON 1.000 elementos, com carga de CPU), `/memory` (incrementa um contador estático e retorna o PID, demonstrando persistência de estado) e `/db` (consulta por chave primária a uma tabela com 10.000 linhas, expondo o PID da conexão PostgreSQL).

### 3.3 Instrumentação

A carga foi gerada pelo Grafana k6 em contêiner isolado (2,0 CPU e 512 MB). Cada execução tem 15 minutos: 2 min de aquecimento até 10 usuários virtuais, 2 min de rampa até 100, 10 min de patamar a 100 usuários e 1 min de desaceleração. Cada usuário dispara requisições continuamente, sem espera entre elas, com a distribuição 10% `/health`, 30% `/compute`, 30% `/memory` e 30% `/db`. As métricas foram exportadas ao Prometheus, visualizadas no Grafana, e o consumo de CPU e RAM dos contêineres foi amostrado com `docker stats` a cada cerca de 7 segundos.

### 3.4 Procedimento de coleta

Cada cenário foi executado três vezes, em ordem rotativa (A, B, C, D, A, B, C, D, A, B, C, D), para reduzir o viés de ordem e de temperatura do hospedeiro. Antes de cada execução, os contêineres anteriores eram derrubados e as métricas do Prometheus, apagadas. Uma execução do cenário D (terceira rodada) foi refeita isoladamente após falha de rede no *build*. Os experimentos rodaram em um notebook com processador AMD Ryzen 7 5700U (8 núcleos e 16 *threads*) e 14 GiB de RAM, com Linux e Docker 28.1.1; a limpeza do cache do sistema operacional entre execuções não foi possível por falta de permissão administrativa.

### 3.5 Análise dos dados

Para cada cenário foram calculadas a média e o desvio-padrão, entre as três execuções, da vazão (RPS), da latência (p50 e p95), da taxa de erros e do consumo de CPU e RAM no patamar sustentado. Os ganhos foram expressos em variação percentual sobre o cenário A. Considerou-se relevante uma diferença muito maior que o desvio-padrão entre execuções. O processamento é feito pelo script `scripts/analyze.py` (Apêndice D), que gera as tabelas e figuras do capítulo de Resultados.
