import os
from concurrent.futures import ThreadPoolExecutor
import base64
import hashlib
import time
from urllib.parse import parse_qs, urlparse

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
    assert client.get("/.well-known/oauth-authorization-server").json()["registration_endpoint"].endswith("/oauth/register")
    unauthorized_mcp = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert unauthorized_mcp.status_code == 401
    assert "resource_metadata" in unauthorized_mcp.headers["www-authenticate"]


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

    redirect_uri = "https://claude.ai/api/mcp/auth_callback"
    oauth_client = client.post("/oauth/register", json={
        "client_name": "Claude test",
        "redirect_uris": [redirect_uri],
        "token_endpoint_auth_method": "none",
    })
    assert oauth_client.status_code == 200
    client_id = oauth_client.json()["client_id"]
    verifier = "test-verifier-with-enough-random-characters-1234567890"
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    authorize_params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": "test-state",
        "scope": "mcp",
    }
    authorize_page = client.get("/oauth/authorize", params=authorize_params)
    assert authorize_page.status_code == 200
    authorized = client.post(
        "/oauth/authorize",
        data={**authorize_params, "bridge_token": claimed.json()["client_token"]},
        follow_redirects=False,
    )
    assert authorized.status_code == 303
    auth_code = parse_qs(urlparse(authorized.headers["location"]).query)["code"][0]
    exchanged = client.post("/oauth/token", data={
        "grant_type": "authorization_code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code": auth_code,
        "code_verifier": verifier,
    })
    assert exchanged.status_code == 200
    oauth_headers = {"Authorization": "Bearer " + exchanged.json()["access_token"]}
    oauth_mcp = client.post("/mcp", headers=oauth_headers, json={
        "jsonrpc": "2.0", "id": 3, "method": "initialize", "params": {}
    })
    assert oauth_mcp.status_code == 200
