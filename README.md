# AI Bridge

**Connect Roblox Studio to any AI.**

AI Bridge to lokalny, tokenizowany most pomiędzy Roblox Studio i dowolnym
klientem AI, który potrafi wysyłać żądania HTTP lub uruchomić nasze CLI. Codex,
Claude, Gemini i lokalne modele korzystają z tego samego neutralnego protokołu.

## Uruchomienie

Najprościej uruchom `start_ai_bridge.bat`. Otworzy się aplikacja AI Bridge Desktop,
która uruchamia lokalny serwer, pokazuje połączenie ze Studio i przygotowuje
konfigurację MCP dla klientów AI.

Uruchomienie ręczne:

1. Uruchom lokalny serwer:

   ```powershell
   python .\server.py
   ```

2. Token jest zapisywany przez serwer w `.bridge-token`.
3. W Roblox Studio włącz `Plugin Debugging Enabled`, utwórz `Script` w
   `ServerStorage` i wklej kod pluginu.
4. Zaznacz skrypt i wybierz **Plugins → Save as Local Plugin**.
5. Włącz **Game Settings → Security → Allow HTTP Requests**.
6. Otwórz panel **AI Bridge**. Plugin automatycznie sparuje się z uruchomioną
   aplikacją desktopową i zapamięta połączenie lokalnie.

Test:

```powershell
python .\bridge_cli.py ping
```

## Klienci AI

Plugin nie zna marki ani modelu AI. Każdy klient łączy się z lokalnym serwerem
przez opisany w `PROTOCOL.md` protokół. Dzięki temu jedna instalacja pluginu może
obsługiwać różne aplikacje i agentów bez zmiany kodu w Roblox Studio.

`mcp_server.py` jest lokalnym adapterem MCP stdio. Aplikacja desktopowa potrafi
skopiować gotową komendę dla Codexa, konfigurację dla Claude oraz ścieżkę serwera
dla innych klientów MCP. ChatGPT wymaga dodatkowo bezpiecznego endpointu MCP
przez HTTPS; surowy port mostu nigdy nie powinien być publikowany w internecie.

## Logo

Główne logo znajduje się w `assets/ai-bridge-logo.png`. Aby użyć go jako ikony
pluginu w Studio lub Creator Store, trzeba wgrać obraz do Roblox i podstawić
otrzymany identyfikator `rbxassetid`.

## Bezpieczeństwo

Serwer nasłuchuje wyłącznie na `127.0.0.1`, wymaga tokenu i nie pozwala na
wykonywanie dowolnego kodu Luau przesłanego przez HTTP. Token nie jest częścią
publikowanego pluginu; Studio zapisuje go lokalnie dla danego użytkownika.
