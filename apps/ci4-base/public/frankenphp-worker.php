<?php

/**
 * CodeIgniter 4 — FrankenPHP Worker Mode Entry Point
 *
 * Gerado via: php spark worker:install (CI4 >= 4.7.0)
 * Ref: https://codeigniter.com/user_guide/installation/worker_mode.html
 *
 * O framework faz bootstrap uma única vez e mantém o processo vivo entre
 * requests, eliminando o custo de inicialização a cada requisição.
 */

use CodeIgniter\Boot;
use CodeIgniter\Config\Factories;
use CodeIgniter\Config\Services;
use CodeIgniter\Database\Config as DatabaseConfig;
use CodeIgniter\Events\Events;
use Config\Paths;
use Config\WorkerMode;

// Versão mínima exigida pelo CI4 Worker Mode
$minPhpVersion = '8.2';
if (version_compare(PHP_VERSION, $minPhpVersion, '<')) {
    http_response_code(503);
    exit("PHP {$minPhpVersion}+ required. Current: " . PHP_VERSION);
}

if (! defined('FCPATH')) {
    define('FCPATH', __DIR__ . DIRECTORY_SEPARATOR);
}

if (getcwd() . DIRECTORY_SEPARATOR !== FCPATH) {
    chdir(FCPATH);
}

// === BOOTSTRAP (executa UMA vez por processo worker) ===
require_once FCPATH . '../app/Config/Paths.php';
$paths = new Paths();

require_once $paths->systemDirectory . '/Boot.php';

$app = Boot::bootWorker($paths);

ignore_user_abort(true);

/** @var WorkerMode $workerConfig */
$workerConfig = config('WorkerMode');

// === HANDLER (executa para cada request) ===
$handler = static function () use ($app, $workerConfig) {
    // Reconecta DB e Cache se necessário (conexões persistem entre requests)
    DatabaseConfig::reconnectForWorkerMode();
    Services::reconnectCacheForWorkerMode();

    // Reseta estado específico da requisição (request/response objects)
    $app->resetForWorkerMode();

    // Injeta superglobais da requisição atual do FrankenPHP
    service('superglobals')
        ->setServerArray($_SERVER)
        ->setGetArray($_GET)
        ->setPostArray($_POST)
        ->setCookieArray($_COOKIE)
        ->setFilesArray($_FILES)
        ->setRequestArray($_REQUEST);

    try {
        $app->run();
    } catch (Throwable $e) {
        Services::exceptions()->exceptionHandler($e);
    }

    if ($workerConfig->forceGarbageCollection) {
        gc_collect_cycles();
    }
};

// === LOOP (mantém o processo vivo) ===
while (frankenphp_handle_request($handler)) {
    // Fecha sessão da requisição processada
    if (Services::has('session')) {
        Services::session()->close();
    }

    // Limpa transações DB não comitadas
    DatabaseConfig::cleanupForWorkerMode();

    // Reseta Factories (Models, Config instances) — state leakage prevention
    Factories::reset();

    // Reseta Services exceto os persistentes ($persistentServices em WorkerMode.php)
    Services::resetForWorkerMode($workerConfig);

    // Limpa event listeners acumulados
    Events::cleanupForWorkerMode($workerConfig->resetEventListeners);

    if (CI_DEBUG) {
        Services::toolbar()->reset();
    }
}
