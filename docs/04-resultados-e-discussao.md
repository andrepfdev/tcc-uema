## 4 RESULTADOS E DISCUSSÃO

Este capítulo apresenta os resultados obtidos nos quatro cenários descritos na Metodologia e os interpreta à luz do referencial teórico. Os valores oficiais provêm de 12 execuções do teste de carga (3 repetições por cenário, sem navegador ou outra ferramenta concorrendo pelos recursos do hospedeiro). As figuras extraídas do Grafana (Figuras 4 a 7) vêm de uma rodada extra, feita apenas para captura de tela, e não entram nas médias.

### 4.1 Validação do ambiente experimental

Antes das medições, cada cenário foi submetido a um teste de sanidade (*smoke test*) e os quatro endpoints (`/health`, `/compute`, `/memory` e `/db`) responderam com sucesso. Nas 12 execuções válidas, todas as verificações (*checks*) do k6 passaram e a taxa de falhas HTTP foi de 0,00%, o que indica que as diferenças de desempenho adiante não decorrem de erros de aplicação.

Os endpoints `/memory` e `/db` revelam o que cada arquitetura realmente preserva entre requisições. Em verificação manual, três requisições consecutivas a cada cenário resultaram em:

**Quadro 1 – Estado preservado entre requisições, por cenário**

| Cenário | `/memory`: contador e PID | `/db`: PID da conexão PostgreSQL |
|---|---|---|
| A – CI4 + PHP-FPM | contador 1, 1, 1; PIDs diferentes (8, 7, 9) | muda a cada requisição (nova conexão) |
| B – CI4 + FrankenPHP clássico | contador 1, 1; PID 1 | não verificado |
| C – CI4 + FrankenPHP Worker | contador 1, 1, 1; PID fixo (1) | muda a cada requisição (62, 63, 64) |
| D – Laravel Octane | contador 1, 2, 3; PID fixo (14) | fixo (69): conexão reutilizada |

Fonte: elaborado pelo autor (2026), por verificação manual com `curl`.

O resultado é relevante: apenas o Laravel Octane (D) preservou tanto o estado da aplicação quanto a conexão com o banco. No CodeIgniter 4 em modo Worker (C), o processo PHP permanece vivo (PID fixo), mas o contador é reiniciado e a conexão com o banco é refeita a cada requisição, ou seja, o *framework* reinicia o estado da aplicação entre requisições por projeto (como medida de isolamento) e fecha a conexão ao final. Portanto, o ganho do cenário C vem da eliminação da inicialização do *framework* (carregamento de classes, serviços e configuração), e não do reaproveitamento de estado ou de conexão. Esse achado corrige a expectativa inicial do trabalho, descrita na Introdução e nos materiais do projeto, de que o contador do `/memory` cresceria no cenário C.

### 4.2 Vazão (requisições por segundo)

A Tabela 1 e a Figura 1 apresentam a vazão média e o desvio-padrão das três execuções de cada cenário, sob 100 usuários virtuais simultâneos durante o patamar sustentado do teste, em um orçamento de 1,0 CPU e 512 MB por cenário.

**Tabela 1 – Vazão e latência global por cenário (média das 3 execuções)**

| Cenário | RPS (média ± dp) | Latência p50 (ms) | Latência p95 (ms) | Erros (%) |
|---|---|---|---|---|
| A – CI4 + PHP-FPM | 126,4 ± 1,4 | 764,5 | 890,9 | 0,00 |
| B – CI4 + FrankenPHP clássico | 109,5 ± 0,5 | 877,7 | 1002,2 | 0,00 |
| C – CI4 + FrankenPHP Worker | 287,7 ± 5,1 | 307,9 | 430,8 | 0,00 |
| D – Laravel Octane | 368,7 ± 2,1 | 275,8 | 314,8 | 0,00 |

Fonte: elaborado pelo autor (2026), a partir dos resumos do k6. Nota: p50 e p95 calculados sobre toda a execução, incluindo as rampas.

![Figura 1](figuras/fig_rps.png)

