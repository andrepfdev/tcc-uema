-- Inicialização do banco de benchmark para o TCC UEMA
-- Executado automaticamente pelo PostgreSQL na primeira inicialização do container

CREATE TABLE IF NOT EXISTS benchmark_items (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    value       INTEGER      NOT NULL,
    description TEXT         NOT NULL
);

-- Popula 10.000 registros para simular uma tabela real
-- generate_series garante dados determinísticos e reprodutíveis
INSERT INTO benchmark_items (name, value, description)
SELECT
    'item_' || gs,
    (random() * 100000)::INTEGER,
    'Descrição do item número ' || gs || ' gerada para benchmark de persistência em memória TCC UEMA'
FROM generate_series(1, 10000) AS gs;

-- Atualiza estatísticas do planner para queries por PK sejam otimizadas
ANALYZE benchmark_items;
