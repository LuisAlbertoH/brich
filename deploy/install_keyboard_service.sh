#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="brich-keyboard.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root. Example:"
  echo "  sudo ./deploy/install_keyboard_service.sh"
  exit 1
fi

if [[ ! -f "${REPO_DIR}/btfpy.so" ]]; then
  echo "btfpy.so not found. Building module..."
  cd "${REPO_DIR}"
  python3 btfpymake.py build
fi

cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=Brich BLE HID Keyboard
After=multi-user.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=${REPO_DIR}
ExecStart=/usr/bin/python3 ${REPO_DIR}/keyboard_autostart.py
Restart=always
RestartSec=2
Environment=BTF_KEYBOARD_CONFIG=${REPO_DIR}/keyboard.txt
Environment=BTF_LE_WAIT_MS=30000
Environment=BTF_RESTART_DELAY_SEC=2
Environment=BTF_TIMER_DS=1
Environment=BTF_KEYBOARD_QUEUE=/tmp/brich_keyboard_queue
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