**Figura 1 – Vazão média (RPS) por cenário, com desvio-padrão das 3 execuções.** Fonte: elaborado pelo autor (2026).

Em relação ao cenário A (referência), o modo clássico do FrankenPHP (B) apresentou vazão 13,4% menor, o Worker com CodeIgniter 4 (C) apresentou vazão 127,7% maior (cerca de 2,3 vezes) e o Laravel Octane (D) apresentou vazão 191,7% maior (cerca de 2,9 vezes). Entre C e B, a diferença é de 162,8% a favor de C. Todas essas diferenças são muito maiores que a variação entre execuções do mesmo cenário (desvio-padrão entre 0,4% e 1,8% da média), o que dá segurança de que não são ruído de medição.

### 4.3 Latência por endpoint

A Tabela 2 e a Figura 2 detalham a latência média e o percentil 95 por endpoint.

**Tabela 2 – Latência por endpoint (média / p95, em ms)**

| Cenário | /health | /compute | /memory | /db |
|---|---|---|---|---|
| A – CI4 + PHP-FPM | 599,9 / 862,2 | 609,2 / 885,7 | 600,8 / 861,8 | 644,8 / 899,7 |
| B – CI4 + FrankenPHP clássico | 708,6 / 996,2 | 709,0 / 1000,0 | 707,2 / 997,5 | 719,8 / 1009,6 |
| C – CI4 + FrankenPHP Worker | 265,9 / 407,4 | 277,3 / 435,4 | 266,6 / 425,5 | 268,7 / 431,0 |
| D – Laravel Octane | 207,4 / 312,5 | 217,0 / 324,4 | 207,3 / 312,4 | 209,5 / 313,7 |

Fonte: elaborado pelo autor (2026).

![Figura 2](figuras/fig_latencia_p95.png)

**Figura 2 – Latência p95 por endpoint e cenário.** Fonte: elaborado pelo autor (2026).

Um achado importante é que a latência é praticamente a mesma nos quatro endpoints dentro de cada cenário, embora o `/health` não faça processamento e o `/compute` gere e serialize mil registros. A explicação é a forma de carga: o k6 mantém 100 usuários virtuais disparando requisições continuamente, sem tempo de espera entre elas, e o servidor, limitado a 1 CPU, está saturado (Seção 4.4). Nessa condição, o tempo de resposta é dominado pelo tempo de fila e, pela Lei de Little, aproxima-se de usuários ÷ vazão. A conta confere: 100 ÷ 126,4 ≈ 791 ms no cenário A (p50 medido: 765 ms) e 100 ÷ 368,7 ≈ 271 ms no cenário D (p50 medido: 276 ms). Consequentemente, a latência aqui é um espelho da vazão, e não uma medida independente do custo de cada endpoint. Isso limita a conclusão sobre o diferencial do `/db` (reaproveitamento de conexão): a diferença entre `/db` e `/health` é pequena em todos os cenários (por exemplo, 45 ms no cenário A e 3 ms no cenário C), mas o desenho do experimento não isola o custo de cada endpoint com precisão. Para isso seria necessária carga com taxa de chegada fixa (modelo aberto), tema indicado nos trabalhos futuros.

### 4.4 Consumo de CPU e memória

**Tabela 3 – Consumo de recursos no patamar sustentado (média das 3 execuções)**

| Cenário | CPU média (% de 1 núcleo) | RAM média (MiB) | RAM pico (MiB) |
|---|---|---|---|
| A – CI4 + PHP-FPM (app + Nginx) | 92,1 ± 0,1 | 48,9 ± 10,3 | 50,1 |
| B – CI4 + FrankenPHP clássico | 89,0 ± 0,3 | 104,2 ± 2,2 | 114,6 |
| C – CI4 + FrankenPHP Worker | 100,6 ± 0,1 | 142,9 ± 0,4 | 197,4 |
| D – Laravel Octane | 100,5 ± 0,1 | 98,5 ± 6,2 | 104,3 |

