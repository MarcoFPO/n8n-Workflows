#!/usr/bin/env bash
# Deploy-Script für Egon2.
#
# Überträgt den Quellcode via tar-Pipe direkt in pct exec auf LXC 128 —
# KEIN Staging auf dem Proxmox-Host, KEINE LXC-Konfigfiles auf Proxmox.
# .env und systemd-Service-File bleiben auf dem LXC unberührt.
set -euo pipefail

PROXMOX_HOST="${PROXMOX_HOST:-root@10.1.1.100}"
LXC_ID="${LXC_ID:-128}"
LXC_USER="${LXC_USER:-egon2}"
REMOTE_PATH="${REMOTE_PATH:-/opt/egon2}"
LOCAL_PATH="$(dirname "$(realpath "$0")")/.."

echo "=== Egon2 Deploy auf LXC ${LXC_ID} ==="

echo ">>> tar-Pipe → LXC ${LXC_ID}:${REMOTE_PATH}/"
tar -czf - \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='data' \
  --exclude='backup' \
  --exclude='.claude' \
  -C "${LOCAL_PATH}" . \
| ssh "${PROXMOX_HOST}" \
    "pct exec ${LXC_ID} -- tar -xzf - -C ${REMOTE_PATH}"

ssh "${PROXMOX_HOST}" \
    "pct exec ${LXC_ID} -- chown -R ${LXC_USER}:${LXC_USER} ${REMOTE_PATH}"

echo ">>> uv sync auf LXC"
ssh "${PROXMOX_HOST}" \
    "pct exec ${LXC_ID} -- bash -c 'cd ${REMOTE_PATH} && /usr/local/bin/uv sync --python python3 2>&1 | tail -10'"

echo ">>> systemctl restart egon2"
ssh "${PROXMOX_HOST}" "pct exec ${LXC_ID} -- systemctl daemon-reload"
ssh "${PROXMOX_HOST}" \
    "pct exec ${LXC_ID} -- systemctl restart egon2 || pct exec ${LXC_ID} -- systemctl start egon2"
sleep 2
ssh "${PROXMOX_HOST}" \
    "pct exec ${LXC_ID} -- systemctl status egon2 --no-pager -l | head -25"

echo "=== Deploy fertig ==="
