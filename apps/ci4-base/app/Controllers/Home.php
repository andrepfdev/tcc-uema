<?php

namespace App\Controllers;

class Home extends BaseController
{
    public function index(): string
    {
        return 'CI4 Benchmark - TCC UEMA | Endpoints: /health /compute /memory';
    }
}
