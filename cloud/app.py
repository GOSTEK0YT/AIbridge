"""AI Bridge Cloud API — pairing and command relay for Roblox Studio plugins."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
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
app = FastAPI(title="AI Bridge Cloud", version="0.1.0")


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


def require_api_key(x_ai_bridge_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("AI_BRIDGE_API_KEY", "dev-only-change-me")
    if not x_ai_bridge_key or not hmac.compare_digest(x_ai_bridge_key, expected):
        raise HTTPException(401, "Invalid AI Bridge API key")


class RegisterRequest(BaseModel):
    name: str = Field(default="Roblox Studio", max_length=100)


class PairClaim(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class CreateCommand(BaseModel):
    device_id: str
    client: str = Field(default="AI client", max_length=100)
    action: str = Field(max_length=64)
    args: dict = Field(default_factory=dict)


class CommandResult(BaseModel):
    ok: bool
    data: object | None = None


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
  <p><a href="/docs">Open API documentation &rarr;</a></p>
  <small>AI Bridge Cloud v0.1.0</small>
</main></body></html>"""


@app.get("/health")
def health():
    return {"ok": True, "service": "ai-bridge-cloud", "version": "0.1.0"}


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


@app.post("/v1/pair/claim", dependencies=[Depends(require_api_key)])
def claim_pairing(payload: PairClaim, db: Session = Depends(database)):
    device = db.scalar(select(Device).where(Device.pairing_code == payload.code))
    expires_at = device.pairing_expires_at if device else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not device or not expires_at or expires_at < utcnow():
        raise HTTPException(404, "Pairing code is invalid or expired")
    device.paired = True
    db.commit()
    return {"ok": True, "device_id": device.id, "name": device.name}


@app.get("/v1/plugin/poll")
def plugin_poll(authorization: str | None = Header(default=None), db: Session = Depends(database)):
    device = authenticate_device(authorization, db)
    device.last_seen_at = utcnow()
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


@app.post("/v1/commands", dependencies=[Depends(require_api_key)])
def create_command(payload: CreateCommand, db: Session = Depends(database)):
    device = db.get(Device, payload.device_id)
    if not device or not device.paired:
        raise HTTPException(404, "Paired device not found")
    command = Command(
        id=str(uuid.uuid4()),
        device_id=device.id,
        client=payload.client,
        action=payload.action,
        arguments=payload.args,
    )
    db.add(command)
    db.commit()
    return {"ok": True, "command_id": command.id}


@app.get("/v1/commands/{command_id}", dependencies=[Depends(require_api_key)])
def get_command(command_id: str, db: Session = Depends(database)):
    command = db.get(Command, command_id)
    if not command:
        raise HTTPException(404, "Command not found")
    return {"id": command.id, "status": command.status, "result": command.result}
