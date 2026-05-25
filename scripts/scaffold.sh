#!/usr/bin/env bash
# ==============================================================================
# scaffold.sh — Monta o scaffold completo dos apps via Docker (sem PHP local)
#
# Uso (única vez, antes do primeiro build):
#   ./scripts/scaffold.sh
#
# O que faz:
#   1. Scaffold CI4 4.7 + overlay dos arquivos customizados do TCC
#   2. Scaffold Laravel 13 + overlay + instala laravel/octane
#
# Após rodar, apps/ci4-base/ e apps/laravel-octane/ ficam completos.
# O vendor/ gerado pode ficar local (não sobe ao git — ver .gitignore).
# No docker build, o composer install roda dentro da imagem.
# ==============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSER_IMAGE="composer:2"

echo "======================================================================"
echo " TCC UEMA — Scaffold de aplicações (Docker-only, sem PHP no host)"
echo "======================================================================"

# ---------------------------------------------------------------------------
# CI4 4.7
# ---------------------------------------------------------------------------
echo ""
echo "[1/2] Scaffold CodeIgniter 4.7..."

CI4_DIR="${ROOT}/apps/ci4-base"

# Salva os arquivos customizados do TCC
TMP_CUSTOM=$(mktemp -d)
trap "rm -rf '${TMP_CUSTOM}'" EXIT

cp -r "${CI4_DIR}/app"    "${TMP_CUSTOM}/"
cp -r "${CI4_DIR}/public" "${TMP_CUSTOM}/"
cp    "${CI4_DIR}/.env"   "${TMP_CUSTOM}/.env"
cp    "${CI4_DIR}/composer.json" "${TMP_CUSTOM}/composer.json"

# Scaffold completo em diretório temporário
TMP_CI4=$(mktemp -d)
trap "rm -rf '${TMP_CUSTOM}' '${TMP_CI4}'" EXIT

docker run --rm \
  -v "${TMP_CI4}:/output" \
  "${COMPOSER_IMAGE}" \
  composer create-project codeigniter4/appstarter /output \
    --no-interaction \
    --prefer-dist \
    --no-scripts

# Substitui o diretório do TCC pelo scaffold completo
rm -rf "${CI4_DIR}"
mv "${TMP_CI4}" "${CI4_DIR}"

# Re-aplica os customizados por cima (sobrescreve o que o scaffold gerou)
cp -r "${TMP_CUSTOM}/app"    "${CI4_DIR}/"
cp -r "${TMP_CUSTOM}/public" "${CI4_DIR}/"
cp    "${TMP_CUSTOM}/.env"   "${CI4_DIR}/.env"
cp    "${TMP_CUSTOM}/composer.json" "${CI4_DIR}/composer.json"

# composer.lock agora existe do scaffold; roda install para atualizar ao nosso composer.json
docker run --rm \
  -v "${CI4_DIR}:/app" \
  -w /app \
  "${COMPOSER_IMAGE}" \
  composer update --no-dev --optimize-autoloader --no-interaction

echo "   CI4 pronto em apps/ci4-base/"

# ---------------------------------------------------------------------------
# Laravel 13 + Octane
# ---------------------------------------------------------------------------
echo ""
echo "[2/2] Scaffold Laravel 13 + Octane..."

LARAVEL_DIR="${ROOT}/apps/laravel-octane"

# Salva customizados
TMP_LARAVEL_CUSTOM=$(mktemp -d)
trap "rm -rf '${TMP_CUSTOM}' '${TMP_CI4}' '${TMP_LARAVEL_CUSTOM}'" EXIT

cp -r "${LARAVEL_DIR}/app"    "${TMP_LARAVEL_CUSTOM}/"
cp -r "${LARAVEL_DIR}/routes" "${TMP_LARAVEL_CUSTOM}/"
cp    "${LARAVEL_DIR}/.env"   "${TMP_LARAVEL_CUSTOM}/.env"
cp    "${LARAVEL_DIR}/composer.json" "${TMP_LARAVEL_CUSTOM}/composer.json"

# Scaffold completo
TMP_LARAVEL=$(mktemp -d)
trap "rm -rf '${TMP_CUSTOM}' '${TMP_CI4}' '${TMP_LARAVEL_CUSTOM}' '${TMP_LARAVEL}'" EXIT

docker run --rm \
  -v "${TMP_LARAVEL}:/output" \
  "${COMPOSER_IMAGE}" \
  composer create-project laravel/laravel /output \
    --no-interaction \
    --prefer-dist \
    --no-scripts

# Substitui pelo scaffold
rm -rf "${LARAVEL_DIR}"
mv "${TMP_LARAVEL}" "${LARAVEL_DIR}"

# Re-aplica customizados
cp -r "${TMP_LARAVEL_CUSTOM}/app"    "${LARAVEL_DIR}/"
cp -r "${TMP_LARAVEL_CUSTOM}/routes" "${LARAVEL_DIR}/"
cp    "${TMP_LARAVEL_CUSTOM}/.env"   "${LARAVEL_DIR}/.env"
cp    "${TMP_LARAVEL_CUSTOM}/composer.json" "${LARAVEL_DIR}/composer.json"

# Instala laravel/octane e atualiza o lock
docker run --rm \
  -v "${LARAVEL_DIR}:/app" \
  -w /app \
  "${COMPOSER_IMAGE}" \
  composer require "laravel/octane:^2.5" --no-interaction

docker run --rm \
  -v "${LARAVEL_DIR}:/app" \
  -w /app \
  "${COMPOSER_IMAGE}" \
  composer install --no-dev --optimize-autoloader --no-interaction

echo "   Laravel pronto em apps/laravel-octane/"

echo ""
echo "======================================================================"
echo " Scaffold concluído!"
echo ""
echo " Próximos passos:"
echo "   ./scripts/run-scenario.sh a smoke   # Cenário A — sanidade"
echo "   ./scripts/run-scenario.sh a load    # Cenário A — carga"
echo "======================================================================"
