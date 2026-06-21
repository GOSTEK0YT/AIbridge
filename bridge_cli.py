"""Send one command to the local Roblox Studio bridge and await its result."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from app_paths import TOKEN_FILE


def request(method: str, url: str, token: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "X-Bridge-Token": token},
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action")
    parser.add_argument("args", nargs="?", default="{}", help="JSON object")
    parser.add_argument("--url", default="http://127.0.0.1:32145")
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--client", default="AI Bridge CLI")
    ns = parser.parse_args()
    raw_args = sys.stdin.read() if ns.args == "-" else ns.args
    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    submitted = request("POST", f"{ns.url}/command", token, {
        "action": ns.action,
        "args": json.loads(raw_args),
        "client": ns.client,
    })
    command_id = submitted["command_id"]
    deadline = time.time() + ns.timeout
    while time.time() < deadline:
        response = request("GET", f"{ns.url}/result/{command_id}", token)
        if response["ready"]:
            print(json.dumps(response["result"], ensure_ascii=False, indent=2))
            return
        time.sleep(0.2)
    raise SystemExit(f"Timed out waiting for Roblox Studio ({command_id})")


if __name__ == "__main__":
    main()
