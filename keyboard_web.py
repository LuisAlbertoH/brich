#!/usr/bin/python3
import json
import mimetypes
import os
import socket
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from keyboard_client import DEFAULT_MACROS_FILE, enqueue_lines, load_macros, pending_command_count, service_state

HOST = os.environ.get("BTF_WEB_HOST", "0.0.0.0")
PORT = int(os.environ.get("BTF_WEB_PORT", "8080"))
STATIC_DIR = Path(__file__).resolve().parent / "webui"
KEYBOARD_SERVICE = os.environ.get("BTF_KEYBOARD_SERVICE", "brich-keyboard.service")


def get_bind_host():
    if HOST == "0.0.0.0":
        return "0.0.0.0"
    return HOST


def get_local_addresses():
    addresses = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in addresses:
                addresses.append(ip)
    except OSError:
        pass
    return addresses


def status_payload():
    macros = load_macros(DEFAULT_MACROS_FILE)
    return {
        "keyboard_service": service_state(KEYBOARD_SERVICE),
        "queue_pending": pending_command_count(),
        "macro_count": len(macros),
        "hostname": socket.gethostname(),
        "addresses": get_local_addresses(),
        "port": PORT,
    }


def validate_lines(lines):
    if not isinstance(lines, list) or not lines:
        raise ValueError("lines must be a non-empty array of strings")
    if len(lines) > 50:
        raise ValueError("Too many command lines")
    for line in lines:
        if not isinstance(line, str):
            raise ValueError("All command lines must be strings")
        if len(line) > 4000:
            raise ValueError("Command line too long")


class KeyboardWebHandler(BaseHTTPRequestHandler):
    server_version = "BrichKeyboardWeb/1.0"

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/status":
            self.send_json(status_payload())
            return
        if path == "/api/macros":
            macros = load_macros(DEFAULT_MACROS_FILE)
            self.send_json({"macros": macros})
            return
        self.serve_static(path)

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/queue":
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")
            return

        try:
            payload = self.read_json_body()
            lines = payload.get("lines")
            validate_lines(lines)
            queued_path = enqueue_lines(lines)
            self.send_json({"ok": True, "queued": str(queued_path)})
        except ValueError as exc:
            self.send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            raise ValueError("Missing JSON body")
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON body") from exc

    def serve_static(self, path):
        if path in ("", "/"):
            rel = "index.html"
        else:
            rel = path.lstrip("/")

        target = (STATIC_DIR / rel).resolve()
        if not str(target).startswith(str(STATIC_DIR.resolve())):
            self.send_error(HTTPStatus.FORBIDDEN, "Invalid path")
            return
        if not target.exists() or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload, status=HTTPStatus.OK):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")


def main():
    server = ThreadingHTTPServer((get_bind_host(), PORT), KeyboardWebHandler)
    print(f"Brich keyboard web UI listening on http://{get_bind_host()}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
