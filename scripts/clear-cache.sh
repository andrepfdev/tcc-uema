#!/usr/bin/env bash
# ==============================================================================
# clear-cache.sh — Limpa o cache do sistema operacional entre benchmarks
#
# Por que isso é necessário:
#   O kernel Linux armazena em memória o page cache (conteúdo de arquivos lidos),
#   dentries (cache de diretórios) e inodes. Sem limpeza entre cenários, o 2º e 3º
#   testes se beneficiam de dados já cacheados pelo teste anterior, o que infla
#   artificialmente os resultados e compromete a validade da comparação.
#
# Impacto no benchmark:
#   - Page cache: arquivos PHP/vendor já carregados ficam na RAM do host
#   - Dentries/inodes: acesso ao filesystem é mais rápido após o 1º uso
#   - OPcache dentro do container NÃO é afetado (vive no espaço do processo PHP)
#
# Requisitos:
#   - Linux: sudo necessário para /proc/sys/vm/drop_caches
#   - macOS: sudo purge
#
# Para evitar prompt de senha no Linux, adicione ao sudoers:
#   seu_usuario ALL=(ALL) NOPASSWD: /usr/bin/tee /proc/sys/vm/drop_caches
# ==============================================================================

set -euo pipefail

OS="$(uname)"

echo "Limpando cache do sistema operacional (${OS})..."

if [[ "$OS" == "Linux" ]]; then
  # Garante que buffers de escrita pendentes sejam descarregados para disco
  sync

  if [[ -w /proc/sys/vm/drop_caches ]]; then
    echo 3 > /proc/sys/vm/drop_caches
    echo "Cache liberado diretamente (sem sudo)."
  else
    echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
    echo "Cache liberado via sudo."
  fi

  # Exibe memória disponível após limpeza
  echo ""
  echo "Memória após limpeza:"
  free -h

elif [[ "$OS" == "Darwin" ]]; then
  sudo purge
  echo "Cache do macOS liberado (purge)."

else
  echo "Sistema operacional não suportado: ${OS}"
  echo "Limpe o cache manualmente antes de cada cenário."
  exit 1
fi

echo ""
echo "Cache limpo. Aguardando 2s para o SO estabilizar..."
sleep 2
echo "Pronto."
