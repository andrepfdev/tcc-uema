<?php

// Define caminho raiz da aplicação
define('FCPATH', __DIR__ . DIRECTORY_SEPARATOR);

// Carrega o autoloader do Composer
require_once FCPATH . '../vendor/autoload.php';

// Inicializa e executa o CodeIgniter
$app = \Config\Services::codeigniter();
$app->initialize();
$app->run();