Fonte: elaborado pelo autor (2026), a partir de amostras de `docker stats` a cada cerca de 7 s. Nota: no cenário A, soma de PHP-FPM e Nginx.

![Figura 3](figuras/fig_recursos.png)

**Figura 3 – CPU e RAM médias por cenário.** Fonte: elaborado pelo autor (2026).

Em todos os cenários a CPU ficou próxima do limite de 1,0 núcleo (89% a 101%), confirmando a saturação e que o gargalo do experimento é a CPU, e não a memória. Os cenários persistentes (C e D) chegaram a 100% de uso porque processaram mais requisições com a mesma CPU; ou seja, converteram o recurso em trabalho útil com mais eficiência, e não consumiram mais por requisição. O PHP-FPM foi o mais econômico em memória (49 MiB), custo esperado de manter a aplicação carregada em memória nos demais.

O comportamento da memória ao longo do tempo diferencia os cenários persistentes (Figuras 6 e 7). No Laravel Octane (D), a RAM se estabiliza em cerca de 100 MiB logo no início do patamar. No CodeIgniter 4 em modo Worker (C), a RAM cresce de forma contínua e aproximadamente linear durante toda a execução, de cerca de 45 MiB para cerca de 210 MiB ao final dos 15 minutos, sem formar patamar. Em testes mais longos, esse crescimento poderia atingir o limite de 512 MiB; ele indica acúmulo de memória entre requisições no processo persistente (por exemplo, objetos ou registros mantidos pelo *framework* ou pela aplicação), o que o presente experimento não investigou. A média de 143 MiB da Tabela 3 reflete, portanto, um valor que ainda crescia, e o pico (197 MiB) não é um teto.

### 4.5 Visão temporal nas execuções de captura

As Figuras 4 a 7 mostram o painel do Grafana de cada cenário em uma execução de captura. Elas ilustram o comportamento no tempo: rampa de usuários virtuais, patamar estável de vazão e latência, CPU constante no teto e erro em 0%. O painel de vazão exibe uma curva por endpoint (a soma delas corresponde à vazão total da Tabela 1).

![Figura 4](figuras/grafana-a.png)

**Figura 4 – Painel do Grafana, cenário A (execução de captura).** Fonte: elaborado pelo autor (2026).

![Figura 5](figuras/grafana-b.png)

**Figura 5 – Painel do Grafana, cenário B (execução de captura).** Fonte: elaborado pelo autor (2026).

![Figura 6](figuras/grafana-c.png)

**Figura 6 – Painel do Grafana, cenário C (execução de captura).** Fonte: elaborado pelo autor (2026).

![Figura 7](figuras/grafana-d.png)

**Figura 7 – Painel do Grafana, cenário D (execução de captura).** Nota: a linha amarela curta no início do painel de RAM é uma série de instância anterior do contêiner. Fonte: elaborado pelo autor (2026).

### 4.6 Discussão

**Persistência do processo reduz o custo de inicialização.** O resultado mais forte do estudo é que manter o processo e o *framework* carregados em memória mais que dobrou a vazão do CodeIgniter 4 (C em relação a A, +127,7%) com os mesmos recursos, mesmo sem preservar estado de aplicação nem conexão com o banco (Quadro 1). Isso é coerente com a motivação do trabalho: no modelo tradicional, a inicialização do framework se repete a cada requisição, e o modo Worker do FrankenPHP elimina essa repetição ao manter o processo vivo (FRANKENPHP, 2026). Resultado semelhante em direção, ainda que em outro contexto, é relatado por Luz, Silva e Emer (2025), que encontraram vantagem estatisticamente significativa do modelo assíncrono do Swoole sobre o PHP síncrono tradicional em testes de carga, e por Azzahidi, Wijayanto e Darmawan (2025), que incluíram Laravel com FrankenPHP entre os *frameworks* avaliados e o destacaram pelo uso eficiente de memória. Nossos resultados complementam esses estudos ao isolar o efeito do servidor (B) do efeito do modo Worker (C) em um mesmo *framework*.

