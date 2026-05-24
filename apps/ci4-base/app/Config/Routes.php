<?php

/** @var \CodeIgniter\Router\RouteCollection $routes */
$routes->get('/', 'Home::index');
$routes->get('health',  'BenchmarkController::health');
$routes->get('compute', 'BenchmarkController::compute');
$routes->get('memory',  'BenchmarkController::memory');
$routes->get('db',      'BenchmarkController::db');
