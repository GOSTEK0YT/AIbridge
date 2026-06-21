"""AI Bridge Cloud API — pairing and command relay for Roblox Studio plugins."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import string
import uuid
import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker
from sqlalchemy.pool import StaticPool


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ai_bridge.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

if DATABASE_URL == "sqlite:///:memory:":
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Device(Base):
    __tablename__ = "devices"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), default="Roblox Studio")
    secret_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    pairing_code: Mapped[str] = mapped_column(String(6), index=True, nullable=False)
    pairing_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paired: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    commands: Mapped[list["Command"]] = relationship(back_populates="device", cascade="all, delete-orphan")
    clients: Mapped[list["ClientCredential"]] = relationship(back_populates="device", cascade="all, delete-orphan")


class ClientCredential(Base):
    __tablename__ = "client_credentials"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    name: Mapped[str] = mapped_column(String(100), default="AI client")
    secret_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    device: Mapped[Device] = relationship(back_populates="clients")


class Command(Base):
    __tablename__ = "commands"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    client: Mapped[str] = mapped_column(String(100), default="AI client")
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    arguments: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    device: Mapped[Device] = relationship(back_populates="commands")


Base.metadata.create_all(engine)
app = FastAPI(title="AI Bridge Cloud", version="0.2.0")


def database():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def pairing_code() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(6))


def authenticate_device(authorization: str | None, db: Session) -> Device:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing plugin authorization")
    raw_secret = authorization.removeprefix("Bearer ").strip()
    try:
        device_id, secret = raw_secret.split(".", 1)
    except ValueError as exc:
        raise HTTPException(401, "Invalid plugin authorization") from exc
    device = db.get(Device, device_id)
    if not device or not hmac.compare_digest(device.secret_hash, digest(secret)):
        raise HTTPException(401, "Invalid plugin authorization")
    return device


def bearer_token(authorization: str | None, missing_message: str) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, missing_message)
    return authorization.removeprefix("Bearer ").strip()


def authenticate_client(authorization: str | None, db: Session) -> ClientCredential:
    raw_token = bearer_token(authorization, "Missing AI client authorization")
    try:
        credential_id, secret = raw_token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(401, "Invalid AI client authorization") from exc
    credential = db.get(ClientCredential, credential_id)
    if not credential or not hmac.compare_digest(credential.secret_hash, digest(secret)):
        raise HTTPException(401, "Invalid AI client authorization")
    return credential


def require_api_key(x_ai_bridge_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("AI_BRIDGE_API_KEY", "dev-only-change-me")
    if not x_ai_bridge_key or not hmac.compare_digest(x_ai_bridge_key, expected):
        raise HTTPException(401, "Invalid AI Bridge API key")


class RegisterRequest(BaseModel):
    name: str = Field(default="Roblox Studio", max_length=100)


class PairClaim(BaseModel):
    code: str = Field(min_length=6, max_length=6)
    client_name: str = Field(default="AI client", max_length=100)


class CreateCommand(BaseModel):
    device_id: str
    client: str = Field(default="AI client", max_length=100)
    action: str = Field(max_length=64)
    args: dict = Field(default_factory=dict)


class ClientCommand(BaseModel):
    action: str = Field(max_length=64)
    args: dict = Field(default_factory=dict)


class CommandResult(BaseModel):
    ok: bool
    data: object | None = None


MCP_TOOLS = [
    {"name": "ping", "description": "Check the connected Roblox Studio place.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_tree", "description": "Read the Roblox instance tree.", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "depth": {"type": "integer", "minimum": 0, "maximum": 8}}}},
    {"name": "create_instance", "description": "Create an Instance in Roblox Studio.", "inputSchema": {"type": "object", "properties": {"parent": {"type": "string"}, "className": {"type": "string"}, "name": {"type": "string"}, "properties": {"type": "object"}}, "required": ["className"]}},
    {"name": "set_properties", "description": "Change properties of an existing Instance.", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "properties": {"type": "object"}}, "required": ["path", "properties"]}},
    {"name": "move_instance", "description": "Move an Instance to another parent.", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "newParent": {"type": "string"}}, "required": ["path", "newParent"]}},
    {"name": "delete_instance", "description": "Delete an Instance from Roblox Studio.", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
]


def queue_command(db: Session, device_id: str, client_name: str, action: str, arguments: dict) -> Command:
    command = Command(
        id=str(uuid.uuid4()),
        device_id=device_id,
        client=client_name,
        action=action,
        arguments=arguments,
    )
    db.add(command)
    db.commit()
    return command


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home():
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Bridge Cloud</title>
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; display: grid; place-items: center; padding: 24px;
      color: #f7f8ff; font-family: Inter, system-ui, sans-serif;
      background: radial-gradient(circle at 20% 10%, #152956 0, transparent 35%), #070a13; }
    main { width: min(680px, 100%); padding: 42px; border: 1px solid #29324d; border-radius: 24px;
      background: rgba(15,20,36,.92); box-shadow: 0 24px 80px #0008; }
    .brand { font-size: 14px; font-weight: 800; letter-spacing: .18em; color: #7dd3fc; }
    h1 { margin: 14px 0 8px; font-size: clamp(36px, 8vw, 64px); line-height: .95; }
    p { color: #b6bfd8; font-size: 18px; line-height: 1.6; }
    .status { display: flex; gap: 10px; align-items: center; margin: 28px 0; padding: 16px 18px;
      border-radius: 14px; background: #111a2d; color: #dfffea; font-weight: 700; }
    .dot { width: 11px; height: 11px; border-radius: 50%; background: #2ee68b; box-shadow: 0 0 18px #2ee68b; }
    a { color: #8bdcff; text-decoration: none; font-weight: 700; }
    small { color: #77819c; }
  </style>
</head>
<body><main>
  <div class="brand">AI BRIDGE</div>
  <h1>Cloud relay is online.</h1>
  <p>Connect Roblox Studio to AI clients through one secure bridge.</p>
  <div class="status"><span class="dot"></span> Service operational</div>
  <p><a href="/connect">Connect Roblox Studio &rarr;</a></p>
  <p><a href="/docs">Open API documentation</a></p>
  <small>AI Bridge Cloud v0.2.0</small>
</main></body></html>"""


