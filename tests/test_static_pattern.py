"""Tests for the static pattern handler."""

import json

import pytest

from mirage.engine.patterns.static import make_static_handler
from mirage.loader.yaml_loader import EndpointDef


def _make_endpoint(method: str, path: str, response: dict) -> EndpointDef:
    return EndpointDef(method=method, path=path, step=None, response=response)


# ---------------------------------------------------------------------------
# Handler construction
# ---------------------------------------------------------------------------


def test_handler_is_callable():
    ep = _make_endpoint("POST", "/leanpms/token", {"status": 200, "body": {"token": "abc"}})
    handler = make_static_handler(ep)
    assert callable(handler)


def test_handler_has_unique_name():
    ep = _make_endpoint("POST", "/leanpms/token", {"status": 200, "body": {"token": "abc"}})
    handler = make_static_handler(ep)
    assert "static" in handler.__name__


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_returns_body_from_yaml():
    ep = _make_endpoint(
        "POST", "/leanpms/token",
        {"status": 200, "body": {"token": "2893e0a65fcfffcbb86e16fb1bc1c612fcd3eb78"}},
    )
    handler = make_static_handler(ep)
    response = await handler()

    body = json.loads(response.body)
    assert response.status_code == 200
    assert body == {"token": "2893e0a65fcfffcbb86e16fb1bc1c612fcd3eb78"}


@pytest.mark.asyncio
async def test_respects_custom_status_code():
    ep = _make_endpoint("GET", "/health", {"status": 204, "body": {}})
    handler = make_static_handler(ep)
    response = await handler()
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_defaults_to_200_when_status_absent():
    ep = _make_endpoint("POST", "/token", {"body": {"token": "abc"}})
    handler = make_static_handler(ep)
    response = await handler()
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_empty_body_when_body_absent():
    ep = _make_endpoint("POST", "/token", {"status": 200})
    handler = make_static_handler(ep)
    response = await handler()
    body = json.loads(response.body)
    assert body == {}


@pytest.mark.asyncio
async def test_arbitrary_body_shape():
    ep = _make_endpoint(
        "POST", "/auth/session",
        {"status": 201, "body": {"sessionId": "xyz", "expiresIn": 86400, "roles": ["admin"]}},
    )
    handler = make_static_handler(ep)
    response = await handler()
    body = json.loads(response.body)
    assert body["sessionId"] == "xyz"
    assert body["expiresIn"] == 86400
    assert body["roles"] == ["admin"]
