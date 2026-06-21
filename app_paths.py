"""Shared writable and bundled paths for AI Bridge."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


APP_NAME = "AI Bridge"
VERSION = "0.4.0"
SOURCE_ROOT = Path(__file__).resolve().parent
DATA_ROOT = Path(os.getenv("LOCALAPPDATA", Path.home())) / "AIBridge"
DATA_ROOT.mkdir(parents=True, exist_ok=True)
TOKEN_FILE = DATA_ROOT / "bridge-token"
LOG_DIR = DATA_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def resource_path(relative: str) -> Path:
    bundle_root = Path(getattr(sys, "_MEIPASS", SOURCE_ROOT))
    return bundle_root / relative


def migrate_legacy_token() -> None:
    legacy = SOURCE_ROOT / ".bridge-token"
    if not TOKEN_FILE.exists() and legacy.exists():
        shutil.copy2(legacy, TOKEN_FILE)


migrate_legacy_token()
