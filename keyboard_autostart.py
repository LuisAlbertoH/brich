#!/usr/bin/python3
import atexit
import fcntl
import os
import subprocess
import time
import traceback
from pathlib import Path

import btfpy

# Dedicated keyboard daemon for Raspberry Pi (auto-start friendly).
# It keeps the LE server alive and reinitializes on unexpected exits.

CONFIG_FILE = os.environ.get("BTF_KEYBOARD_CONFIG", "keyboard.txt")
LE_WAIT_MS = int(os.environ.get("BTF_LE_WAIT_MS", "30000"))
RESTART_DELAY_SEC = float(os.environ.get("BTF_RESTART_DELAY_SEC", "2"))
TIMER_DS = int(os.environ.get("BTF_TIMER_DS", "1"))
QUEUE_DIR = Path(os.environ.get("BTF_KEYBOARD_QUEUE", "/tmp/brich_keyboard_queue"))
LOCK_FILE = Path(os.environ.get("BTF_KEYBOARD_LOCK", "/tmp/brich_keyboard.lock"))

# Fixed random LE address (static random address).
# Change this value if clients keep using stale cached identity.
RANDADD = [0xD3, 0x56, 0xD6, 0x74, 0x33, 0x04]

reportmap = [
    0x05, 0x01, 0x09, 0x06, 0xA1, 0x01, 0x85, 0x01, 0x05, 0x07, 0x19, 0xE0,
    0x29, 0xE7, 0x15, 0x00, 0x25, 0x01, 0x75, 0x01, 0x95, 0x08, 0x81, 0x02,
    0x95, 0x01, 0x75, 0x08, 0x81, 0x01, 0x95, 0x06, 0x75, 0x08, 0x15, 0x00,
    0x25, 0x65, 0x05, 0x07, 0x19, 0x00, 0x29, 0x65, 0x81, 0x00, 0xC0
]
report = [0, 0, 0, 0, 0, 0, 0, 0]

name = "HID"
appear = [0xC1, 0x03]
pnpinfo = [0x02, 0x6B, 0x1D, 0x46, 0x02, 0x37, 0x05]
protocolmode = [0x01]
hidinfo = [0x01, 0x11, 0x00, 0x02]

reportindex = -1
node = 0
client_connected = False
lock_handle = None

MOD_LCTRL = 0x01
MOD_LSHIFT = 0x02
MOD_LALT = 0x04
MOD_LGUI = 0x08
MOD_RCTRL = 0x10
MOD_RSHIFT = 0x20
MOD_RALT = 0x40
MOD_RGUI = 0x80

MOD_ALIAS = {
    "CTRL": MOD_LCTRL,
    "LCTRL": MOD_LCTRL,
    "RCTRL": MOD_RCTRL,
    "SHIFT": MOD_LSHIFT,
    "LSHIFT": MOD_LSHIFT,
    "RSHIFT": MOD_RSHIFT,
    "ALT": MOD_LALT,
    "LALT": MOD_LALT,
    "RALT": MOD_RALT,
    "ALTGR": MOD_RALT,
    "GUI": MOD_LGUI,
    "WIN": MOD_LGUI,
    "CMD": MOD_LGUI,
}

