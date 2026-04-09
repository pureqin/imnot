# Mirage

Mirage is a stateful API mock server for integration testing.

Define a partner's API as a YAML file, run `mirage start`, and you get a fully functional
mock server — no code changes required to add new partners or endpoints.

## How it works

- **Partner definitions** live in `partners/<name>/partner.yaml`. Each file declares the
  partner's endpoints, the interaction pattern each endpoint follows, and the expected
  response shape.
- **Patterns** capture common async API idioms:
  - `oauth` — client-credentials token endpoint that returns a JWT.
  - `poll` — three-step async flow: submit → poll for readiness → fetch result.
  - `push` — Mirage proactively delivers a payload to a callback URL (future).
- **Payload storage** supports two modes:
  - *Global* — one payload per datapoint, last write wins.
  - *Session* — isolated payload per test run, selected via `X-Mirage-Session` header.
- **Admin API** is always available at `/mirage/admin/` for uploading payloads and
  inspecting sessions.

## Quick start

```bash
# Install
pip install -e .

# Start the server (loads all partner YAMLs automatically)
mirage start

# Upload a global payload for OHIP reservations
curl -X POST http://localhost:8000/mirage/admin/ohip/reservation/payload \
     -H "Content-Type: application/json" \
     -d @partners/ohip/payloads/reservation_example.json

# Run the OHIP reservation flow
curl -X POST http://localhost:8000/oauth/token
curl -X POST http://localhost:8000/ohip/reservations
curl -I       http://localhost:8000/ohip/reservations/<uuid>
curl          http://localhost:8000/ohip/reservations/<uuid>
```

## Session-isolated testing

```bash
# Upload a session-scoped payload — returns a session_id
SESSION=$(curl -s -X POST http://localhost:8000/mirage/admin/ohip/reservation/payload/session \
               -H "Content-Type: application/json" \
               -d @my_payload.json | jq -r .session_id)

# Use the session in your test
curl -X POST http://localhost:8000/ohip/reservations -H "X-Mirage-Session: $SESSION"
```

## Project structure

```
mirage/
├── mirage/
│   ├── api/           # FastAPI app factory
│   ├── engine/
│   │   ├── patterns/  # oauth / poll / push handlers
│   │   ├── router.py  # dynamic route registration
│   │   └── session_store.py  # SQLite persistence
│   ├── loader/        # YAML partner definition parser
│   └── cli.py         # mirage start / mirage status
├── partners/
│   └── ohip/
│       ├── partner.yaml
│       └── payloads/  # example payload files
└── tests/
```

## CLI

| Command | Description |
|---------|-------------|
| `mirage start` | Load all partner YAMLs and start the server |
| `mirage status` | Show active sessions |
