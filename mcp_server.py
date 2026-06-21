"""Provider-neutral MCP stdio adapter for AI Bridge."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from app_paths import TOKEN_FILE
BRIDGE_URL = "http://127.0.0.1:32145"
SERVER_INFO = {"name": "ai-bridge", "version": "0.4.0"}


TOOLS = [
    {
        "name": "roblox_ping",
        "description": "Check the active Roblox Studio place connected through AI Bridge.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "roblox_create_instance",
        "description": "Create a Roblox Instance under a DataModel path.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "parent": {"type": "string", "description": "Example: game/Workspace"},
                "className": {"type": "string", "description": "Roblox class name"},
                "name": {"type": "string"},
                "properties": {"type": "object"},
            },
            "required": ["parent", "className"],
            "additionalProperties": False,
        },
    },
    {
        "name": "roblox_set_properties",
        "description": "Update properties of an existing Roblox Instance.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "properties": {"type": "object"}},
            "required": ["path", "properties"],
            "additionalProperties": False,
        },
    },
    {
        "name": "roblox_move_instance",
        "description": "Move an existing Roblox Instance to a new parent.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "newParent": {"type": "string"}},
            "required": ["path", "newParent"],
            "additionalProperties": False,
        },
    },
    {
        "name": "roblox_delete_instance",
        "description": "Delete an existing Roblox Instance. This is destructive.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
        "annotations": {"destructiveHint": True},
    },
]


ACTION_MAP = {
    "roblox_ping": "ping",
    "roblox_create_instance": "create_instance",
    "roblox_set_properties": "set_properties",
    "roblox_move_instance": "move_instance",
    "roblox_delete_instance": "delete_instance",
}


def token() -> str:
    if not TOKEN_FILE.exists():
        raise RuntimeError("Start AI Bridge Desktop or server.py first")
    return TOKEN_FILE.read_text(encoding="utf-8").strip()


def bridge_request(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        BRIDGE_URL + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "X-Bridge-Token": token()},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.load(response)
    except urllib.error.URLError as exc:
        raise RuntimeError(f"AI Bridge is unavailable: {exc.reason}") from exc


def execute_tool(name: str, arguments: dict) -> dict:
    action = ACTION_MAP.get(name)
    if not action:
        raise RuntimeError(f"Unknown tool: {name}")
    submitted = bridge_request("POST", "/command", {
        "client": "MCP client",
        "action": action,
        "args": arguments,
    })
    command_id = submitted["command_id"]
    deadline = time.time() + 20
    while time.time() < deadline:
        response = bridge_request("GET", f"/result/{command_id}")
        if response["ready"]:
            result = response["result"]
            if not result.get("ok"):
                raise RuntimeError(str(result.get("data", "Roblox operation failed")))
            return result.get("data", {})
        time.sleep(0.15)
    raise RuntimeError("Roblox Studio did not answer within 20 seconds")


def response(request_id: object, result: object = None, error: dict | None = None) -> None:
    message = {"jsonrpc": "2.0", "id": request_id}
    if error is not None:
        message["error"] = error
    else:
        message["result"] = result
    sys.stdout.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def handle(message: dict) -> None:
    method = message.get("method")
    request_id = message.get("id")
    if method == "initialize":
        requested = message.get("params", {}).get("protocolVersion", "2024-11-05")
        response(request_id, {
            "protocolVersion": requested,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
        })
    elif method == "ping":
        response(request_id, {})
    elif method == "tools/list":
        response(request_id, {"tools": TOOLS})
    elif method == "tools/call":
        params = message.get("params", {})
        try:
            result = execute_tool(params.get("name", ""), params.get("arguments") or {})
            response(request_id, {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]})
        except Exception as exc:
            response(request_id, {
                "content": [{"type": "text", "text": str(exc)}],
                "isError": True,
            })
    elif request_id is not None:
        response(request_id, error={"code": -32601, "message": f"Method not found: {method}"})


def main() -> None:
    for line in sys.stdin:
        try:
            message = json.loads(line)
            handle(message)
        except Exception as exc:
            response(None, error={"code": -32700, "message": str(exc)})


if __name__ == "__main__":
    main()
