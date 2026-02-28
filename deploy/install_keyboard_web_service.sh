#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="brich-keyboard-web.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}"
SERVICE_USER="${SUDO_USER:-$(stat -c '%U' "${REPO_DIR}")}"
USER_HOME="$(getent passwd "${SERVICE_USER}" | cut -d: -f6)"
DESKTOP_DIR="${USER_HOME}/Desktop"
APP_DIR="${USER_HOME}/.local/share/applications"
SHORTCUT_NAME="brich-keyboard-web.desktop"

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

mkdir -p "${APP_DIR}"
cat > "${APP_DIR}/${SHORTCUT_NAME}" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Brich Keyboard Web
Comment=Open the local Brich keyboard web UI
Exec=sh -c 'xdg-open http://127.0.0.1:8080 >/dev/null 2>&1'
Icon=web-browser
Terminal=false
Categories=Network;Utility;
EOF
chmod 755 "${APP_DIR}/${SHORTCUT_NAME}"
chown "${SERVICE_USER}:${SERVICE_USER}" "${APP_DIR}/${SHORTCUT_NAME}"

if [[ -d "${DESKTOP_DIR}" ]]; then
  cp "${APP_DIR}/${SHORTCUT_NAME}" "${DESKTOP_DIR}/${SHORTCUT_NAME}"
  chown "${SERVICE_USER}:${SERVICE_USER}" "${DESKTOP_DIR}/${SHORTCUT_NAME}"
  chmod 755 "${DESKTOP_DIR}/${SHORTCUT_NAME}"
fi

echo "Installed and started ${SERVICE_NAME}"
echo "Check status:"
echo "  systemctl status ${SERVICE_NAME}"
echo "View logs:"
echo "  journalctl -u ${SERVICE_NAME} -f"
echo "Desktop shortcut:"
echo "  ${DESKTOP_DIR}/${SHORTCUT_NAME}"
