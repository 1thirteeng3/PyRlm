#!/bin/bash
# Script utilitário para instalação automatizada do gVisor (runsc) em Ubuntu/Debian
# Requer sudo.

set -e

echo "[INFO] Iniciando instalação do gVisor (runsc)..."

# 1. Configurar URL da arquitetura
ARCH=$(uname -m)
URL="https://storage.googleapis.com/gvisor/releases/release/latest/${ARCH}"

# 2. Baixar binário e checksum
wget ${URL}/runsc ${URL}/runsc.sha512 \
    ${URL}/containerd-shim-runsc-v1 ${URL}/containerd-shim-runsc-v1.sha512

# 3. Verificar integridade
sha512sum -c runsc.sha512 \
    -c containerd-shim-runsc-v1.sha512

# 4. Remover checksums e instalar binários
rm -f *.sha512
chmod a+rx runsc containerd-shim-runsc-v1
sudo mv runsc containerd-shim-runsc-v1 /usr/local/bin

echo "[INFO] Binários instalados em /usr/local/bin."

# 5. Configurar Docker Daemon
echo "[INFO] Configurando Docker para usar runsc..."
sudo /usr/local/bin/runsc install

# 6. Reload do Docker
sudo systemctl reload docker

echo "[SUCCESS] gVisor instalado! Testando..."
docker run --rm --runtime=runsc hello-world

echo "[DONE] O RLM-Python agora pode usar 'runtime=runsc'."