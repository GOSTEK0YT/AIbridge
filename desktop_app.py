"""AI Bridge Desktop MVP built with the Python standard library."""

from __future__ import annotations

import json
import sys
import threading
import tkinter as tk
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import messagebox

from app_paths import TOKEN_FILE, VERSION, resource_path
from server import create_server, enable_pairing

BRIDGE_URL = "http://127.0.0.1:32145"


def mcp_command_path() -> str:
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).with_name("AIBridgeMCP.exe"))
    return str(resource_path("mcp_server.py"))


class AIBridgeApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("AI Bridge")
        self.geometry("900x720")
        self.minsize(820, 680)
        self.configure(bg="#090b12")
        self.http_server = None
        self.server_thread: threading.Thread | None = None
        self.token_visible = False
        self.actual_token = ""
        self.logo_image: tk.PhotoImage | None = None
        self._build_ui()
        self.after(400, self.refresh_status)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _label(self, parent, text, size=12, color="#dfe7ff", bold=False, **kwargs):
        font = ("Segoe UI", size, "bold" if bold else "normal")
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color, font=font, **kwargs)

    def _button(self, parent, text, command, color="#5b5cff"):
        return tk.Button(
            parent, text=text, command=command, bg=color, fg="white",
            activebackground=color, activeforeground="white", bd=0,
            padx=16, pady=9, cursor="hand2", font=("Segoe UI", 10, "bold"),
        )

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg="#0d101a", height=112)
        header.pack(fill="x")
        header.pack_propagate(False)
        logo_path = resource_path("assets/ai-bridge-logo.png")
        try:
            self.logo_image = tk.PhotoImage(file=str(logo_path)).subsample(12, 12)
            self.iconphoto(True, self.logo_image)
            tk.Label(header, image=self.logo_image, bg="#0d101a").pack(side="left", padx=(24, 12), pady=12)
        except tk.TclError:
            self._label(header, "AI", 30, "#6fe8ff", True).pack(side="left", padx=24)
        title_box = tk.Frame(header, bg="#0d101a")
        title_box.pack(side="left", pady=18)
        self._label(title_box, "AI BRIDGE", 25, "#ffffff", True).pack(anchor="w")
        self._label(title_box, "Connect Roblox Studio to any AI", 11, "#8da0c9").pack(anchor="w")
        self._label(header, "v" + VERSION, 9, "#667391", True).pack(side="right", padx=20, pady=20, anchor="ne")

        body = tk.Frame(self, bg="#090b12")
        body.pack(fill="both", expand=True, padx=24, pady=20)
        status_card = tk.Frame(body, bg="#131827", padx=20, pady=16)
        status_card.pack(fill="x")
        top = tk.Frame(status_card, bg="#131827")
        top.pack(fill="x")
        self.status_dot = self._label(top, "●", 18, "#7d8599", True)
        self.status_dot.pack(side="left")
        self.status_text = self._label(top, "Bridge stopped", 14, "#ffffff", True)
        self.status_text.pack(side="left", padx=8)
        self.toggle_button = self._button(top, "Start bridge", self.toggle_server)
        self.toggle_button.pack(side="right")
        self.studio_text = self._label(status_card, "Roblox Studio: waiting", 11, "#93a0bd")
        self.studio_text.pack(anchor="w", pady=(10, 0))
        self.client_text = self._label(status_card, "Active AI: none", 11, "#68d8ff")
        self.client_text.pack(anchor="w", pady=(4, 0))

        self.pairing_text = self._label(status_card, "Pairing: starts with the bridge", 10, "#f5bf63")
        self.pairing_text.pack(anchor="w", pady=(4, 0))

        token_row = tk.Frame(status_card, bg="#131827")
        token_row.pack(fill="x", pady=(12, 0))
        self._label(token_row, "No token copying required. Open the plugin and it pairs automatically.", 10, "#b9c4df").pack(side="left", fill="x", expand=True)
        self._button(token_row, "Advanced: copy token", self.copy_token, "#27304a").pack(side="right", padx=(8, 0))
        self._button(token_row, "Pair plugin", self.start_pairing, "#2a9d78").pack(side="right", padx=(8, 0))

        self._label(body, "AI clients", 16, "#ffffff", True).pack(anchor="w", pady=(22, 10))
        grid = tk.Frame(body, bg="#090b12")
        grid.pack(fill="both", expand=True)
        providers = [
            ("Codex", "Local MCP ready", "Copy setup command", self.copy_codex),
            ("Claude", "Local MCP ready", "Copy config", self.copy_claude),
            ("Gemini", "MCP adapter ready", "Copy server path", self.copy_mcp_path),
            ("ChatGPT", "Requires secure HTTPS MCP", "Open setup guide", self.open_chatgpt),
        ]
        for index, (name, status, action, callback) in enumerate(providers):
            card = tk.Frame(grid, bg="#131827", padx=18, pady=16)
            card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=(0 if index % 2 == 0 else 8, 0), pady=(0, 8))
            self._label(card, name, 15, "#ffffff", True).pack(anchor="w")
            self._label(card, status, 10, "#8fa0c2").pack(anchor="w", pady=(4, 12))
            self._button(card, action, callback, "#5d4fff" if name != "ChatGPT" else "#2a9d78").pack(anchor="w")
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        grid.grid_rowconfigure(0, weight=1)
        grid.grid_rowconfigure(1, weight=1)

    def read_token(self) -> str:
        return TOKEN_FILE.read_text(encoding="utf-8").strip() if TOKEN_FILE.exists() else ""

    def health(self) -> dict | None:
        current_token = self.read_token()
        if not current_token:
            return None
        request = urllib.request.Request(BRIDGE_URL + "/health", headers={"X-Bridge-Token": current_token})
        try:
            with urllib.request.urlopen(request, timeout=0.5) as response:
                return json.load(response)
        except Exception:
            return None

    def refresh_status(self) -> None:
        health = self.health()
        if health:
            self.status_dot.config(fg="#36df8a")
            self.status_text.config(text="Bridge running")
            self.toggle_button.config(text="Stop bridge", bg="#d34559", activebackground="#d34559")
            age = health.get("plugin_seen_seconds_ago")
            studio_ok = age is not None and age < 3
            self.studio_text.config(text="Roblox Studio: connected" if studio_ok else "Roblox Studio: waiting for plugin")
            self.client_text.config(text="Active AI: " + str(health.get("last_client", "none")))
            pairing_left = int(health.get("pairing_seconds_left") or 0)
            self.pairing_text.config(text=f"Pairing: open for {pairing_left}s" if pairing_left else "Pairing: closed")
            self.actual_token = self.read_token()
        else:
            self.status_dot.config(fg="#7d8599")
            self.status_text.config(text="Bridge stopped")
            self.toggle_button.config(text="Start bridge", bg="#5b5cff", activebackground="#5b5cff")
            self.studio_text.config(text="Roblox Studio: waiting")
            self.client_text.config(text="Active AI: none")
            self.pairing_text.config(text="Pairing: starts with the bridge")
        self.after(700, self.refresh_status)

    def toggle_server(self) -> None:
        if self.health():
            if self.http_server is not None:
                self.http_server.shutdown()
                self.http_server.server_close()
                self.http_server = None
                self.server_thread = None
            else:
                messagebox.showinfo("AI Bridge", "A bridge started outside this app is already running.")
            return
        try:
            self.http_server = create_server()
            enable_pairing(300)
            self.server_thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
            self.server_thread.start()
        except OSError as exc:
            self.http_server = None
            messagebox.showerror("AI Bridge", f"Could not start the local bridge:\n{exc}")

    def copy(self, value: str, message: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(value)
        messagebox.showinfo("AI Bridge", message)

    def copy_token(self) -> None:
        self.copy(self.actual_token or self.read_token(), "Bridge token copied.")

    def toggle_token(self) -> None:
        self.token_visible = not self.token_visible
        self.actual_token = self.read_token()

    def start_pairing(self) -> None:
        if not self.health():
            messagebox.showinfo("AI Bridge", "Start the bridge first.")
            return
        enable_pairing(300)
        messagebox.showinfo("AI Bridge", "Pairing is open for 5 minutes. Open the AI Bridge plugin in Roblox Studio.")

    def copy_mcp_path(self) -> None:
        self.copy(mcp_command_path(), "MCP server path copied.")

    def copy_codex(self) -> None:
        if getattr(sys, "frozen", False):
            command = f'codex mcp add ai-bridge -- "{mcp_command_path()}"'
        else:
            command = f'codex mcp add ai-bridge -- python "{resource_path("mcp_server.py")}"'
        self.copy(command, "Codex setup command copied.")

    def copy_claude(self) -> None:
        if getattr(sys, "frozen", False):
            config = {"mcpServers": {"ai-bridge": {"command": mcp_command_path(), "args": []}}}
        else:
            config = {"mcpServers": {"ai-bridge": {"command": sys.executable, "args": [str(resource_path("mcp_server.py"))]}}}
        self.copy(json.dumps(config, indent=2), "Claude MCP configuration copied.")

    def open_chatgpt(self) -> None:
        webbrowser.open("https://developers.openai.com/apps-sdk/deploy/connect-chatgpt")

    def on_close(self) -> None:
        if self.http_server is not None:
            self.http_server.shutdown()
            self.http_server.server_close()
        self.destroy()


if __name__ == "__main__":
    AIBridgeApp().mainloop()
