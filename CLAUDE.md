Create a CLAUDE.md file in the root of this repo with the following content — 
this will serve as the persistent context for our entire project:

---

# Mirage — Project Context for Claude Code

## Instructions for Claude
- After completing any module or making any meaningful progress, update PLAN.md immediately:
  mark the module as Done, update the Next pointer, and log any decisions made.
- Update CLAUDE.md whenever something architectural changes: new pattern added, YAML schema
  updated, data model revised, or a significant design decision is locked in.
- Read PLAN.md at the start of every session to orient yourself before doing anything.
- Never leave either file stale — they are the source of truth between sessions.

## What is Mirage
Mirage is an open source stateful API mock server for integration testing.
It reads partner definition YAML files and dynamically registers HTTP endpoints at startup.
No hardcoded routes — adding a new partner means writing a YAML file, nothing else.

## Origin and motivation
Built by Héctor Sanhueso, Lead Integration Solutions Engineer with 15 years of experience
in integration platforms (NiFi, Groovy, XSLT, AWS/Bedrock, K8s). Mirage replaces a fragile
NiFi-based mock that exists at Duetto (hospitality tech SaaS) and generalizes the concept
for any integration team needing to simulate stateful partner APIs.

## Tech stack
- Python
- FastAPI (dynamic route registration at startup)
- SQLite (session and payload persistence via session_store)
- PyYAML (partner definition loader)
- Uvicorn (ASGI server)
- Click (CLI)

## Project structure
mirage/
├── mirage/
│   ├── engine/
│   │   ├── patterns/
│   │   │   ├── oauth.py       # handles OAuth token pattern
│   │   │   ├── poll.py        # handles POST→HEAD→GET async sequence
│   │   │   └── push.py        # future: handles outbound push pattern
│   │   ├── session_store.py   # SQLite: sessions and payload persistence
│   │   └── router.py          # reads YAMLs, registers FastAPI routes dynamically
│   ├── api/
│   │   └── server.py          # FastAPI app + fixed admin endpoints
│   ├── loader/
│   │   └── yaml_loader.py     # parses partner YAML into Python objects
│   └── cli.py                 # Click CLI: mirage start, mirage status
├── partners/
│   └── ohip/
│       ├── partner.yaml       # OHIP partner definition
│       └── payloads/          # uploaded payload files live here
├── tests/
├── pyproject.toml
└── README.md

## POC scope: OHIP reservations only

### Consumer endpoints (dynamic, generated from YAML)
POST   /oauth/token                          → hardcoded JWT (pattern: oauth)
POST   /ohip/reservations                    → 202 + Location header with UUID (poll step 1)
HEAD   /ohip/reservations/{uuid}             → 201 + status COMPLETED (poll step 2)
GET    /ohip/reservations/{uuid}             → 200 + stored payload (poll step 3)

### Admin endpoints (dynamic, generated from YAML)
POST   /mirage/admin/ohip/reservation/payload          → upload global payload
POST   /mirage/admin/ohip/reservation/payload/session  → upload session payload, returns session_id

### Fixed infra endpoints (hardcoded)
GET    /mirage/admin/sessions   → list active sessions
GET    /mirage/admin/partners   → list loaded partners

## Payload storage: two modes
- Global mode: payload uploaded without session_id. Last write wins.
  Used when the consumer system cannot send custom headers (e.g. existing Duetto integration).
- Session mode: payload uploaded via /session endpoint, returns session_id.
  Consumer includes X-Mirage-Session header in POST to /ohip/reservations.
  Allows multiple users to work in parallel without overwriting each other.

Resolution logic on GET /ohip/reservations/{uuid}:
  1. If X-Mirage-Session header present → look up session payload → 404 if not found
  2. If no header → look up global payload for that datapoint → 404 if not found

## Pattern vocabulary (partner-agnostic)
- oauth: fixed token response, no state
- poll: consumer polls partner for data — POST→HEAD→GET async sequence with state
- poll_paginated: poll with offset-based pagination logic (future)
- push: consumer pushes data to partner — future

## Data model (loader/yaml_loader.py)

Three dataclasses mirror three levels of hierarchy in the YAML and serve distinct roles:

**PartnerDef** — one per YAML file; represents an entire external system (e.g. OHIP).
Top-level container the router iterates over at startup. The partner name drives admin
route generation: `/mirage/admin/{partner}/{datapoint}/payload`.

**DatapointDef** — one per logical capability within a partner (e.g. "reservation", "token").
This is the unit of payload storage: the session store is keyed by (partner, datapoint),
not by individual HTTP route. A datapoint owns a single pattern and groups all the HTTP
endpoints that implement it together.

**EndpointDef** — one per HTTP route (method + path + response config).
A datapoint may need several endpoints: the poll pattern always produces three
(POST / HEAD / GET). The router registers exactly one FastAPI route per EndpointDef.

Key insight: you upload a payload for "ohip/reservation" (datapoint level), not for
"GET /ohip/reservations/{uuid}" (endpoint level). Multiple endpoints within the same
datapoint share access to that one payload.

## YAML schema decisions
- All response config lives inside the endpoint block (not at datapoint level).
  Keeps the structure uniform across oauth and poll — every endpoint is self-contained.
- Poll endpoints carry a `step` field (1/2/3) so the router can wire them in order
  without relying on list position.