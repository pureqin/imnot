"""
Poll pattern handler.

Responsibilities:
- Expose a factory function `make_poll_handlers` that accepts a partner name,
  a DatapointDef, and a SessionStore instance, and returns a dict mapping
  step number → FastAPI route coroutine for each of the three poll steps.

Step 1 (POST):  accept the request, register a poll entry in the store, return
                202 + Location header pointing to the polling URL.
Step 2 (HEAD):  return the configured status code + any response headers from YAML
                (e.g. Status: COMPLETED). No store interaction.
Step 3 (GET):   validate the UUID exists, resolve the payload via the store respecting
                the X-Mirage-Session header, return 200 + payload or 404.
"""

from __future__ import annotations

from typing import Any, Callable

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from mirage.engine.session_store import SessionStore
from mirage.loader.yaml_loader import DatapointDef, EndpointDef


def make_poll_handlers(
    partner: str,
    datapoint: DatapointDef,
    store: SessionStore,
) -> dict[int, Callable]:
    """Return {step: handler} for all poll endpoints in *datapoint*."""

    steps: dict[int, EndpointDef] = {ep.step: ep for ep in datapoint.endpoints}

    handlers: dict[int, Callable] = {}

    if 1 in steps:
        handlers[1] = _make_step1(partner, datapoint, steps[1], store)
    if 2 in steps:
        handlers[2] = _make_step2(datapoint, steps[2])
    if 3 in steps:
        handlers[3] = _make_step3(partner, datapoint, steps[3], store)

    return handlers


# ---------------------------------------------------------------------------
# Step builders
# ---------------------------------------------------------------------------


def _make_step1(
    partner: str,
    datapoint: DatapointDef,
    endpoint: EndpointDef,
    store: SessionStore,
) -> Callable:
    dp_name = datapoint.name
    status_code: int = endpoint.response.get("status", 202)
    location_template: str = endpoint.response.get("location_template", "/{uuid}")

    async def step1(request: Request) -> Response:
        session_id: str | None = request.headers.get("X-Mirage-Session")
        async_uuid = store.register_async_request(
            partner=partner,
            datapoint=dp_name,
            session_id=session_id,
        )
        location = location_template.format(uuid=async_uuid)
        return Response(
            status_code=status_code,
            headers={"Location": location},
        )

    step1.__name__ = f"poll_step1_{partner}_{dp_name}"
    return step1


def _make_step2(
    datapoint: DatapointDef,
    endpoint: EndpointDef,
) -> Callable:
    dp_name = datapoint.name
    status_code: int = endpoint.response.get("status", 201)
    extra_headers: dict[str, str] = endpoint.response.get("headers", {})

    async def step2(uuid: str) -> Response:
        return Response(
            status_code=status_code,
            headers=extra_headers,
        )

    step2.__name__ = f"poll_step2_{datapoint.name}"
    return step2


def _make_step3(
    partner: str,
    datapoint: DatapointDef,
    endpoint: EndpointDef,
    store: SessionStore,
) -> Callable:
    dp_name = datapoint.name
    status_code: int = endpoint.response.get("status", 200)

    async def step3(uuid: str, request: Request) -> Response:
        async_row = store.get_async_request(uuid)
        if async_row is None:
            return JSONResponse(
                status_code=404,
                content={"detail": f"Unknown request UUID: {uuid}"},
            )

        session_id: str | None = request.headers.get("X-Mirage-Session")
        payload: dict[str, Any] | None = store.resolve_payload(
            partner=partner,
            datapoint=dp_name,
            session_id=session_id,
        )

        if payload is None:
            detail = (
                f"No session payload found for session '{session_id}'"
                if session_id
                else f"No global payload found for {partner}/{dp_name}"
            )
            return JSONResponse(status_code=404, content={"detail": detail})

        return JSONResponse(status_code=status_code, content=payload)

    step3.__name__ = f"poll_step3_{partner}_{dp_name}"
    return step3
