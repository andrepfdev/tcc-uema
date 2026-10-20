## 4 RESULTADOS E DISCUSSÃO

Este capítulo apresenta os resultados obtidos nos cenários descritos na Metodologia e os interpreta à luz do referencial teórico. Os valores oficiais provêm de 15 execuções do teste de carga de 15 minutos (3 repetições de cada um dos cenários A, B, C, D e E) e de dois testes longos de 30 minutos de patamar (cenários C e D). As figuras extraídas do Grafana e do painel do k6 (Figuras 5 a 12) vêm de uma execução adicional de cada cenário, feita apenas para captura, e não entram nas médias.

### 4.1 Validação do ambiente e persistência de estado

Em todas as execuções válidas, as verificações (*checks*) do k6 passaram e a taxa de falhas HTTP foi de 0,00%, o que indica que as diferenças de desempenho adiante não decorrem de erros de aplicação.

Os endpoints `/memory` e `/db` revelam o que cada arquitetura realmente preserva entre requisições. O Quadro 1 resume as verificações feitas: cinco requisições sequenciais em cada cenário A, B e E, e 200 requisições sequenciais e 200 concorrentes nos cenários C e D, com 1 e com 4 *workers*.

**Quadro 1 – Estado preservado entre requisições, por cenário**

| Cenário | `/memory`: contador | `/db`: conexão PostgreSQL |
|---|---|---|
| A – CI4 + PHP-FPM | sempre 1; PID do processo varia (8, 10, 8, 10, 8) | nova a cada requisição (PIDs 40 a 44) |
| B e E – CI4 + FrankenPHP clássico | sempre 1; PID 1 | nova a cada requisição (PIDs 40 a 44) |
| C – CI4 + FrankenPHP Worker | cresce (2 a 201 em um *worker*); cada *worker* tem o seu contador | mantida: um único PID por *worker* (um *worker*: PID 70; quatro: PIDs 40, 48, 49 e 50) |
| D – Laravel Octane | cresce (2 a 201 em um *worker*); cada *worker* tem o seu contador | mantida: um único PID por *worker* |

Fonte: elaborado pelo autor (2026), a partir de `results/diagnostico`.

O Quadro 1 mostra que os dois cenários em modo Worker (C e D) preservam tanto o estado da aplicação quanto a conexão com o banco, ao passo que A, B e E reiniciam ambos a cada requisição. Com quatro *workers*, os pedidos concorrentes são distribuídos entre quatro processos persistentes, cada um com seu contador e sua conexão, de modo que o contador global não é compartilhado entre eles. No cenário D com quatro *workers*, o diagnóstico registrou cinco identificadores de *worker* e, com um *worker*, dois; o padrão (um *worker* encerrado após cerca de 500 requisições e substituído por outro) é coerente com o reciclo periódico de processos que o Laravel Octane faz por padrão, e não ocorreu no CodeIgniter 4. A diferença entre os dois comportamentos é relevante para a memória, tratada na Seção 4.5.

### 4.2 Vazão (requisições por segundo) e latência

A Tabela 1 e a Figura 1 apresentam a vazão média e o desvio-padrão das três execuções de cada cenário, sob 100 usuários virtuais simultâneos, em um orçamento de 1,0 CPU e 512 MB por cenário, e a latência global das requisições.

**Tabela 1 – Vazão e latência global por cenário (média das 3 execuções)**

| Cenário | RPS (média ± dp) | Latência p50 (ms) | Latência p95 (ms) | Latência p99 (ms) | Erros (%) |
|---|---|---|---|---|---|
| A – CI4 + PHP-FPM | 143,7 ± 0,5 | 687,4 | 785,6 | 800,5 | 0,00 |
| B – CI4 + FrankenPHP clássico | 156,1 ± 1,4 | 602,7 | 710,0 | 782,9 | 0,00 |
| E – CI4 + FrankenPHP clássico (*threads* padrão) | 175,5 ± 1,7 | 524,6 | 660,6 | 720,7 | 0,00 |
| C – CI4 + FrankenPHP Worker | 318,1 ± 6,1 | 300,2 | 394,1 | 405,7 | 0,00 |
| D – Laravel Octane | 351,3 ± 0,9 | 287,6 | 374,6 | 396,8 | 0,00 |

Fonte: elaborado pelo autor (2026), a partir dos resumos do k6. Nota: percentis calculados sobre toda a execução, incluindo as rampas.

![Figura 1](figuras/fig_rps.png)

