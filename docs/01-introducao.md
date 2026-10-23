## 1 INTRODUÇÃO

A evolução constante das tecnologias web tem exigido que sistemas modernos ofereçam alta escalabilidade e baixo tempo de resposta, forçando desenvolvedores a tomarem decisões estratégicas sobre a arquitetura de execução. Historicamente, a linguagem PHP dominou o cenário do desenvolvimento *server-side* operando no modelo *Request-Response-Die*, no qual o interpretador é iniciado, o *script* executado e todos os recursos destruídos ao final de cada requisição HTTP. Embora o PHP-FPM tenha trazido avanços ao manter processos persistentes, ele ainda opera de forma sequencial e bloqueante, o que gera um *overhead* de *bootstrapping* (inicialização do *framework*) que se repete a cada acesso, limitando o desempenho em cenários de alta carga.

A justificativa para a realização deste *benchmark* reside na necessidade de validar a transição desse modelo tradicional para o paradigma de memória persistente por meio de servidores de aplicação modernos. O surgimento de tecnologias como o Swoole e o FrankenPHP permitiu que o PHP funcionasse com laços de eventos persistentes, mantendo a aplicação carregada na memória RAM e reduzindo a inicialização. O ecossistema Laravel, por meio do Laravel Octane, já consolidou essa prática como padrão de mercado para alto desempenho, tratando nativamente a limpeza de estado e a injeção de dependências. Ainda assim, estudos que comparam a arquitetura tradicional (PHP-FPM com servidor web separado) com a integrada (FrankenPHP) são escassos: a literatura concentra-se na otimização no nível da aplicação ou do *framework*, e os estudos sobre a camada do servidor de aplicação são limitados (DHANISWARA; KUSUMASARI; ALAM, 2025).

Entretanto, o *framework* CodeIgniter 4 (CI4), embora amplamente utilizado pela sua leveza e simplicidade, passou a oferecer suporte nativo ao modo Worker do FrankenPHP apenas a partir da versão 4.7. Até então era possível utilizar o modo clássico, mas sem o mesmo desempenho. Para a comunidade de desenvolvimento web, é relevante compreender se adotar o modo Worker no CI4 justifica os ganhos de vazão (RPS) e latência, ou se o uso do FrankenPHP em seu modo clássico já seria suficiente para superar o legado do PHP-FPM.

A relevância deste estudo é multifacetada:

a) eficiência de recursos: em infraestrutura em nuvem, onde o consumo de CPU e RAM impacta diretamente os custos operacionais, validar arquiteturas que otimizam o uso do *hardware* é uma prioridade estratégica;

b) modernização de sistemas legados: muitos sistemas baseados em CodeIgniter precisam escalar sem reescrita completa para outros *frameworks* ou linguagens;

c) adoção de novas ferramentas: o FrankenPHP é uma tecnologia recente que integra o PHP a um servidor escrito em Go, e este estudo fornece dados empíricos sobre seu desempenho em diferentes modos de operação.

### 1.1 Problema de pesquisa

Em que medida a execução persistente em memória do FrankenPHP (modo Worker) altera a vazão, a latência e o consumo de recursos do CodeIgniter 4, em comparação com o PHP-FPM e com o FrankenPHP em modo clássico, tendo o Laravel Octane como referência?

### 1.2 Objetivo geral

Comparar o desempenho do CodeIgniter 4 sob PHP-FPM, FrankenPHP em modo clássico e FrankenPHP em modo Worker, utilizando o Laravel Octane como referência, sob carga controlada e com o mesmo orçamento de recursos.

### 1.3 Objetivos específicos

a) montar um ambiente experimental conteinerizado, reprodutível, com limites idênticos de CPU e memória para os quatro cenários;

b) medir e comparar vazão (requisições por segundo) e latência (p50 e p95) dos cenários sob carga crescente e sustentada;

c) avaliar o consumo de CPU e memória de cada cenário durante o teste;

d) verificar quais elementos (estado da aplicação e conexão com o banco) são efetivamente preservados entre requisições em cada arquitetura;

e) discutir se o ganho observado justifica a complexidade de adoção do modo Worker em aplicações CodeIgniter 4.
