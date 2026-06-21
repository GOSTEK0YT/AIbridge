# AI Bridge — szybki start

## 1. Zainstaluj plugin w Roblox Studio

1. Włącz **Game Settings → Security → Allow HTTP Requests**.
2. Zainstaluj plugin zawierający `AIBridgePlugin.server.lua`.
3. Otwórz panel **AI Bridge** i kliknij **Connect**.
4. Plugin pokaże sześciocyfrowy kod.

Nie trzeba instalować ani uruchamiać aplikacji `.exe`.

## 2. Sparuj Studio

1. Otwórz <https://ai-bridge-cloud.onrender.com/connect>.
2. Wpisz kod z pluginu.
3. Zachowaj wygenerowany prywatny token klienta AI.

Kod parowania jest jednorazowy. Tokenu klienta nie publikuj i nie wysyłaj innym
osobom — pozwala on edytować sparowany projekt przez obsługiwane operacje.

## 3. Podłącz AI

- **Claude:** dodaj `https://ai-bridge-cloud.onrender.com/mcp` jako własny
  konektor. Na stronie zgody AI Bridge wklej prywatny token i zatwierdź dostęp.
- **Inny klient MCP:** użyj tego samego endpointu oraz nagłówka
  `Authorization: Bearer <token>`, jeśli klient obsługuje własne nagłówki.
- **ChatGPT Custom GPT:** zaimportuj
  `https://ai-bridge-cloud.onrender.com/ai-openapi.json` w sekcji Actions,
  wybierz uwierzytelnianie API Key typu Bearer i wklej token.
- **Własny agent REST:** użyj endpointów `/v1/client/*` opisanych pod `/docs`.

Plugin obsługuje wyłącznie jawnie dozwolone operacje i nie wykonuje dowolnego
kodu Luau otrzymanego z internetu.
