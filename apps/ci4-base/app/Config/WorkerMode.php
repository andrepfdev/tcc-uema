<?php

namespace Config;

use CodeIgniter\Config\WorkerMode as BaseWorkerMode;

class WorkerMode extends BaseWorkerMode
{
    /**
     * Serviços que sobrevivem entre requests.
     * Os não listados aqui são destruídos após cada request (state leakage prevention).
     *
     * Nota sobre 'database': intencionalmente OMITIDO desta lista.
     * O service container é resetado por request (isolamento de estado),
     * mas a conexão PDO subjacente é gerenciada pelo DatabaseConfig separadamente
     * e persiste automaticamente entre requests no Worker Mode.
     * Isso significa: isolamento de transação por request + reuso de conexão TCP.
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
     * Event listeners a serem removidos entre requests.
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