@app.get("/connect", response_class=HTMLResponse, include_in_schema=False)
def connect_page():
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Connect Roblox Studio · AI Bridge</title>
<style>
*{box-sizing:border-box}body{margin:0;min-height:100vh;padding:24px;display:grid;place-items:center;color:#f7f8ff;font-family:Inter,system-ui,sans-serif;background:radial-gradient(circle at 15% 10%,#17356b 0,transparent 34%),#070a13}
main{width:min(720px,100%);padding:38px;border:1px solid #29324d;border-radius:24px;background:#0f1424ee;box-shadow:0 24px 80px #0008}.brand{font-size:13px;font-weight:900;letter-spacing:.18em;color:#7dd3fc}h1{font-size:clamp(32px,7vw,54px);margin:12px 0}p{color:#b6bfd8;line-height:1.6}.row{display:grid;grid-template-columns:1fr auto;gap:12px;margin:26px 0 12px}input,button{border:0;border-radius:13px;padding:16px;font:inherit;font-weight:800}input{min-width:0;background:#080d19;color:white;border:1px solid #33405f;font-size:24px;letter-spacing:.25em;text-align:center}button{cursor:pointer;background:linear-gradient(135deg,#1aa7ff,#7c3cff);color:white}.card{display:none;margin-top:24px;padding:22px;border-radius:16px;background:#101b30;border:1px solid #2c426a}.card.show{display:block}.ok{color:#4af0a0;font-weight:800}.error{color:#ff8493;font-weight:700}code{display:block;overflow-wrap:anywhere;padding:12px;border-radius:10px;background:#060a12;color:#a8e5ff;user-select:all}.copy{margin-top:8px;background:#253250}.links{display:flex;gap:18px;flex-wrap:wrap;margin-top:22px}a{color:#8bdcff;text-decoration:none;font-weight:700}@media(max-width:560px){main{padding:25px}.row{grid-template-columns:1fr}input{font-size:20px}}
</style></head><body><main>
<div class="brand">AI BRIDGE</div><h1>Connect your Studio</h1>
<p>Open the AI Bridge plugin in Roblox Studio, click <b>Connect</b>, then enter the six-digit code below.</p>
<div class="row"><input id="code" maxlength="6" inputmode="numeric" autocomplete="one-time-code" placeholder="000000"><button id="pair">Connect</button></div>
<div id="message"></div>
<section id="result" class="card"><div class="ok">✓ Roblox Studio connected</div><p>Your private AI client token:</p><code id="token"></code><button class="copy" id="copy">Copy token</button><p><b>Claude, Cursor and other MCP clients</b></p><code>https://ai-bridge-cloud.onrender.com/mcp</code><p>Use the token as an <b>Authorization: Bearer</b> header.</p><p><b>ChatGPT Custom GPT Action</b></p><code>https://ai-bridge-cloud.onrender.com/ai-openapi.json</code><p>Import this schema in GPT Actions, choose API Key authentication, select Bearer, and paste the private token.</p><div class="links"><a href="/docs">REST API docs</a><a href="/">Service status</a></div></section>
</main><script>
const code=document.querySelector('#code'),pair=document.querySelector('#pair'),message=document.querySelector('#message'),result=document.querySelector('#result'),token=document.querySelector('#token');
const preset=new URLSearchParams(location.search).get('code');if(preset)code.value=preset.replace(/\\D/g,'').slice(0,6);
pair.onclick=async()=>{const value=code.value.replace(/\\D/g,'');if(value.length!==6){message.className='error';message.textContent='Enter all 6 digits.';return}pair.disabled=true;pair.textContent='Connecting…';message.textContent='';try{const r=await fetch('/v1/pair/claim',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:value,client_name:'Web AI client'})});const data=await r.json();if(!r.ok)throw new Error(data.detail||'Pairing failed');token.textContent=data.client_token;result.classList.add('show');message.textContent=''}catch(e){message.className='error';message.textContent=e.message}finally{pair.disabled=false;pair.textContent='Connect'}};
document.querySelector('#copy').onclick=async()=>{await navigator.clipboard.writeText(token.textContent);document.querySelector('#copy').textContent='Copied!'};
</script></body></html>"""


@app.get("/health")
def health():
    return {"ok": True, "service": "ai-bridge-cloud", "version": "0.2.0"}


@app.get("/ai-openapi.json", include_in_schema=False)
def ai_openapi_schema():
    return {
        "openapi": "3.1.0",
        "info": {"title": "AI Bridge for Roblox Studio", "version": "0.2.0"},
        "servers": [{"url": "https://ai-bridge-cloud.onrender.com"}],
        "components": {"securitySchemes": {"BearerAuth": {"type": "http", "scheme": "bearer"}}},
        "security": [{"BearerAuth": []}],
        "paths": {
            "/v1/client/status": {"get": {"operationId": "getStudioStatus", "summary": "Check the connected Roblox Studio", "responses": {"200": {"description": "Studio status"}}}},
            "/v1/client/commands": {"post": {"operationId": "sendRobloxCommand", "summary": "Send a safe editing command to Roblox Studio", "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {"action": {"type": "string", "enum": [tool["name"] for tool in MCP_TOOLS]}, "args": {"type": "object"}}, "required": ["action"]}}}}, "responses": {"200": {"description": "Queued command"}}}},
            "/v1/client/commands/{command_id}": {"get": {"operationId": "getRobloxCommandResult", "summary": "Read the result of a Roblox Studio command", "parameters": [{"name": "command_id", "in": "path", "required": True, "schema": {"type": "string"}}], "responses": {"200": {"description": "Command result"}}}},
        },
    }


@app.post("/v1/plugins/register")
def register_plugin(payload: RegisterRequest, db: Session = Depends(database)):
    device_id = str(uuid.uuid4())
    secret = secrets.token_urlsafe(32)
    code = pairing_code()
    while db.scalar(select(Device).where(Device.pairing_code == code, Device.pairing_expires_at > utcnow())):
        code = pairing_code()
    device = Device(
        id=device_id,
        name=payload.name,
        secret_hash=digest(secret),
        pairing_code=code,
        pairing_expires_at=utcnow() + timedelta(minutes=10),
    )
    db.add(device)
    db.commit()
    return {
        "device_id": device_id,
        "plugin_token": f"{device_id}.{secret}",
        "pairing_code": code,
        "expires_in": 600,
    }


@app.post("/v1/pair/claim")
def claim_pairing(payload: PairClaim, db: Session = Depends(database)):
    device = db.scalar(select(Device).where(Device.pairing_code == payload.code))
    expires_at = device.pairing_expires_at if device else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not device or not expires_at or expires_at < utcnow():
        raise HTTPException(404, "Pairing code is invalid or expired")
    if device.paired:
        raise HTTPException(409, "Pairing code has already been used")
    credential_id = str(uuid.uuid4())
    client_secret = secrets.token_urlsafe(32)
    credential = ClientCredential(
        id=credential_id,
        device_id=device.id,
        name=payload.client_name,
        secret_hash=digest(client_secret),
    )
    device.paired = True
    db.add(credential)
    db.commit()
    return {
        "ok": True,
        "device_id": device.id,
        "name": device.name,
        "client_token": f"{credential_id}.{client_secret}",
        "mcp_url": "https://ai-bridge-cloud.onrender.com/mcp",
    }


@app.get("/v1/plugin/poll")
def plugin_poll(authorization: str | None = Header(default=None), db: Session = Depends(database)):
    device = authenticate_device(authorization, db)
    device.last_seen_at = utcnow()
    expires_at = device.pairing_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not device.paired and expires_at < utcnow():
        device.pairing_code = pairing_code()
        device.pairing_expires_at = utcnow() + timedelta(minutes=10)
    command = db.scalar(
        select(Command)
        .where(Command.device_id == device.id, Command.status == "pending")
        .order_by(Command.created_at)
        .limit(1)
    )
    if command:
        command.status = "running"
        command.updated_at = utcnow()
    db.commit()
    return {
        "ok": True,
        "paired": device.paired,
        "pairing_code": None if device.paired else device.pairing_code,
        "command": None if not command else {
            "id": command.id,
            "client": command.client,
            "action": command.action,
            "args": command.arguments,
        },
    }


@app.post("/v1/plugin/result/{command_id}")
def plugin_result(command_id: str, payload: CommandResult, authorization: str | None = Header(default=None), db: Session = Depends(database)):
    device = authenticate_device(authorization, db)
    command = db.get(Command, command_id)
    if not command or command.device_id != device.id:
        raise HTTPException(404, "Command not found")
    command.status = "done" if payload.ok else "error"
    command.result = {"ok": payload.ok, "data": payload.data}
    command.updated_at = utcnow()
    db.commit()
    return {"ok": True}


@app.get("/v1/client/status")
def client_status(authorization: str | None = Header(default=None), db: Session = Depends(database)):
    credential = authenticate_client(authorization, db)
    device = credential.device
    return {
        "ok": True,
        "client": credential.name,
        "device_id": device.id,
        "device_name": device.name,
        "studio_online": bool(device.last_seen_at and device.last_seen_at > utcnow() - timedelta(seconds=15)),
    }


@app.post("/v1/client/commands")
def client_create_command(payload: ClientCommand, authorization: str | None = Header(default=None), db: Session = Depends(database)):
    credential = authenticate_client(authorization, db)
    command = queue_command(db, credential.device_id, credential.name, payload.action, payload.args)
    return {"ok": True, "command_id": command.id}


@app.get("/v1/client/commands/{command_id}")
def client_get_command(command_id: str, authorization: str | None = Header(default=None), db: Session = Depends(database)):
    credential = authenticate_client(authorization, db)
    command = db.get(Command, command_id)
    if not command or command.device_id != credential.device_id:
        raise HTTPException(404, "Command not found")
    return {"id": command.id, "status": command.status, "result": command.result}


@app.post("/mcp", include_in_schema=False)
async def mcp_endpoint(request: Request, authorization: str | None = Header(default=None), db: Session = Depends(database)):
    credential = authenticate_client(authorization, db)
    message = await request.json()
    request_id = message.get("id")
    method = message.get("method")
    if request_id is None:
        return Response(status_code=202)
    if method == "initialize":
        result = {
            "protocolVersion": "2025-06-18",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "AI Bridge", "version": "0.2.0"},
        }
    elif method == "tools/list":
        result = {"tools": MCP_TOOLS}
    elif method == "tools/call":
        params = message.get("params") or {}
        tool_name = params.get("name")
        if tool_name not in {tool["name"] for tool in MCP_TOOLS}:
            return JSONResponse({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": "Unknown tool"}}, status_code=400)
        command = queue_command(db, credential.device_id, credential.name, tool_name, params.get("arguments") or {})
        deadline = utcnow() + timedelta(seconds=45)
        while utcnow() < deadline:
            await asyncio.sleep(0.4)
            db.expire_all()
            current = db.get(Command, command.id)
            if current and current.status in {"done", "error"}:
                payload = current.result or {"ok": False, "data": "No result returned"}
                result = {
                    "content": [{"type": "text", "text": json.dumps(payload.get("data"), ensure_ascii=False)}],
                    "isError": current.status == "error" or not payload.get("ok", False),
                }
                break
        else:
            result = {"content": [{"type": "text", "text": "Roblox Studio did not answer within 45 seconds."}], "isError": True}
    else:
        return JSONResponse({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Method not found"}}, status_code=404)
    return JSONResponse({"jsonrpc": "2.0", "id": request_id, "result": result})


@app.post("/v1/commands", dependencies=[Depends(require_api_key)])
def create_command(payload: CreateCommand, db: Session = Depends(database)):
    device = db.get(Device, payload.device_id)
    if not device or not device.paired:
        raise HTTPException(404, "Paired device not found")
    command = queue_command(db, device.id, payload.client, payload.action, payload.args)
    return {"ok": True, "command_id": command.id}


@app.get("/v1/commands/{command_id}", dependencies=[Depends(require_api_key)])
def get_command(command_id: str, db: Session = Depends(database)):
    command = db.get(Command, command_id)
    if not command:
        raise HTTPException(404, "Command not found")
    return {"id": command.id, "status": command.status, "result": command.result}