**Figura 1 – Vazão média (RPS) por cenário, com desvio-padrão das 3 execuções.** Fonte: elaborado pelo autor (2026).

Em relação ao cenário A, o modo clássico do FrankenPHP (B) apresentou vazão 8,7% maior, o Worker com CodeIgniter 4 (C) apresentou vazão 121,4% maior (cerca de 2,2 vezes) e o Laravel Octane (D) apresentou vazão 144,5% maior (cerca de 2,4 vezes). Entre C e B, a diferença é de 103,7% a favor de C. A latência acompanha a vazão: o p95 do cenário C é 49,8% menor que o do A (394,1 contra 785,6 ms) e o p99, 49,3% menor (405,7 contra 800,5 ms). O desvio-padrão entre execuções do mesmo cenário ficou entre 0,3% e 1,9% da média, muito menor que as diferenças entre cenários, exceto entre C e D, discutida adiante.

A Tabela 2 reúne os testes estatísticos. A análise de variância (ANOVA) indicou diferença entre os cinco cenários na vazão (F = 3.311,6; p < 0,001), no p95 (F = 2.179,3; p < 0,001) e no p99 (F = 1.107,4; p < 0,001). Nos testes t de Welch par a par, com correção de Bonferroni para as seis comparações, as diferenças de vazão entre A, B, E e C permaneceram significativas ao nível de 5%; a diferença de vazão entre D e C teve p = 0,0098 sem correção e p ajustado = 0,059, ou seja, não é significativa após a correção. Como há apenas três execuções por cenário, o poder dos testes é limitado, e a diferença de 10,4% entre D e C deve ser lida como indicativa. O mesmo vale para o p99, em que B não difere de A (p ajustado = 0,97) e E difere de B apenas sem correção.

**Tabela 2 – Comparações par a par (testes t de Welch, n = 3)**

| Comparação | Vazão (%) | p ajust. | p95 (%) | p ajust. | p99 (%) | p ajust. |
|---|---|---|---|---|---|---|
| B contra A | +8,7 | 0,012 | −9,6 | 0,003 | −2,2 | 0,97 |
| E contra B | +12,4 | 0,001 | −7,0 | 0,099 | −7,9 | 0,070 |
| C contra A | +121,4 | 0,002 | −49,8 | < 0,001 | −49,3 | < 0,001 |
| C contra B | +103,7 | 0,002 | −44,5 | < 0,001 | −48,2 | 0,003 |
| C contra E | +81,3 | 0,002 | −40,3 | 0,006 | −43,7 | 0,007 |
| D contra C | +10,4 | 0,059 | −4,9 | < 0,001 | −2,2 | 0,019 |

Fonte: elaborado pelo autor (2026), com `scripts/analyze.py`. Nota: variações percentuais da média do primeiro cenário em relação ao segundo; p ajustado pelo método de Bonferroni.

### 4.3 Latência por endpoint

A Tabela 3 e a Figura 2 detalham a latência média e o percentil 95 por endpoint.

**Tabela 3 – Latência por endpoint (média / p95, em ms)**

| Cenário | /health | /compute | /memory | /db |
|---|---|---|---|---|
| A – CI4 + PHP-FPM | 529,0 / 775,2 | 536,8 / 781,0 | 527,8 / 775,6 | 565,3 / 794,5 |
| B – CI4 + FrankenPHP clássico | 482,2 / 697,3 | 492,1 / 700,9 | 484,2 / 697,3 | 525,4 / 754,5 |
| E – CI4 + FrankenPHP clássico (*threads* padrão) | 436,8 / 648,9 | 439,9 / 652,9 | 436,5 / 648,9 | 456,9 / 674,9 |
| C – CI4 + FrankenPHP Worker | 241,3 / 392,0 | 251,1 / 397,1 | 241,3 / 392,1 | 242,2 / 392,7 |
| D – Laravel Octane | 217,5 / 331,1 | 228,1 / 382,7 | 217,2 / 328,7 | 219,7 / 367,4 |

Fonte: elaborado pelo autor (2026).

![Figura 2](figuras/fig_latencia_p95.png)

**Figura 2 – Latência p95 por endpoint e cenário.** Fonte: elaborado pelo autor (2026).

