# AI Bridge

**Connect Roblox Studio to any AI.**

AI Bridge jest neutralnym mostem pomiędzy Roblox Studio a klientami AI. Plugin
łączy się bezpośrednio z bezpiecznym serwerem HTTPS, więc użytkownik nie musi
instalować aplikacji `.exe` ani uruchamiać lokalnego serwera.

## Jak to działa

1. Plugin rejestruje Studio w chmurze i pokazuje jednorazowy kod.
2. Użytkownik wpisuje kod na stronie `/connect`.
3. Strona wydaje prywatny token klienta AI.
4. AI korzysta ze zdalnego MCP lub neutralnego REST API.
5. Plugin odbiera dozwolone polecenia, wykonuje je w Studio i odsyła wynik.

Pełna instrukcja: [QUICKSTART.md](QUICKSTART.md). Protokół:
[PROTOCOL.md](PROTOCOL.md).

## Obsługiwane operacje

- odczyt drzewa instancji,
- tworzenie instancji,
- zmiana właściwości,
- przenoszenie i usuwanie instancji,
- test połączenia.

Plugin celowo nie wykonuje dowolnego kodu Luau przesłanego przez internet.

## Usługi

- Strona i parowanie: <https://ai-bridge-cloud.onrender.com/connect>
- Remote MCP: `https://ai-bridge-cloud.onrender.com/mcp`
- Schemat dla ChatGPT Actions: <https://ai-bridge-cloud.onrender.com/ai-openapi.json>
- Dokumentacja API: <https://ai-bridge-cloud.onrender.com/docs>

## Logo

Logo produktu znajduje się w `assets/ai-bridge-logo.png`. Ikona pluginu używa
zasobu Roblox `rbxassetid://95427397446061`.
