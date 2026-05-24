<?php

use App\Http\Controllers\BenchmarkController;
use Illuminate\Support\Facades\Route;

Route::get('/health',  [BenchmarkController::class, 'health']);
Route::get('/compute', [BenchmarkController::class, 'compute']);
Route::get('/memory',  [BenchmarkController::class, 'memory']);
