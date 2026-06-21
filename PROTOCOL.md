# AI Bridge Protocol v0.2

Domyślny adres: `http://127.0.0.1:32145`

Każde żądanie musi zawierać nagłówek:

```text
X-Bridge-Token: <local token>
```

## Sprawdzenie połączenia

```http
GET /health
```

## Wysłanie polecenia

```http
POST /command
Content-Type: application/json

{
  "client": "My AI Agent",
  "action": "create_instance",
  "args": {
    "parent": "game/Workspace",
    "className": "Part",
    "name": "AIBlock"
  }
}
```

Odpowiedź zawiera `command_id`. Klient odpytuje o rezultat:

```http
GET /result/<command_id>
```

## Operacje v0.2

- `ping`
- `get_tree`
- `create_instance`
- `set_properties`
- `move_instance`
- `delete_instance`

Serwer i protokół nie wymagają konkretnego dostawcy AI. Integracja może używać
CLI, własnego agenta, aplikacji desktopowej albo bezpośrednich żądań HTTP.
Pole `client` jest opcjonalną nazwą wyświetlaną użytkownikowi w panelu Studio.
