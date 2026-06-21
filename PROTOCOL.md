# AI Bridge Cloud Protocol v0.3

Adres usługi: `https://ai-bridge-cloud.onrender.com`

## Plugin Roblox Studio

1. `POST /v1/plugins/register` zwraca token pluginu i kod parowania.
2. `GET /v1/plugin/poll` odbiera polecenia. Wymaga tokenu pluginu Bearer.
3. `POST /v1/plugin/result/{command_id}` odsyła wynik do chmury.

## Klient AI

1. `POST /v1/pair/claim` wymienia jednorazowy kod na prywatny token klienta.
2. `POST /v1/client/commands` kolejkuje polecenie.
3. `GET /v1/client/commands/{command_id}` zwraca stan i wynik.

Każde żądanie klienta po sparowaniu zawiera:

```text
Authorization: Bearer <client token>
```

## MCP

Zdalny endpoint MCP znajduje się pod `/mcp` i używa tego samego nagłówka Bearer.
Udostępnia narzędzia: `ping`, `get_tree`, `create_instance`, `set_properties`,
`move_instance` i `delete_instance`.

Kod parowania wygasa po 10 minutach i można go użyć tylko raz. Token pluginu i
token klienta są niezależne; klient AI nigdy nie otrzymuje sekretu pluginu.