Um achado importante é que a latência é praticamente a mesma nos quatro endpoints dentro de cada cenário, embora o `/health` não faça processamento e o `/compute` gere e serialize mil registros. A explicação é a forma de carga: o k6 mantém 100 usuários virtuais disparando requisições continuamente, sem tempo de espera entre elas, e o servidor, limitado a 1 CPU, está saturado (Seção 4.4). Nessa condição, o tempo de resposta é dominado pelo tempo de fila e, pela Lei de Little (LITTLE, 1961), a latência média em um sistema fechado aproxima-se de usuários ÷ vazão. A conta confere: 100 ÷ 143,7 ≈ 696 ms no cenário A (p50 medido: 687 ms), 100 ÷ 318,1 ≈ 314 ms no cenário C (300 ms) e 100 ÷ 351,3 ≈ 285 ms no cenário D (288 ms). Consequentemente, a latência aqui é um espelho da vazão, e não uma medida independente do custo de cada endpoint. A diferença entre `/db` e `/health` é pequena em todos os cenários: 36 ms no cenário A, 43 ms no B, 20 ms no E, 1 ms no C e 2 ms no D. Ela é maior nos cenários que abrem uma nova conexão a cada requisição (A, B, E) do que nos que a reaproveitam (C e D), o que é coerente com o Quadro 1, mas o desenho do experimento não isola o custo de cada endpoint com precisão. Para isso seria necessária carga com taxa de chegada fixa (modelo aberto), tema indicado nos trabalhos futuros.

### 4.4 Consumo de CPU e memória

**Tabela 4 – Consumo de recursos no patamar sustentado (média das 3 execuções)**

| Cenário | CPU média (% de 1 núcleo) | RAM média (MiB) | RAM pico (MiB) |
|---|---|---|---|
| A – CI4 + PHP-FPM (app + Nginx) | 92,7 ± 0,1 | 79,2 ± 0,0 | 80,6 |
| B – CI4 + FrankenPHP clássico | 100,2 ± 0,4 | 123,9 ± 0,2 | 124,9 |
| E – CI4 + FrankenPHP clássico (*threads* padrão) | 98,0 ± 1,7 | 119,7 ± 0,4 | 120,8 |
| C – CI4 + FrankenPHP Worker | 100,4 ± 0,4 | 125,4 ± 0,5 | 127,4 |
| D – Laravel Octane | 100,6 ± 0,0 | 171,6 ± 0,4 | 172,9 |

Fonte: elaborado pelo autor (2026), a partir de amostras de `docker stats`. Nota: no cenário A, soma de PHP-FPM e Nginx.

![Figura 3](figuras/fig_recursos.png)

**Figura 3 – CPU e RAM médias por cenário.** Fonte: elaborado pelo autor (2026).

Em todos os cenários a CPU ficou próxima do limite de 1,0 núcleo (92,7% a 100,6%), confirmando a saturação e que o gargalo do experimento é a CPU, e não a memória: nenhum cenário passou de 173 MiB, contra o limite de 512 MiB. Os cenários persistentes (C e D) usaram a mesma CPU que B e processaram mais requisições; ou seja, converteram o recurso em trabalho útil com mais eficiência, e não consumiram mais por requisição. O cenário A foi o único abaixo de 100%, o que pode refletir a divisão da cota entre PHP-FPM (0,85 CPU) e Nginx (0,15 CPU): como cada contêiner tem seu próprio limite, a capacidade ociosa de um não pode ser usada pelo outro. O PHP-FPM foi o mais econômico em memória (79 MiB), custo esperado de manter a aplicação carregada em memória nos demais: o CodeIgniter 4 em modo Worker usou 125 MiB (+46 MiB em relação ao A) e o Laravel Octane, 172 MiB.

### 4.5 Estabilidade da memória nos testes longos

Para verificar se a memória dos cenários persistentes cresce com o tempo, os cenários C e D foram executados com patamar de 30 minutos. A Tabela 5 e a Figura 4 mostram o resultado.

**Tabela 5 – Testes longos (patamar de 30 minutos) nos cenários C e D**

| Cenário | RPS | p95 (ms) | p99 (ms) | RAM nos 5 min iniciais (MiB) | RAM nos 5 min finais (MiB) | RAM pico (MiB) |
|---|---|---|---|---|---|---|
| C – CI4 + FrankenPHP Worker | 310,1 | 396,1 | 406,7 | 125,8 | 126,0 | 127,0 |
| D – Laravel Octane | 346,8 | 376,5 | 397,0 | 171,3 | 171,8 | 174,2 |

Fonte: elaborado pelo autor (2026), a partir dos testes longos e de `docker stats`.

![Figura 4](figuras/fig_ram_longo.png)

**Figura 4 – Memória dos contêineres C e D ao longo do patamar de 30 minutos.** Fonte: elaborado pelo autor (2026).

