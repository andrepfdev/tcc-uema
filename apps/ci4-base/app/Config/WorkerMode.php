<?php

namespace Config;

use CodeIgniter\Config\WorkerMode as BaseWorkerMode;

class WorkerMode extends BaseWorkerMode
{
    /**
     * Serviços que sobrevivem entre requests.
     * Os não listados aqui são destruídos após cada request (state leakage prevention).
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
