"""
Dynamic router: registers FastAPI routes at startup from partner definitions.

Responsibilities:
- Accept a list of parsed PartnerDefinition objects.
- For each datapoint in each partner, create the appropriate route handler
  by delegating to the matching pattern module (oauth, poll, push).
- Register consumer endpoints (e.g. POST /ohip/reservations) on the FastAPI app.
- Register admin payload endpoints:
    POST /mirage/admin/{partner}/{datapoint}/payload         (global)
    POST /mirage/admin/{partner}/{datapoint}/payload/session (session-scoped)
- Register fixed infra endpoints:
    GET /mirage/admin/sessions
    GET /mirage/admin/partners
"""