**Trocar apenas o servidor não basta.** O FrankenPHP em modo clássico (B) não superou o PHP-FPM (A): ficou 13,4% abaixo. Esse resultado diverge da expectativa inicial, de que o modo clássico, por ser "substituto direto" do PHP-FPM, seria no mínimo equivalente (FRANKENPHP, 2026). Ele reforça a importância do desenho com o cenário B: sem ele, o ganho do cenário C poderia ser atribuído erroneamente ao FrankenPHP em si, quando decorre do modo Worker. Neste experimento não investigamos a causa da diferença entre A e B; hipóteses plausíveis, que exigiriam testes próprios, são o uso de PHP *thread-safe* (necessário ao FrankenPHP) em vez do modelo de processos do PHP-FPM e a contenção entre as *threads* do servidor sob a cota de 1 CPU. Note-se que, no cenário B, a CPU média ficou em 89%, abaixo dos demais, sinal de que parte da cota não foi aproveitada.

**O CodeIgniter 4 em Worker ficou atrás do Laravel Octane.** O Laravel Octane (D) superou o CodeIgniter 4 em modo Worker (C) em 28% de vazão (368,7 contra 287,7 RPS; C ficou 22% abaixo de D). Esse resultado também diverge da expectativa implícita no problema de pesquisa, de que o CodeIgniter, por ser mais leve, aproveitaria melhor o modo Worker. Três observações ajudam a interpretar: (i) o Octane é um pacote maduro, projetado para esse modelo de execução e já tratando limpeza de estado entre requisições, enquanto o suporte nativo do CodeIgniter ao modo Worker é recente (versão 4.7); (ii) como mostrou o Quadro 1, o Octane reaproveita a conexão com o PostgreSQL e preserva estado entre requisições, ao passo que o CodeIgniter 4 refaz a conexão a cada requisição; como 30% da carga é o endpoint `/db`, isso é uma explicação plausível para parte da diferença, embora a saturação da fila (Seção 4.3) impeça medir esse efeito isoladamente; e (iii) o cenário C apresentou crescimento contínuo de memória, ao passo que o D se estabilizou. Não foi feito perfilamento do código, de modo que essas explicações permanecem hipóteses; o que os dados sustentam é a diferença de vazão e o comportamento da memória, não suas causas.

**Quanto a reprodutibilidade e benchmarking.** A decisão de repetir cada cenário três vezes, em ordem rotativa, e de reportar o desvio-padrão segue a recomendação da literatura de que benchmarks de software sofrem instabilidade e devem ser tratados com repetição e controle do ambiente (LAABER; BASMACI; SALZA, 2021), e a de que comparações de desempenho exigem condições idênticas de execução (ZHAN, 2022; BRUNST et al., 2022; JIA et al., 2013). O desvio-padrão baixo observado (no máximo 1,8% da média) indica que o ambiente conteinerizado, com limites estritos de CPU e memória, produziu medições estáveis.

### 4.7 Ameaças à validade e limitações

- **Hospedeiro único e injetor no mesmo hospedeiro:** o k6 rodou na mesma máquina que os servidores (em contêiner com 2,0 CPU), o que pode causar interferência, embora igual entre cenários. Outros processos do computador do autor consumiam memória durante as medições, e o cache do sistema operacional não pôde ser limpo entre execuções por falta de permissão administrativa.
- **Ordem das execuções:** as execuções seguiram ordem rotativa (A, B, C, D) por rodada, com exceção da repetição do cenário D na terceira rodada, refeita isoladamente após falha de rede no *build*.
- **Carga sintética e modelo fechado:** os endpoints são simples e a carga é de usuários virtuais sem tempo de espera, o que satura o servidor e torna a latência função da vazão (Seção 4.3). Os resultados não se estendem automaticamente a aplicações reais, com consultas mais complexas e uso de sessão.
- **Percentil 99 não analisado:** o resumo exportado pelo k6 não trouxe o p99; foram usados p50 e p95.
- **Causas não investigadas:** diferenças entre A e B e entre C e D foram interpretadas como hipóteses, sem perfilamento.