KEY_NAME_TO_USAGE = {
    "ENTER": 0x28,
    "RETURN": 0x28,
    "ESC": 0x29,
    "ESCAPE": 0x29,
    "BACKSPACE": 0x2A,
    "TAB": 0x2B,
    "SPACE": 0x2C,
    "MINUS": 0x2D,
    "EQUAL": 0x2E,
    "LBRACKET": 0x2F,
    "RBRACKET": 0x30,
    "BACKSLASH": 0x31,
    "SEMICOLON": 0x33,
    "APOSTROPHE": 0x34,
    "GRAVE": 0x35,
    "COMMA": 0x36,
    "DOT": 0x37,
    "PERIOD": 0x37,
    "SLASH": 0x38,
    "CAPSLOCK": 0x39,
    "F1": 0x3A,
    "F2": 0x3B,
    "F3": 0x3C,
    "F4": 0x3D,
    "F5": 0x3E,
    "F6": 0x3F,
    "F7": 0x40,
    "F8": 0x41,
    "F9": 0x42,
    "F10": 0x43,
    "F11": 0x44,
    "F12": 0x45,
    "PRINTSCREEN": 0x46,
    "SCROLLLOCK": 0x47,
    "PAUSE": 0x48,
    "INSERT": 0x49,
    "HOME": 0x4A,
    "PGUP": 0x4B,
    "PAGEUP": 0x4B,
    "DELETE": 0x4C,
    "DEL": 0x4C,
    "END": 0x4D,
    "PGDN": 0x4E,
    "PAGEDOWN": 0x4E,
    "RIGHT": 0x4F,
    "LEFT": 0x50,
    "DOWN": 0x51,
    "UP": 0x52,
}

CHAR_TO_USAGE = {
    " ": (0, 0x2C),
    "-": (0, 0x2D),
    "_": (MOD_LSHIFT, 0x2D),
    "=": (0, 0x2E),
    "+": (MOD_LSHIFT, 0x2E),
    "[": (0, 0x2F),
    "{": (MOD_LSHIFT, 0x2F),
    "]": (0, 0x30),
    "}": (MOD_LSHIFT, 0x30),
    "\\": (0, 0x31),
    "|": (MOD_LSHIFT, 0x31),
    ";": (0, 0x33),
    ":": (MOD_LSHIFT, 0x33),
    "'": (0, 0x34),
    "\"": (MOD_LSHIFT, 0x34),
    "`": (0, 0x35),
    "~": (MOD_LSHIFT, 0x35),
    ",": (0, 0x36),
    "<": (MOD_LSHIFT, 0x36),
    ".": (0, 0x37),
    ">": (MOD_LSHIFT, 0x37),
    "/": (0, 0x38),
    "?": (MOD_LSHIFT, 0x38),
    "!": (MOD_LSHIFT, 0x1E),
    "@": (MOD_LSHIFT, 0x1F),
    "#": (MOD_LSHIFT, 0x20),
    "$": (MOD_LSHIFT, 0x21),
    "%": (MOD_LSHIFT, 0x22),
    "^": (MOD_LSHIFT, 0x23),
    "&": (MOD_LSHIFT, 0x24),
    "*": (MOD_LSHIFT, 0x25),
    "(": (MOD_LSHIFT, 0x26),
    ")": (MOD_LSHIFT, 0x27),
}


def write_local_hid_characteristics():
    uuid = [0x2A, 0x00]
    btfpy.Write_ctic(node, btfpy.Find_ctic_index(node, btfpy.UUID_2, uuid), name, 0)

    uuid = [0x2A, 0x01]
    btfpy.Write_ctic(node, btfpy.Find_ctic_index(node, btfpy.UUID_2, uuid), appear, 0)

    uuid = [0x2A, 0x4E]
    btfpy.Write_ctic(node, btfpy.Find_ctic_index(node, btfpy.UUID_2, uuid), protocolmode, 0)

    uuid = [0x2A, 0x4A]
    btfpy.Write_ctic(node, btfpy.Find_ctic_index(node, btfpy.UUID_2, uuid), hidinfo, 0)

    uuid = [0x2A, 0x4B]
    btfpy.Write_ctic(node, btfpy.Find_ctic_index(node, btfpy.UUID_2, uuid), reportmap, 0)

    uuid = [0x2A, 0x4D]
    btfpy.Write_ctic(node, btfpy.Find_ctic_index(node, btfpy.UUID_2, uuid), report, 0)

    uuid = [0x2A, 0x50]
    btfpy.Write_ctic(node, btfpy.Find_ctic_index(node, btfpy.UUID_2, uuid), pnpinfo, 0)


