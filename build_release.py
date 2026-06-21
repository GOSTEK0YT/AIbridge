"""Build Windows product executables and a distributable ZIP."""

from __future__ import annotations

import hashlib
import shutil
import struct
import subprocess
import sys
import tkinter as tk
import zipfile
from pathlib import Path


ROOT = Path(__file__).parent.resolve()
VERSION = "0.4.0"
PRODUCT_NAME = f"AI-Bridge-{VERSION}-windows"
WORK = ROOT / "release-build"
DIST = ROOT / "dist"
RELEASE = ROOT / "release" / PRODUCT_NAME


def create_icon() -> Path:
    source = ROOT / "assets" / "ai-bridge-logo.png"
    WORK.mkdir(parents=True, exist_ok=True)
    resized = WORK / "ai-bridge-icon.png"
    icon = WORK / "ai-bridge.ico"
    window = tk.Tk()
    window.withdraw()
    image = tk.PhotoImage(file=str(source))
    factor = max(1, (max(image.width(), image.height()) + 255) // 256)
    small = image.subsample(factor, factor)
    small.write(str(resized), format="png")
    window.destroy()
    png = resized.read_bytes()
    width, height = struct.unpack(">II", png[16:24])
    directory = struct.pack(
        "<BBBBHHII", width if width < 256 else 0, height if height < 256 else 0,
        0, 0, 1, 32, len(png), 22,
    )
    icon.write_bytes(struct.pack("<HHH", 0, 1, 1) + directory + png)
    return icon


def run_pyinstaller(args: list[str]) -> None:
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", *args],
        cwd=ROOT,
        check=True,
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    for path in (WORK, DIST, RELEASE):
        if path.exists():
            shutil.rmtree(path)
    icon = create_icon()
    data_arg = f"{ROOT / 'assets' / 'ai-bridge-logo.png'};assets"
    run_pyinstaller([
        "--onefile", "--windowed", "--name", "AIBridge", "--icon", str(icon),
        "--add-data", data_arg, str(ROOT / "desktop_app.py"),
    ])
    run_pyinstaller([
        "--onefile", "--console", "--name", "AIBridgeMCP", "--icon", str(icon),
        str(ROOT / "mcp_server.py"),
    ])

    RELEASE.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DIST / "AIBridge.exe", RELEASE / "AIBridge.exe")
    shutil.copy2(DIST / "AIBridgeMCP.exe", RELEASE / "AIBridgeMCP.exe")
    shutil.copy2(ROOT / "AIBridgePlugin.server.lua", RELEASE / "AIBridgePlugin.lua")
    shutil.copy2(ROOT / "assets" / "ai-bridge-logo.png", RELEASE / "ai-bridge-logo.png")
    for name in ("QUICKSTART.md", "PRIVACY.md", "LICENSE.txt"):
        shutil.copy2(ROOT / name, RELEASE / name)

    files = [path for path in RELEASE.iterdir() if path.is_file()]
    checksums = "\n".join(f"{sha256(path)}  {path.name}" for path in sorted(files)) + "\n"
    (RELEASE / "SHA256SUMS.txt").write_text(checksums, encoding="utf-8")

    archive = ROOT / "release" / f"{PRODUCT_NAME}.zip"
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        for path in sorted(RELEASE.iterdir()):
            output.write(path, f"{PRODUCT_NAME}/{path.name}")
    print(archive)


if __name__ == "__main__":
    main()
