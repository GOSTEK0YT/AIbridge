import os

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


def test_pair_command_roundtrip():
    registered = client.post("/v1/plugins/register", json={"name": "Studio test"})
    assert registered.status_code == 200
    registration = registered.json()
    headers = {"X-AI-Bridge-Key": "test-key"}
    claimed = client.post("/v1/pair/claim", headers=headers, json={"code": registration["pairing_code"]})
    assert claimed.status_code == 200

    created = client.post("/v1/commands", headers=headers, json={
        "device_id": registration["device_id"],
        "client": "test-ai",
        "action": "ping",
        "args": {},
    })
    command_id = created.json()["command_id"]
    plugin_headers = {"Authorization": "Bearer " + registration["plugin_token"]}
    polled = client.get("/v1/plugin/poll", headers=plugin_headers)
    assert polled.json()["command"]["id"] == command_id
    result = client.post(f"/v1/plugin/result/{command_id}", headers=plugin_headers, json={"ok": True, "data": {"place": "Test"}})
    assert result.status_code == 200
    fetched = client.get(f"/v1/commands/{command_id}", headers=headers)
    assert fetched.json()["status"] == "done"