def send_key(key):
    hidcode = btfpy.Hid_key_code(key)
    if hidcode == 0:
        return

    buf = [0, 0, 0, 0, 0, 0, 0, 0]

    buf[0] = (hidcode >> 8) & 0xFF
    buf[2] = hidcode & 0xFF
    btfpy.Write_ctic(node, reportindex, buf, 0)

    buf[0] = 0
    buf[2] = 0
    btfpy.Write_ctic(node, reportindex, buf, 0)


def send_hid(modifier, keycode):
    buf = [modifier & 0xFF, 0, keycode & 0xFF, 0, 0, 0, 0, 0]
    btfpy.Write_ctic(node, reportindex, buf, 0)
    btfpy.Write_ctic(node, reportindex, [0, 0, 0, 0, 0, 0, 0, 0], 0)


def key_token_to_hid(token):
    t = token.strip()
    if not t:
        return None

    if len(t) == 1:
        ch = t
        if "a" <= ch <= "z":
            return (0, 0x04 + (ord(ch) - ord("a")))
        if "A" <= ch <= "Z":
            return (MOD_LSHIFT, 0x04 + (ord(ch.lower()) - ord("a")))
        if "1" <= ch <= "9":
            return (0, 0x1E + (ord(ch) - ord("1")))
        if ch == "0":
            return (0, 0x27)
        if ch in CHAR_TO_USAGE:
            return CHAR_TO_USAGE[ch]
        return None

    upper = t.upper()
    if upper in KEY_NAME_TO_USAGE:
        return (0, KEY_NAME_TO_USAGE[upper])

    return None


def parse_combo(combo_spec):
    parts = [p.strip() for p in combo_spec.split("+") if p.strip()]
    if not parts:
        raise ValueError("Empty combo")

    modifier = 0
    key_part = None
    for part in parts:
        up = part.upper()
        if up in MOD_ALIAS:
            modifier |= MOD_ALIAS[up]
        else:
            if key_part is not None:
                raise ValueError("Combo must include only one non-modifier key")
            key_part = part

    if key_part is None:
        raise ValueError("Combo must include a key")

    parsed = key_token_to_hid(key_part)
    if parsed is None:
        raise ValueError("Unsupported key in combo: " + key_part)

    extra_mod, keycode = parsed
    return (modifier | extra_mod, keycode)


def send_text(text):
    for ch in text:
        send_key(ord(ch))


def send_named_key(token):
    parsed = key_token_to_hid(token)
    if parsed is None:
        raise ValueError("Unsupported key token: " + token)
    mod, keycode = parsed
    send_hid(mod, keycode)


def execute_command_line(line):
    raw = line.rstrip("\r\n")
    if not raw.strip() or raw.lstrip().startswith("#"):
        return

    parts = raw.split(" ", 1)
    cmd = parts[0].strip().upper()
    payload = parts[1] if len(parts) > 1 else ""

    if cmd == "TEXT":
        send_text(payload)
    elif cmd == "KEY":
        send_named_key(payload.strip())
    elif cmd == "COMBO":
        mod, keycode = parse_combo(payload.strip())
        send_hid(mod, keycode)
    elif cmd == "DELAY":
        delay_ms = int(payload.strip())
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
    else:
        raise ValueError("Unknown command: " + cmd)


def ensure_queue_dir():
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(QUEUE_DIR, 0o777)
    except PermissionError:
        pass


def run_quiet(cmd, timeout_sec=3):
    try:
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=timeout_sec,
        )
    except FileNotFoundError:
        pass
    except subprocess.TimeoutExpired:
        pass


def prepare_adapter():
    # Best-effort recovery before btferret init.
    run_quiet(["rfkill", "unblock", "bluetooth"])
    run_quiet(["hciconfig", "hci0", "up"])


def acquire_instance_lock():
    global lock_handle
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    lock_handle = LOCK_FILE.open("w", encoding="utf-8")
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise RuntimeError(
            "Another keyboard service instance is already running. "
            "Stop brich-keyboard.service before starting manually."
        ) from exc
    lock_handle.seek(0)
    lock_handle.write(str(os.getpid()))
    lock_handle.truncate()
    lock_handle.flush()


