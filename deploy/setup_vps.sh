#!/usr/bin/env bash
# Secondary Linux deployment for the canonical OFFLINE stack.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "${EUID}" -eq 0 ]]; then
  echo "Run this installer as the dedicated non-root service user." >&2
  exit 1
fi

sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv curl

if [[ ! -x venv/bin/python ]]; then
  python3 -m venv venv
fi
venv/bin/python -m pip install --upgrade pip
venv/bin/python -m pip install -r requirements.txt

venv/bin/python -B scripts/provision_trader_runtime.py --output .runtime/trader-stack.env
chmod 700 .runtime .runtime/logs .runtime/pids .runtime/backups
chmod 600 .runtime/trader-stack.env
venv/bin/python -B scripts/migrate_web_storage.py \
  --env-file .runtime/trader-stack.env \
  --evidence audit/deployment_remediation/evidence/credential_migration.json

SERVICE_USER="$(id -un)"
SERVICE_GROUP="$(id -gn)"
PYTHON="$ROOT/venv/bin/python"
SERVICE_FILE=/etc/systemd/system/trader-stack-offline.service

sudo tee "$SERVICE_FILE" >/dev/null <<EOF
[Unit]
Description=Trader Stack OFFLINE Supervisor
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$ROOT
Environment=PYTHONUNBUFFERED=1
ExecStart=$PYTHON -B scripts/trader_stack_supervisor.py --env-file $ROOT/.runtime/trader-stack.env
ExecStop=/usr/bin/touch $ROOT/.runtime/stop.request
Restart=on-failure
RestartSec=10
TimeoutStartSec=90
TimeoutStopSec=45
NoNewPrivileges=true
PrivateTmp=true
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now trader-stack-offline.service

echo "OFFLINE stack installed. Ports 50051 and 8088 bind to loopback only."
echo "No firewall rule was added; use a private Cloudflare Tunnel origin for public ingress."
echo "Status: sudo systemctl status trader-stack-offline.service"
echo "Logs:  journalctl -u trader-stack-offline.service -f"
