"""Provider-neutral local HTTP bridge for Roblox Studio and AI clients."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import threading
import time
import uuid
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from app_paths import TOKEN_FILE


STATE_LOCK = threading.Lock()
COMMANDS: deque[dict] = deque()
RESULTS: dict[str, dict] = {}
PLUGIN_LAST_SEEN = 0.0
LAST_CLIENT = "No AI client yet"
LAST_CLIENT_SEEN = 0.0
PAIRING_UNTIL = 0.0


def json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "AIBridge/0.2"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def send_json(self, status: int, value: object) -> None:
        body = json_bytes(value)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            raise ValueError("Request is too large")
        raw = self.rfile.read(length)
        return json.loads(raw or b"{}")

    def authorized(self) -> bool:
        return secrets.compare_digest(
            self.headers.get("X-Bridge-Token", ""), self.server.bridge_token
        )

    def require_auth(self) -> bool:
        if self.authorized():
            return True
        self.send_json(401, {"ok": False, "error": "Invalid bridge token"})
        return False

    def do_GET(self) -> None:
        global PLUGIN_LAST_SEEN
        if not self.require_auth():
            return
        path = urlparse(self.path).path
        if path == "/health":
            with STATE_LOCK:
                age = time.time() - PLUGIN_LAST_SEEN if PLUGIN_LAST_SEEN else None
                queued = len(COMMANDS)
                client_age = time.time() - LAST_CLIENT_SEEN if LAST_CLIENT_SEEN else None
                pairing_left = max(0, PAIRING_UNTIL - time.time())
            self.send_json(200, {
                "ok": True,
                "plugin_seen_seconds_ago": age,
                "queued": queued,
                "last_client": LAST_CLIENT,
                "last_client_seen_seconds_ago": client_age,
                "pairing_seconds_left": pairing_left,
            })
            return
        if path == "/plugin/poll":
            with STATE_LOCK:
                PLUGIN_LAST_SEEN = time.time()
                command = COMMANDS.popleft() if COMMANDS else None
            self.send_json(200, {"ok": True, "command": command})
            return
        if path.startswith("/result/"):
            command_id = path.removeprefix("/result/")
            with STATE_LOCK:
                result = RESULTS.get(command_id)
            self.send_json(200, {"ok": True, "ready": result is not None, "result": result})
            return
        self.send_json(404, {"ok": False, "error": "Unknown endpoint"})

    def do_POST(self) -> None:
        global LAST_CLIENT, LAST_CLIENT_SEEN
        path = urlparse(self.path).path
        try:
            payload = self.read_json()
            if path == "/plugin/pair":
                if time.time() > PAIRING_UNTIL:
                    self.send_json(403, {"ok": False, "error": "Pairing mode is closed"})
                    return
                install_id = str(payload.get("install_id", ""))
                if not install_id or len(install_id) > 100:
                    self.send_json(400, {"ok": False, "error": "Invalid install ID"})
                    return
                self.send_json(200, {"ok": True, "token": self.server.bridge_token})  # type: ignore[attr-defined]
                return
            if not self.require_auth():
                return
            if path == "/command":
                LAST_CLIENT = str(payload.get("client", "Unknown AI client"))[:100]
                LAST_CLIENT_SEEN = time.time()
                command = {
                    "id": str(uuid.uuid4()),
                    "action": payload["action"],
                    "args": payload.get("args", {}),
                    "client": payload.get("client", "Unknown AI client"),
                }
                with STATE_LOCK:
                    COMMANDS.append(command)
                self.send_json(202, {"ok": True, "command_id": command["id"]})
                return
            if path == "/plugin/result":
                command_id = payload["id"]
                with STATE_LOCK:
                    RESULTS[command_id] = payload
                    if len(RESULTS) > 500:
                        for old_id in list(RESULTS)[:100]:
                            RESULTS.pop(old_id, None)
                self.send_json(200, {"ok": True})
                return
            self.send_json(404, {"ok": False, "error": "Unknown endpoint"})
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=32145)
    parser.add_argument("--token", default=os.getenv("ROBLOX_BRIDGE_TOKEN"))
    args = parser.parse_args()
    saved_token = TOKEN_FILE.read_text(encoding="utf-8").strip() if TOKEN_FILE.exists() else None
    token = args.token or saved_token or secrets.token_urlsafe(24)
    TOKEN_FILE.write_text(token, encoding="utf-8")
    server = create_server(args.host, args.port, token)
    enable_pairing(300)
    print(f"Bridge listening on http://{args.host}:{args.port}")
    print(f"Token: {token}")
    print(f"Token saved to: {TOKEN_FILE}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping bridge.")


def create_server(host: str = "127.0.0.1", port: int = 32145, token: str | None = None) -> ThreadingHTTPServer:
    bridge_token = token or (TOKEN_FILE.read_text(encoding="utf-8").strip() if TOKEN_FILE.exists() else secrets.token_urlsafe(24))
    TOKEN_FILE.write_text(bridge_token, encoding="utf-8")
    http_server = ThreadingHTTPServer((host, port), BridgeHandler)
    http_server.bridge_token = bridge_token  # type: ignore[attr-defined]
    return http_server


def enable_pairing(seconds: int = 300) -> None:
    global PAIRING_UNTIL
    PAIRING_UNTIL = time.time() + max(30, min(seconds, 600))


if __name__ == "__main__":
    main()
