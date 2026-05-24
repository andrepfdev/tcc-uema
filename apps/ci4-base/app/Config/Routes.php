<?php

use CodeIgniter\Router\RouteCollection;

/** @var RouteCollection $routes */
$routes->get('/', 'Home::index');
$routes->get('health',  'BenchmarkController::health');
$routes->get('compute', 'BenchmarkController::compute');
$routes->get('memory',  'BenchmarkController::memory');
