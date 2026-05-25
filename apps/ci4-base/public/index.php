<?php

// Mínimo de versão PHP
$minPhpVersion = '8.1';
if (version_compare(PHP_VERSION, $minPhpVersion, '<')) {
    exit(sprintf(
        'Your PHP version must be %s or higher. Current version: %s',
        $minPhpVersion,
        PHP_VERSION
    ));
}

define('FCPATH', __DIR__ . DIRECTORY_SEPARATOR);

if (getcwd() . DIRECTORY_SEPARATOR !== FCPATH) {
    chdir(dirname(__FILE__));
}

// Entry point do CI4 4.7 — Boot::bootWeb() carrega o framework
require FCPATH . '../app/Config/Paths.php';
$paths = new Config\Paths();

require $paths->systemDirectory . '/Boot.php';

exit(CodeIgniter\Boot::bootWeb($paths));
