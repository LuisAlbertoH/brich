#!/usr/bin/python3
import json
import os
import subprocess
import time
from pathlib import Path

QUEUE_DIR = Path(os.environ.get("BTF_KEYBOARD_QUEUE", "/tmp/brich_keyboard_queue"))
DEFAULT_MACROS_FILE = Path(os.environ.get("BTF_KEYBOARD_MACROS", "keyboard_macros.json"))


def ensure_queue_dir():
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(QUEUE_DIR, 0o777)
    except PermissionError:
        pass


def enqueue_lines(lines):
    ensure_queue_dir()
    ts = time.time_ns()
    cmd_file = QUEUE_DIR / f"{ts}_{os.getpid()}.cmd"
    data = "\n".join(lines) + "\n"
    cmd_file.write_text(data, encoding="utf-8")
    try:
        os.chmod(cmd_file, 0o666)
    except PermissionError:
        pass
    return cmd_file


def load_macros(path=None):
    macro_path = Path(path) if path is not None else DEFAULT_MACROS_FILE
    if not macro_path.exists():
        raise FileNotFoundError(
            f"Macros file not found: {macro_path}. Create it from keyboard_macros.json sample."
        )
    obj = json.loads(macro_path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("Macros file must be a JSON object: {\"macro_name\": [\"COMMAND ...\"]}")
    return obj


def pending_command_count():
    ensure_queue_dir()
    return len(list(QUEUE_DIR.glob("*.cmd")))


def service_state(service_name):
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "unknown"

    state = result.stdout.strip()
    return state or "unknown"
