#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="brich-keyboard-web.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}"
SERVICE_USER="${SUDO_USER:-$(stat -c '%U' "${REPO_DIR}")}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root. Example:"
  echo "  sudo ./deploy/install_keyboard_web_service.sh"
  exit 1
fi

cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=Brich Keyboard Web UI
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${REPO_DIR}
ExecStart=/usr/bin/python3 ${REPO_DIR}/keyboard_web.py
Restart=always
RestartSec=2
Environment=BTF_WEB_HOST=0.0.0.0
Environment=BTF_WEB_PORT=8080
Environment=BTF_KEYBOARD_QUEUE=/tmp/brich_keyboard_queue
Environment=BTF_KEYBOARD_MACROS=${REPO_DIR}/keyboard_macros.json
Environment=BTF_KEYBOARD_SERVICE=brich-keyboard.service
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now "${SERVICE_NAME}"

echo "Installed and started ${SERVICE_NAME}"
echo "Check status:"
echo "  systemctl status ${SERVICE_NAME}"
echo "View logs:"
echo "  journalctl -u ${SERVICE_NAME} -f"
