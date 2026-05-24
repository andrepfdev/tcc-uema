<?php

namespace App\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Routing\Controller;
use Illuminate\Support\Facades\DB;

class BenchmarkController extends Controller
{
    private static int $counter = 0;

    public function health(): JsonResponse
    {
        return response()->json([
            'status'   => 'ok',
            'scenario' => env('SCENARIO_NAME', 'scenario-d'),
        ]);
    }

    public function compute(): JsonResponse
    {
        $size = (int) env('COMPUTE_SIZE', 1000);
        $data = [];

        for ($i = 0; $i < $size; $i++) {
            $data[] = [
                'id'    => $i + 1,
                'uuid'  => md5(uniqid((string) $i, true)),
                'value' => random_int(1, 999999),
                'label' => str_repeat('x', random_int(5, 20)),
            ];
        }

        return response()->json([
            'count'    => $size,
            'scenario' => env('SCENARIO_NAME', 'scenario-d'),
            'data'     => $data,
        ]);
    }

    public function memory(): JsonResponse
    {
        self::$counter++;

        return response()->json([
            'counter'  => self::$counter,
            'pid'      => getmypid(),
            'scenario' => env('SCENARIO_NAME', 'scenario-d'),
        ]);
    }

    public function db(): JsonResponse
    {
        $id = random_int(1, 10000);

        // pg_backend_pid() incluído na mesma query — sem round-trip extra.
        // Mesmo papel do endpoint /memory: prova persistência, mas agora
        // no nível da conexão PostgreSQL em vez do estado PHP em memória.
        $row = DB::selectOne(
            'SELECT id, name, value, pg_backend_pid() AS pg_pid FROM benchmark_items WHERE id = ?',
            [$id]
        );

        return response()->json([
            'item'     => $row,
            'php_pid'  => getmypid(),
            'scenario' => env('SCENARIO_NAME', 'scenario-d'),
        ]);
    }
}
