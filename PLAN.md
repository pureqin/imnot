# Mirage — Build Plan

Read this file at the start of any session to get current build state.
Update it as each module is completed.

---

## Status

| Module | File | Status | Notes |
|--------|------|--------|-------|
| Project scaffold | `pyproject.toml`, all `__init__.py` | Done | `.venv` created, dev extras working |
| Partner YAML | `partners/ohip/partner.yaml` | Done | Full OHIP reservation flow defined |
| YAML loader | `mirage/loader/yaml_loader.py` | Done | Parses YAML → `PartnerDef` / `DatapointDef` / `EndpointDef`; 7 tests passing |
| Session store | `mirage/engine/session_store.py` | Done | SQLite, 3 tables, 12 tests passing |
| OAuth pattern | `mirage/engine/patterns/oauth.py` | Done | Factory returns route handler; 5 tests passing |
| Poll pattern | `mirage/engine/patterns/poll.py` | Done | Factory returns {step: handler}; 12 tests passing |
| Dynamic router | `mirage/engine/router.py` | **Next** | |
| App factory | `mirage/api/server.py` | Pending | |
| CLI | `mirage/cli.py` | Pending | |

---

## Build order and rationale

```
yaml_loader  →  session_store  →  patterns/oauth  →  patterns/poll
                                                            ↓
                                               router  →  server  →  cli
```

- `session_store` before patterns: both oauth and poll need to read/write payloads and sessions.
- Patterns before router: router composes pattern handlers, so handlers must exist first.
- Router before server: server mounts the router onto the FastAPI app.
- Server before CLI: CLI calls server to start uvicorn.

---

## Session store — implemented

SQLite tables:
- `global_payloads (partner, datapoint, payload JSON, updated_at)` — upsert, last write wins
- `sessions (session_id, partner, datapoint, payload JSON, created_at)` — one row per session upload
- `poll_requests (uuid, partner, datapoint, session_id nullable, created_at)` — created at poll step 1, read at step 3

Public API on `SessionStore`:
- `init()` / `close()` — lifecycle
- `store_global_payload(partner, datapoint, payload)`
- `store_session_payload(partner, datapoint, payload) → session_id`
- `register_poll_request(partner, datapoint, session_id) → uuid`
- `get_poll_request(uuid) → Row | None`
- `resolve_payload(partner, datapoint, session_id | None) → dict | None`
- `list_sessions() → list[dict]`

## Testing plan

### Layers

| Layer | Tool | When to run | What it covers |
|-------|------|-------------|----------------|
| Unit | pytest | Every module, always | Individual functions and classes in isolation (loader, store, pattern handlers) |
| Integration | pytest + FastAPI TestClient | After router + server are done | Full HTTP request/response cycle through the real app, in-process, no server needed |
| End-to-end (manual) | curl | Final smoke test before calling it done | Real `mirage start` on localhost, curl through the entire OHIP flow |

### Integration test plan (to implement once server is ready)

Full OHIP reservation flow in a single test:
1. `POST /oauth/token` → assert 200 + Bearer token in body
2. Upload global payload via `POST /mirage/admin/ohip/reservation/payload`
3. `POST /ohip/reservations` → assert 202 + `Location` header contains a UUID
4. `HEAD /ohip/reservations/{uuid}` → assert 201 + `Status: COMPLETED` header
5. `GET /ohip/reservations/{uuid}` → assert 200 + body matches uploaded payload

Session-isolated variant of the same flow:
1. Upload payload via `POST /mirage/admin/ohip/reservation/payload/session` → capture `session_id`
2. `POST /ohip/reservations` with `X-Mirage-Session: {session_id}` → capture UUID
3. `GET /ohip/reservations/{uuid}` with `X-Mirage-Session: {session_id}` → assert payload matches
4. `GET /ohip/reservations/{uuid}` without session header → assert 404 (no global payload)

Admin endpoints:
- `GET /mirage/admin/sessions` → assert session appears after session upload
- `GET /mirage/admin/partners` → assert ohip appears on startup

### End-to-end curl script (to add to repo once server is running)

Will live at `scripts/smoke_test.sh` — runs the full OHIP flow against localhost:8000.

## Dynamic router — design notes (next module)

`register_routes(app: FastAPI, partners: list[PartnerDef], store: SessionStore)`

For each partner → each datapoint:
- If pattern == "oauth": call `make_oauth_handler(endpoint)`, register with `app.add_api_route`
- If pattern == "poll": call `make_poll_handlers(partner, datapoint, store)`, register each
  step handler against its endpoint's method + path

Admin payload endpoints (dynamic, one pair per datapoint):
- `POST /mirage/admin/{partner}/{datapoint}/payload`         → store global payload
- `POST /mirage/admin/{partner}/{datapoint}/payload/session` → store session payload, return `{"session_id": "..."}`

Fixed infra endpoints (always registered):
- `GET /mirage/admin/sessions`  → `store.list_sessions()`
- `GET /mirage/admin/partners`  → list of loaded partner names + datapoint counts

---

## Open questions / decisions log

| # | Question | Decision |
|---|----------|----------|
| 1 | Response config at datapoint vs endpoint level in YAML? | Inside endpoint — keeps structure uniform, every endpoint self-contained |
| 2 | PLAN.md vs stuffing status into CLAUDE.md? | PLAN.md for living state; CLAUDE.md for stable architectural facts only |
