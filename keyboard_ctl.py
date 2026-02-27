#!/usr/bin/python3
import argparse
import json
import os
import sys
import time
from pathlib import Path

QUEUE_DIR = Path(os.environ.get("BTF_KEYBOARD_QUEUE", "/tmp/brich_keyboard_queue"))
DEFAULT_MACROS_FILE = Path(os.environ.get("BTF_KEYBOARD_MACROS", "keyboard_macros.json"))


def ensure_queue_dir():
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)


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
    print("Queued:", cmd_file)


def load_macros(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Macros file not found: {path}. Create it from keyboard_macros.json sample."
        )
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("Macros file must be a JSON object: {\"macro_name\": [\"COMMAND ...\"]}")
    return obj


def main():
    parser = argparse.ArgumentParser(
        description="Queue remote keyboard commands for keyboard_autostart.py"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_text = sub.add_parser("text", help="Send literal text")
    p_text.add_argument("message", help="Text to type")

    p_key = sub.add_parser("key", help="Send a single key")
    p_key.add_argument("token", help="Examples: ENTER, TAB, ESC, F5, a, A, 1")

    p_combo = sub.add_parser("combo", help="Send a modifier combination")
    p_combo.add_argument("spec", help="Examples: CTRL+ALT+T, GUI+R, CTRL+SHIFT+ESC")

    p_macro = sub.add_parser("macro", help="Run a named macro from JSON file")
    p_macro.add_argument("name", help="Macro name")
    p_macro.add_argument(
        "--file",
        default=str(DEFAULT_MACROS_FILE),
        help="Macros JSON file (default: keyboard_macros.json)",
    )

    p_list = sub.add_parser("list-macros", help="List macros from JSON file")
    p_list.add_argument(
        "--file",
        default=str(DEFAULT_MACROS_FILE),
        help="Macros JSON file (default: keyboard_macros.json)",
    )

    args = parser.parse_args()

    try:
        if args.cmd == "text":
            enqueue_lines([f"TEXT {args.message}"])
        elif args.cmd == "key":
            enqueue_lines([f"KEY {args.token}"])
        elif args.cmd == "combo":
            enqueue_lines([f"COMBO {args.spec}"])
        elif args.cmd == "macro":
            macro_path = Path(args.file)
            macros = load_macros(macro_path)
            if args.name not in macros:
                available = ", ".join(sorted(macros.keys())) or "(none)"
                raise KeyError(f"Macro '{args.name}' not found. Available: {available}")

            lines = macros[args.name]
            if not isinstance(lines, list) or not all(isinstance(x, str) for x in lines):
                raise ValueError(
                    f"Macro '{args.name}' must be an array of strings like "
                    f"[\"COMBO CTRL+L\", \"TEXT hello\", \"KEY ENTER\"]"
                )
            enqueue_lines(lines)
        elif args.cmd == "list-macros":
            macro_path = Path(args.file)
            macros = load_macros(macro_path)
            for name in sorted(macros.keys()):
                print(name)
        else:
            raise ValueError("Unknown command")
    except Exception as exc:
        print("Error:", exc, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
