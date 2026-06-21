# AI Bridge — Quick Start

## 1. Start the desktop app

Run `AIBridge.exe` and click **Start bridge**.

## 2. Install the Roblox Studio plugin

1. Open Roblox Studio and enable **Plugin Debugging Enabled**.
2. Insert a `Script` into `ServerStorage`.
3. Paste the contents of `AIBridgePlugin.lua`.
4. Select the script and choose **Plugins → Save as Local Plugin**.
5. Enable **Game Settings → Security → Allow HTTP Requests**.
6. Open the AI Bridge panel. It pairs with the desktop app automatically while
   the pairing window is open. No token copying is required.

The desktop app should show **Roblox Studio: connected**.

## 3. Connect an AI client

- **Codex:** click **Copy setup command** and run the copied command once.
- **Claude:** click **Copy config** and merge it into Claude's MCP configuration.
- **Other MCP clients:** use the path shown by **Copy server path**.
- **ChatGPT:** requires a secure HTTPS MCP endpoint and is not enabled by the
  local-only 0.3 release.

Never publish port `32145` directly to the internet.
