"""
Static pattern handler.

Responsibilities:
- Expose a factory function `make_static_handler` that accepts an EndpointDef
  and returns a FastAPI route coroutine.
- The handler responds with exactly the JSON body defined under `response.body`
  in the YAML. No payload storage, no state — purely fixed.
- Use this pattern for any endpoint whose response is fully known at YAML
  authoring time and never changes (e.g. non-standard token endpoints,
  health checks, fixed capability documents).
"""

from __future__ import annotations

from typing import Any, Callable

from fastapi import Response
from fastapi.responses import JSONResponse

from mirage.loader.yaml_loader import EndpointDef


def make_static_handler(endpoint: EndpointDef) -> Callable[[], Response]:
    """Return a FastAPI route handler for the given static EndpointDef."""

    response_cfg: dict[str, Any] = endpoint.response
    status_code: int = response_cfg.get("status", 200)
    body: dict[str, Any] = response_cfg.get("body") or {}

    async def handler() -> JSONResponse:
        return JSONResponse(status_code=status_code, content=body)

    handler.__name__ = f"static_{endpoint.method}_{endpoint.path.replace('/', '_').strip('_')}"

    return handler