def release_instance_lock():
    global lock_handle
    if lock_handle is None:
        return
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass
    lock_handle.close()
    lock_handle = None


def process_command_queue():
    # A command file can contain multiple lines, for example:
    # COMBO CTRL+L
    # TEXT https://example.com
    # KEY ENTER
    for cmd_file in sorted(QUEUE_DIR.glob("*.cmd")):
        try:
            with cmd_file.open("r", encoding="utf-8") as fh:
                lines = fh.readlines()
            for line in lines:
                execute_command_line(line)
            print("Executed command file:", cmd_file.name)
        except Exception as exc:
            print("Failed command file", cmd_file.name, "->", exc)
        finally:
            try:
                cmd_file.unlink()
            except FileNotFoundError:
                pass


def lecallback(clientnode, op, cticn):
    global client_connected

    if op == btfpy.LE_CONNECT:
        client_connected = True
        print("Client connected. Keyboard events enabled.")
        print("F10 sends 'Hello' + Enter. Remote queue is active.")
        process_command_queue()

    elif op == btfpy.LE_KEYPRESS:
        if cticn == 23:
            hello = "Hello\n"
            for ch in hello:
                send_key(ord(ch))
        else:
            send_key(cticn)

    elif op == btfpy.LE_TIMER:
        if client_connected:
            process_command_queue()

    elif op == btfpy.LE_DISCONNECT:
        # Keep process alive and wait for the next connection.
        client_connected = False
        print("Client disconnected. Waiting for reconnection...")
        return btfpy.SERVER_CONTINUE

    return btfpy.SERVER_CONTINUE


def init_server():
    global node
    global reportindex

    prepare_adapter()
    if btfpy.Init_blue(CONFIG_FILE) == 0:
        raise RuntimeError("Init_blue failed")

    if btfpy.Localnode() != 1:
        local_addr = btfpy.Device_address(btfpy.Localnode())
        raise RuntimeError(
            "Local node is not node 1. Edit keyboard.txt ADDRESS with local address: " + local_addr
        )

    node = btfpy.Localnode()

    uuid = [0x2A, 0x4D]
    reportindex = btfpy.Find_ctic_index(node, btfpy.UUID_2, uuid)
    if reportindex < 0:
        raise RuntimeError("Failed to find Report characteristic (UUID 2A4D)")

    write_local_hid_characteristics()

    ensure_queue_dir()
    btfpy.Set_le_random_address(RANDADD)
    btfpy.Keys_to_callback(btfpy.KEY_ON, 0)
    btfpy.Set_le_wait(LE_WAIT_MS)
    btfpy.Le_pair(btfpy.Localnode(), btfpy.JUST_WORKS, 0)


def main():
    acquire_instance_lock()
    atexit.register(release_instance_lock)

    print("Starting keyboard auto service with config:", CONFIG_FILE)
    print("LE wait (ms):", LE_WAIT_MS)
    print("Timer (deci-seconds):", TIMER_DS)
    print("Queue dir:", str(QUEUE_DIR))
    print("Lock file:", str(LOCK_FILE))

    initialized = False

    while True:
        try:
            init_server()
            initialized = True
            retval = btfpy.Le_server(lecallback, TIMER_DS)
            print("Le_server finished with code:", retval)
        except KeyboardInterrupt:
            print("Interrupted. Exiting.")
            break
        except Exception as exc:
            print("Server error:", exc)
            traceback.print_exc()
            # If initialization fails, exit and let systemd restart.
            # Re-running Init_blue in the same process causes noisy loops.
            if not initialized:
                break
        finally:
            if initialized:
                btfpy.Close_all()
                initialized = False

        time.sleep(RESTART_DELAY_SEC)


if __name__ == "__main__":
    main()