Nos dois cenários a memória se manteve estável durante os 30 minutos, com variação de menos de 1 MiB entre o início e o fim do patamar, e a vazão e a latência ficaram no mesmo nível das execuções de 15 minutos (vazão 2,5% menor no C e 1,3% menor no D). Portanto, não houve evidência de acúmulo de memória nem de degradação de desempenho no modo Worker nem no CodeIgniter 4 nem no Laravel Octane, o que é relevante para a adoção do modo Worker em produção, em que o risco de vazamento entre requisições é a principal contrapartida (DUNGLAS, 2024). A estabilidade em 30 minutos, com 4 *workers*, não garante o mesmo comportamento em períodos de horas ou com aplicações mais complexas.

### 4.6 Visão temporal nas execuções de captura

As Figuras 5 a 8 mostram o painel do Grafana, e as Figuras 9 a 12 o painel de resumo do k6, de cada cenário em uma execução de captura. Elas ilustram o comportamento no tempo: rampa de usuários virtuais, patamar estável de vazão e latência, CPU constante no teto e erro em 0%. No painel do k6, a vazão alta do início da execução corresponde à fase de poucos usuários virtuais, em que as requisições são atendidas sem fila, e cai ao patamar sustentado quando a carga chega a 100 usuários.

![Figura 5](figuras/grafana-a.png)

**Figura 5 – Painel do Grafana, cenário A (execução de captura).** Fonte: elaborado pelo autor (2026).

![Figura 6](figuras/grafana-b.png)

**Figura 6 – Painel do Grafana, cenário B (execução de captura).** Fonte: elaborado pelo autor (2026).

![Figura 7](figuras/grafana-c.png)

**Figura 7 – Painel do Grafana, cenário C (execução de captura).** Fonte: elaborado pelo autor (2026).

![Figura 8](figuras/grafana-d.png)

**Figura 8 – Painel do Grafana, cenário D (execução de captura).** Fonte: elaborado pelo autor (2026).

![Figura 9](figuras/k6-a.png)

**Figura 9 – Painel do k6, cenário A (execução de captura).** Fonte: elaborado pelo autor (2026).

![Figura 10](figuras/k6-b.png)

**Figura 10 – Painel do k6, cenário B (execução de captura).** Fonte: elaborado pelo autor (2026).

![Figura 11](figuras/k6-c.png)

**Figura 11 – Painel do k6, cenário C (execução de captura).** Fonte: elaborado pelo autor (2026).

![Figura 12](figuras/k6-d.png)

**Figura 12 – Painel do k6, cenário D (execução de captura).** Fonte: elaborado pelo autor (2026).

### 4.7 Discussão

**Persistência do processo reduz o custo de inicialização.** O resultado mais forte do estudo é que manter o processo e o *framework* carregados em memória mais que dobrou a vazão do CodeIgniter 4 (C em relação a A, +121,4%) e reduziu pela metade o p95 e o p99, com os mesmos recursos e sem perda de estabilidade (Seção 4.5). Isso é coerente com a motivação do trabalho: no modelo tradicional, a inicialização do *framework* se repete a cada requisição, e o modo Worker do FrankenPHP elimina essa repetição ao manter o processo vivo (DUNGLAS, 2024). O Quadro 1 mostra que, no CodeIgniter 4, o modo Worker preserva também a conexão com o banco e o estado da aplicação, de modo que o ganho decorre da soma da eliminação do *bootstrap* com o reaproveitamento da conexão; o experimento não separa as duas parcelas. Resultado semelhante em direção, ainda que em outro contexto, é relatado por Luz, Silva e Emer (2024), que encontraram vantagem estatisticamente significativa do modelo assíncrono do Swoole sobre o PHP síncrono tradicional em testes de carga, e por Azzahidi, Wijayanto e Darmawan (2025), que incluíram Laravel com FrankenPHP entre os *frameworks* avaliados e o destacaram pelo uso eficiente de memória. Nossos resultados complementam esses estudos ao isolar o efeito do servidor (B) do efeito do modo Worker (C) em um mesmo *framework*.

