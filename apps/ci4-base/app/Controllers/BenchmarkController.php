<?php

namespace App\Controllers;

use CodeIgniter\Controller;

class BenchmarkController extends Controller
{
    public function health(): void
    {
        $this->response->setHeader('Content-Type', 'application/json');
        echo json_encode([
            'status'   => 'ok',
            'scenario' => getenv('SCENARIO_NAME') ?: 'unknown',
        ]);
    }

    public function compute(): void
    {
        $size = (int) (getenv('COMPUTE_SIZE') ?: 1000);
        $data = [];

        for ($i = 0; $i < $size; $i++) {
            $data[] = [
                'id'    => $i + 1,
                'uuid'  => md5(uniqid((string) $i, true)),
                'value' => random_int(1, 999999),
                'label' => str_repeat('x', random_int(5, 20)),
            ];
        }

        $this->response->setHeader('Content-Type', 'application/json');
        echo json_encode([
            'count'    => $size,
            'scenario' => getenv('SCENARIO_NAME') ?: 'unknown',
            'data'     => $data,
        ]);
    }

    public function memory(): void
    {
        // Propriedade estática sobrevive ao loop do Worker Mode (mesma instância PHP)
        // Em PHP-FPM/Classic: reinicia a cada request (processo novo ou sem estado persistente)
        MemoryState::$counter++;

        $this->response->setHeader('Content-Type', 'application/json');
        echo json_encode([
            'counter'  => MemoryState::$counter,
            'pid'      => getmypid(),
            'scenario' => getenv('SCENARIO_NAME') ?: 'unknown',
        ]);
    }

    public function db(): void
    {
        // Seleciona um registro aleatório para evitar cache do query planner
        // e forçar o acesso real à conexão com o banco
        $id = random_int(1, 10000);

        $row = db_connect()
            ->table('benchmark_items')
            ->select('id, name, value')
            ->where('id', $id)
            ->get()
            ->getRow();

        $this->response->setHeader('Content-Type', 'application/json');
        echo json_encode([
            'item'     => $row,
            'scenario' => getenv('SCENARIO_NAME') ?: 'unknown',
            // Inclui o PID para confirmar se a conexão é do mesmo processo (Worker Mode)
            'pid'      => getmypid(),
        ]);
    }
}

class MemoryState
{
    public static int $counter = 0;
}
