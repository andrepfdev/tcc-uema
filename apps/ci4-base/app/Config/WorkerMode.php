<?php

namespace Config;

/**
 * WorkerMode — Configuração do FrankenPHP Worker Mode para CI4 4.7+
 *
 * Substitui a classe padrão do framework (vendor/codeigniter4/framework/app/Config/WorkerMode.php).
 * CI4 usa a versão do app/ quando ela existe.
 *
 * Nota sobre 'database': intencionalmente OMITIDO de $persistentServices.
 * O service container é resetado por request (isolamento de estado),
 * mas a conexão PDO é gerenciada pelo DatabaseConfig separadamente
 * e persiste automaticamente no Worker Mode (conexão TCP reutilizada,
 * mas transações isoladas por request).
 */
class WorkerMode
{
    /**
     * Serviços que sobrevivem entre requests.
     * Os não listados são destruídos após cada request (state leakage prevention).
     *
     * @var list<string>
     */
    public array $persistentServices = [
        'autoloader',
        'locator',
        'exceptions',
        'commands',
        'codeigniter',
        'superglobals',
        'routes',
        'cache',
    ];

    /**
     * Event listeners a remover entre requests.
     * Necessário apenas quando listeners são registrados dentro de callbacks de outros eventos.
     *
     * @var list<string>
     */
    public array $resetEventListeners = [];

    /**
     * Força garbage collection após cada request.
     * Recomendado: true — previne vazamento de memória no processo persistente.
     */
    public bool $forceGarbageCollection = true;
}
