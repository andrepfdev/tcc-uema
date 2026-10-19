## 2 FUNDAMENTAÇÃO TEÓRICA

### 2.1 Modelos de execução do PHP

No modelo tradicional, o PHP processa cada requisição de forma independente: o interpretador carrega o código, executa-o e libera os recursos ao final, sem preservar estado em memória entre requisições. O PHP-FPM (*FastCGI Process Manager*) mantém um *pool* de processos já iniciados, o que evita criar um processo a cada acesso, mas o código da aplicação, e portanto a inicialização do *framework*, continua sendo executado do zero a cada requisição. Luz, Silva e Emer (2025) descrevem esse modelo como síncrono e sem estado (*stateless*) e o comparam ao modelo assíncrono da extensão Swoole, em experimento de carga com análise estatística (ANOVA e teste t), concluindo que o modo de operação foi o fator determinante do desempenho, com o modelo assíncrono superando o síncrono no atendimento a múltiplas requisições.

### 2.2 FrankenPHP: modo clássico e modo Worker

O FrankenPHP é um servidor de aplicação para PHP construído sobre o servidor Caddy, que incorpora o interpretador PHP ao próprio processo do servidor (FRANKENPHP, 2026). Sem nenhuma configuração adicional, opera no **modo clássico**, em que funciona como um servidor PHP tradicional, servindo diretamente os arquivos PHP, e pode substituir o PHP-FPM ou o Apache com `mod_php`. O número de conexões aceitas e enfileiradas é limitado apenas pelos recursos do sistema, e o PHP usa um número fixo de *threads* iniciadas na partida, comparável ao modo estático do PHP-FPM (FRANKENPHP, 2026).

No **modo Worker**, o *script* de entrada da aplicação é carregado uma única vez e permanece vivo, atendendo requisições em um laço: a inicialização do *framework* ocorre uma vez por *worker*, e cada requisição executa apenas o tratamento do pedido (FRANKENPHP, 2026). A contrapartida é que o programador passa a ser responsável por não vazar estado de uma requisição para outra, já que objetos e variáveis estáticas podem sobreviver entre elas.

### 2.3 Laravel Octane e suporte do CodeIgniter 4 ao modo Worker

O Laravel Octane é o pacote oficial do Laravel para executar a aplicação sobre servidores persistentes, entre eles FrankenPHP, Swoole e RoadRunner (LARAVEL, 2026). Ele mantém o *framework* inicializado em memória entre requisições e trata a limpeza do estado por requisição, o que o torna a referência de mercado para esse modelo no ecossistema PHP. O CodeIgniter 4 passou a oferecer suporte nativo ao modo Worker a partir da versão 4.7, com um *script* de entrada gerado pelo próprio *framework* (CODEIGNITER FOUNDATION, 2026), que reinicia o estado de cada requisição e reconecta recursos como banco de dados e cache.

### 2.4 Avaliação de desempenho de *frameworks* web

Estudos recentes comparam *frameworks* web quanto a tempo de resposta, vazão e uso de recursos com ferramentas de carga como o k6. Azzahidi, Wijayanto e Darmawan (2025), por exemplo, avaliaram Spring Boot, Flask, Express.js, Laravel com FrankenPHP e Gin em APIs REST e destacaram o Laravel com FrankenPHP pelo uso eficiente de memória. O k6, mantido pela Grafana Labs, permite descrever cenários de carga em JavaScript, definir rampas de usuários virtuais e exportar métricas para sistemas de monitoramento como o Prometheus (GRAFANA LABS, 2026), e é a ferramenta adotada neste trabalho.

### 2.5 Rigor em *benchmarks*

A literatura sobre *benchmarking* ressalta que resultados de desempenho dependem do desenho experimental e do ambiente de execução. Laaber, Basmaci e Salza (2021) tratam da instabilidade de *benchmarks* de *software*, isto é, da variabilidade de medições repetidas, o que justifica repetir as execuções e relatar a dispersão. Zhan (2022) discute a necessidade de *benchmarks* confiáveis, representativos e reprodutíveis para tecnologias computacionais emergentes; Brunst et al. (2022) relatam a experiência de construir e aplicar um conjunto padronizado de *benchmarks* (SPEChpc 2021); e Jia et al. (2013) mostram que a diversidade de aplicações e de volumes de dados afeta as conclusões de um *benchmark*. Essas contribuições orientam as escolhas metodológicas deste estudo: ambiente conteinerizado com limites idênticos de recursos, três execuções por cenário em ordem rotativa, relato de desvio-padrão e discussão explícita das limitações da carga sintética utilizada.
