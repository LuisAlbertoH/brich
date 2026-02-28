#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="brich-keyboard.service"
WEB_SERVICE_NAME="brich-keyboard-web.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root. Example:"
  echo "  sudo ./deploy/update_keyboard_from_github.sh"
  exit 1
fi

cd "${REPO_DIR}"

BRANCH="$(git branch --show-current)"
if [[ -z "${BRANCH}" ]]; then
  echo "Could not detect current git branch."
  exit 1
fi

echo "[1/6] Stopping keyboard service (disconnects active BLE client)..."
systemctl stop "${SERVICE_NAME}" || true
systemctl stop "${WEB_SERVICE_NAME}" || true

echo "[2/6] Stopping stray manual keyboard processes..."
pkill -f "python3 .*keyboard_autostart.py" || true
pkill -f "python3 .*keyboard.py" || true
sleep 1

echo "[3/6] Resetting Bluetooth adapter state..."
rfkill unblock bluetooth || true
hciconfig hci0 down || true
hciconfig hci0 up || true

echo "[4/6] Updating git branch '${BRANCH}' from origin..."
git fetch origin
git pull --ff-only origin "${BRANCH}"

echo "[5/6] Rebuilding btfpy module..."
python3 btfpymake.py build

echo "[6/6] Starting keyboard service..."
systemctl daemon-reload
systemctl start "${SERVICE_NAME}"
systemctl enable "${SERVICE_NAME}" >/dev/null 2>&1 || true
systemctl start "${WEB_SERVICE_NAME}" || true
systemctl enable "${WEB_SERVICE_NAME}" >/dev/null 2>&1 || true

echo
echo "Update complete."
echo "Status:"
systemctl --no-pager --full status "${SERVICE_NAME}" || true
echo
echo "Live logs:"
echo "  journalctl -u ${SERVICE_NAME} -f"
