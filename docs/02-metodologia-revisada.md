## 3 METODOLOGIA

A presente pesquisa caracteriza-se como um estudo experimental e quantitativo, de natureza comparativa, que mede o desempenho de diferentes arquiteturas de execução para aplicações PHP em condições controladas. Esta seção atualiza e detalha a Metodologia apresentada na etapa anterior, com as versões efetivamente utilizadas e o procedimento de coleta executado.

### 3.1 Objeto de estudo e cenários

Foram avaliados quatro cenários principais, todos com o mesmo orçamento de recursos, de 1,0 CPU e 512 MB de RAM por cenário (no cenário A, dividido entre PHP-FPM, com 0,85 CPU e 448 MB, e Nginx, com 0,15 CPU e 64 MB), e um cenário complementar de sensibilidade:

a) **Cenário A (legado):** CodeIgniter 4.7.5 sobre PHP 8.3.35-FPM, com 4 processos estáticos, e Nginx 1.31.7 como servidor web;
b) **Cenário B (clássico moderno):** o mesmo aplicativo sobre FrankenPHP 1.13.0 em modo clássico, como substituto direto do PHP-FPM, com 4 *threads* PHP, número igual ao de processos do cenário A e de *workers* dos cenários C e D;
c) **Cenário C (vanguarda):** o mesmo aplicativo sobre FrankenPHP em modo Worker, com 4 *workers* e o suporte nativo do CodeIgniter 4.7 ao modo Worker (arquivo `public/frankenphp-worker.php`, gerado pelo comando `php spark worker:install` do próprio *framework*);
d) **Cenário D (referência):** Laravel 13.36.0 com Laravel Octane 2.22.0 sobre FrankenPHP, com 4 *workers*;
e) **Cenário E (sensibilidade):** idêntico ao B, porém com o número padrão de *threads* do FrankenPHP, sem a diretiva `num_threads`. Foi incluído para verificar se o resultado do modo clássico depende dessa configuração.

Todas as imagens de aplicação e de servidor web dos cenários A a E têm a mesma base, Debian 13 (*trixie*), com a mesma versão da biblioteca C (glibc 2.41), e o mesmo PHP 8.3.35, o que evita que diferenças de sistema operacional contaminem a comparação. A única diferença de compilação é inerente às arquiteturas: o PHP do FrankenPHP é compilado em modo *thread-safe* (ZTS), exigido por ele, e o do PHP-FPM em modo *non-thread-safe* (NTS). As imagens e os pacotes foram fixados por versão e por *digest*. Todos usam OPcache com a mesma configuração e o mesmo banco PostgreSQL 16 (contêiner separado, com 0,5 CPU e 256 MB, fora do orçamento dos cenários e idêntico em todos eles).

### 3.2 Endpoints de teste

Os cenários expõem os mesmos endpoints: `/health` (resposta mínima, mede a latência base), `/compute` (gera e serializa em JSON 1.000 elementos, com carga de CPU), `/memory` (incrementa um contador estático e retorna o PID, demonstrando persistência de estado) e `/db` (consulta por chave primária a uma tabela com 10.000 linhas, expondo o PID da conexão PostgreSQL).

### 3.3 Instrumentação

A carga foi gerada pelo Grafana k6 2.3.0 em contêiner isolado (2,0 CPU e 512 MB). Cada execução tem 15 minutos: 2 min de aquecimento até 10 usuários virtuais, 2 min de rampa até 100, 10 min de patamar a 100 usuários e 1 min de desaceleração. Cada usuário dispara requisições continuamente, sem espera entre elas, com a distribuição 10% `/health`, 30% `/compute`, 30% `/memory` e 30% `/db`. As métricas foram exportadas ao Prometheus e visualizadas no Grafana, e o consumo de CPU e RAM dos contêineres foi amostrado com `docker stats` a cada poucos segundos, em paralelo ao teste. A vazão e a latência são calculadas apenas sobre o patamar de 10 minutos (aquecimento, rampa e descida excluídos), e a vazão é o número de requisições do patamar dividido por 600 s; a CPU e a RAM são médias da mesma janela. Como a carga usa um único nível de concorrência (100 usuários virtuais), a vazão medida é a observada nessa carga, e não necessariamente a capacidade máxima de cada cenário.

### 3.4 Procedimento de coleta

A coleta foi automatizada por *script* e executada de uma só vez, do início ao fim, em 19 de outubro de 2026, sem outra ferramenta concorrendo pelos recursos do hospedeiro nas execuções de medição (o navegador só foi usado na etapa (v), para as capturas). As etapas foram: (i) diagnóstico de persistência por *worker* nos cenários C e D (200 requisições sequenciais e 200 concorrentes a `/memory` e `/db`, com 1 e com 4 *workers*); (ii) três execuções de cada cenário A, B, C e D, em ordem rotativa (A, B, C, D, A, B, C, D, A, B, C, D), para reduzir o viés de ordem e de temperatura do hospedeiro; (iii) três execuções do cenário E; (iv) um teste longo, com patamar de 30 minutos, nos cenários C e D, para observar a estabilidade da memória; e (v) uma execução adicional de cada cenário, de 15 minutos, dedicada à captura dos painéis do Grafana. Antes de cada execução, os contêineres anteriores eram derrubados, o *cache* do sistema operacional era limpo (`drop_caches`) e o volume do Prometheus era removido, de modo que cada execução começa sem dados de execuções anteriores.

Os experimentos rodaram em um notebook com processador AMD Ryzen 7 5700U (8 núcleos e 16 *threads*) e 14 GiB de RAM, com Linux e Docker 28.1.1 (Apêndice G). Os *scripts* de coleta e de análise estão no Apêndice D.

### 3.5 Análise dos dados

Para cada cenário foram calculadas a média e o desvio-padrão, entre as três execuções, da vazão (RPS), da latência (p50, p95 e p99), da taxa de erros e do consumo de CPU e RAM, todos calculados no patamar sustentado de 10 minutos. Os ganhos foram expressos em variação percentual. Como as execuções de um mesmo cenário foram apenas três, aplicou-se, em complemento, a análise de variância de um fator (ANOVA) e testes t de Welch par a par, com correção de Bonferroni, em linha com o procedimento adotado por Luz, Silva e Emer (2024); com n = 3 o poder desses testes é limitado, e eles servem como reforço, e não como único critério. A interpretação da latência considera a Lei de Little para sistemas fechados (LITTLE, 1961). O processamento é feito pelo *script* `scripts/analyze.py` (Apêndice D), que gera as tabelas e figuras do capítulo de Resultados.
