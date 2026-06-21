import os
from concurrent.futures import ThreadPoolExecutor
import time

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["AI_BRIDGE_API_KEY"] = "test-key"

from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_home_and_health():
    home = client.get("/")
    assert home.status_code == 200
    assert "Cloud relay is online" in home.text
    assert client.get("/health").json()["ok"] is True
    assert client.get("/connect").status_code == 200


def test_pair_command_roundtrip():
    registered = client.post("/v1/plugins/register", json={"name": "Studio test"})
    assert registered.status_code == 200
    registration = registered.json()
    claimed = client.post("/v1/pair/claim", json={"code": registration["pairing_code"], "client_name": "test-ai"})
    assert claimed.status_code == 200
    client_headers = {"Authorization": "Bearer " + claimed.json()["client_token"]}

    created = client.post("/v1/client/commands", headers=client_headers, json={
        "action": "ping",
        "args": {},
    })
    command_id = created.json()["command_id"]
    plugin_headers = {"Authorization": "Bearer " + registration["plugin_token"]}
    polled = client.get("/v1/plugin/poll", headers=plugin_headers)
    assert polled.json()["command"]["id"] == command_id
    result = client.post(f"/v1/plugin/result/{command_id}", headers=plugin_headers, json={"ok": True, "data": {"place": "Test"}})
    assert result.status_code == 200
    fetched = client.get(f"/v1/client/commands/{command_id}", headers=client_headers)
    assert fetched.json()["status"] == "done"

    initialized = client.post("/mcp", headers=client_headers, json={
        "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}
    })
    assert initialized.status_code == 200
    assert initialized.json()["result"]["serverInfo"]["name"] == "AI Bridge"

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(client.post, "/mcp", headers=client_headers, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "ping", "arguments": {}},
        })
        mcp_command = None
        for _ in range(30):
            candidate = client.get("/v1/plugin/poll", headers=plugin_headers).json()["command"]
            if candidate:
                mcp_command = candidate
                break
            time.sleep(0.05)
        assert mcp_command is not None
        client.post(
            f"/v1/plugin/result/{mcp_command['id']}",
            headers=plugin_headers,
            json={"ok": True, "data": {"placeName": "Test place"}},
        )
        mcp_result = future.result(timeout=5)
    assert mcp_result.status_code == 200
    assert "Test place" in mcp_result.json()["result"]["content"][0]["text"]