**Trocar apenas o servidor traz um ganho pequeno.** O FrankenPHP em modo clássico (B) superou o PHP-FPM (A) em 8,7% de vazão e 9,6% de p95, mas não no p99 (−2,2%, sem significância), e ficou 51% abaixo do cenário C. O cenário B é a comparação mais direta com o A, pois ambos reiniciam estado e conexão a cada requisição (Quadro 1). Sem o cenário B, o ganho do cenário C poderia ser atribuído erroneamente ao FrankenPHP em si, quando decorre sobretudo do modo Worker. Neste experimento não investigamos a causa do pequeno ganho de B sobre A; uma hipótese é que o FrankenPHP dispensa o salto FastCGI entre Nginx e PHP-FPM e a divisão da cota de CPU entre dois contêineres (Seção 4.4), compensada em parte pelo uso de PHP *thread-safe*. O cenário de sensibilidade E, com o número padrão de *threads* do servidor, elevou a vazão em 12,4% em relação ao B, o que mostra que o resultado do modo clássico depende dessa configuração: mesmo assim, E ficou 45% abaixo do cenário C em vazão. A conclusão de que o modo Worker é o que determina o ganho vale, portanto, para as duas configurações do modo clássico.

**O CodeIgniter 4 em Worker ficou próximo do Laravel Octane, atrás dele.** O Laravel Octane (D) superou o CodeIgniter 4 em modo Worker (C) em 10,4% de vazão (351,3 contra 318,1 RPS) e 4,9% de p95, diferença menor que a que separa qualquer cenário clássico do modo Worker e que não é significativa na vazão após a correção de Bonferroni (Tabela 2). O resultado diverge da expectativa implícita no problema de pesquisa, de que o CodeIgniter, por ser mais leve, aproveitaria melhor o modo Worker: ele ficou 9,5% abaixo do Octane, e com menos memória (125 contra 172 MiB, Tabela 4). Duas observações ajudam a interpretar: (i) o Octane é um pacote maduro, projetado para esse modelo de execução e que já trata a limpeza de estado entre requisições (OTWELL, 2024), enquanto o suporte nativo do CodeIgniter ao modo Worker é recente (CODEIGNITER FOUNDATION, 2024); e (ii) o diagnóstico mostrou que os dois preservam estado e conexão, de modo que a diferença remanescente não decorre da persistência da conexão. Não foi feito perfilamento do código, de modo que as causas permanecem hipóteses; o que os dados sustentam é a diferença de vazão, o comportamento da memória e a equivalência de estado preservado.

**Quanto a reprodutibilidade e benchmarking.** A decisão de repetir cada cenário três vezes, em ordem rotativa, de manter a mesma base de sistema operacional em todos eles e de reportar o desvio-padrão segue a recomendação da literatura de que benchmarks de software sofrem instabilidade e devem ser tratados com repetição e controle do ambiente (LAABER; BASMACI; SALZA, 2021), e a de que comparações de desempenho exigem condições idênticas de execução (ZHAN, 2022; BRUNST et al., 2022; JIA et al., 2013). O desvio-padrão baixo observado (no máximo 1,9% da média) indica que o ambiente conteinerizado, com limites estritos de CPU e memória, produziu medições estáveis.

### 4.8 Ameaças à validade e limitações

- **Hospedeiro único e injetor no mesmo hospedeiro:** o k6 rodou na mesma máquina que os servidores (em contêiner com 2,0 CPU), o que pode causar interferência, embora igual entre cenários. Outros processos do computador do autor consumiam memória durante as medições.
- **Ordem das execuções:** os cenários A a D foram executados em ordem rotativa, mas o cenário E foi executado depois deles, e os testes longos por último; a temperatura do hospedeiro pode ter variado entre esses blocos.
- **Carga sintética e modelo fechado:** os endpoints são simples e a carga é de usuários virtuais sem tempo de espera, o que satura o servidor e torna a latência função da vazão (Seção 4.3). Os resultados não se estendem automaticamente a aplicações reais, com consultas mais complexas e uso de sessão.
- **Tamanho da amostra:** com três execuções por cenário, os testes estatísticos têm poder limitado, e a diferença entre C e D, de 10,4% na vazão, não resiste à correção de Bonferroni.
- **Compilação do PHP:** o PHP do FrankenPHP é *thread-safe* e o do PHP-FPM não é, diferença inerente às arquiteturas que o experimento não separa do efeito do servidor.
- **Infraestrutura de medição não fixada:** as imagens do Prometheus, do Grafana, do cAdvisor e do k6 usam a etiqueta `latest`, ao contrário das imagens dos cenários, fixadas por versão e por *digest*. Elas são idênticas entre cenários, mas não garantem a reprodução bit a bit.
- **Causas não investigadas:** diferenças entre A e B e entre C e D foram interpretadas como hipóteses, sem perfilamento.
