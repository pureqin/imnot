"""Tests for the async pattern handler."""

import json
from pathlib import Path

import pytest
from fastapi import Request

from mirage.engine.patterns.async_ import make_async_handlers
from mirage.engine.session_store import SessionStore
from mirage.loader.yaml_loader import DatapointDef, EndpointDef


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path):
    s = SessionStore(db_path=tmp_path / "test.db")
    s.init()
    yield s
    s.close()


def _make_datapoint(endpoints: list[EndpointDef]) -> DatapointDef:
    return DatapointDef(
        name="job",
        description="",
        pattern="async",
        endpoints=endpoints,
    )


def _request(headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    return Request({"type": "http", "headers": headers or []})


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def test_factory_returns_one_handler_per_step(store):
    endpoints = [
        EndpointDef(method="POST", path="/jobs", step=1,
                    response={"status": 202, "generates_id": True,
                              "id_header": "Location", "id_header_value": "/jobs/{id}"}),
        EndpointDef(method="GET", path="/jobs/{id}", step=2,
                    response={"status": 200, "returns_payload": True}),
    ]
    handlers = make_async_handlers("partner", _make_datapoint(endpoints), store)
    assert set(handlers.keys()) == {1, 2}
    assert all(callable(h) for h in handlers.values())


def test_handler_names_are_unique(store):
    endpoints = [
        EndpointDef(method="POST", path="/jobs", step=1,
                    response={"status": 202, "generates_id": True,
                              "id_header": "Location", "id_header_value": "/jobs/{id}"}),
        EndpointDef(method="GET", path="/jobs/{id}", step=2,
                    response={"status": 200, "returns_payload": True}),
    ]
    handlers = make_async_handlers("partner", _make_datapoint(endpoints), store)
    names = [h.__name__ for h in handlers.values()]
    assert len(names) == len(set(names))


# ---------------------------------------------------------------------------
# Submit handler — id_header delivery
# ---------------------------------------------------------------------------


@pytest.fixture
def header_submit_handler(store):
    ep = EndpointDef(
        method="POST", path="/jobs", step=1,
        response={
            "status": 202,
            "generates_id": True,
            "id_header": "Location",
            "id_header_value": "/jobs/{id}",
        },
    )
    return make_async_handlers("partner", _make_datapoint([ep]), store)[1]


@pytest.mark.asyncio
async def test_submit_header_returns_configured_status(header_submit_handler):
    response = await header_submit_handler(_request())
    assert response.status_code == 202


@pytest.mark.asyncio
async def test_submit_header_injects_uuid_into_header(header_submit_handler):
    response = await header_submit_handler(_request())
    location = response.headers.get("Location")
    assert location is not None
    assert location.startswith("/jobs/")
    uuid_part = location.split("/")[-1]
    assert len(uuid_part) == 36  # UUID


@pytest.mark.asyncio
async def test_submit_header_persists_uuid(header_submit_handler, store):
    response = await header_submit_handler(_request())
    uuid = response.headers["Location"].split("/")[-1]
    row = store.get_async_request(uuid)
    assert row is not None
    assert row["partner"] == "partner"
    assert row["datapoint"] == "job"
    assert row["session_id"] is None


@pytest.mark.asyncio
async def test_submit_header_persists_session_id(header_submit_handler, store):
    headers = [(b"x-mirage-session", b"test-session-abc")]
    response = await header_submit_handler(_request(headers))
    uuid = response.headers["Location"].split("/")[-1]
    row = store.get_async_request(uuid)
    assert row["session_id"] == "test-session-abc"


# ---------------------------------------------------------------------------
# Submit handler — id_body_field delivery
# ---------------------------------------------------------------------------


@pytest.fixture
def body_submit_handler(store):
    ep = EndpointDef(
        method="POST", path="/jobs", step=1,
        response={
            "status": 200,
            "generates_id": True,
            "id_body_field": "JobReferenceID",
        },
    )
    return make_async_handlers("partner", _make_datapoint([ep]), store)[1]


@pytest.mark.asyncio
async def test_submit_body_returns_configured_status(body_submit_handler):
    response = await body_submit_handler(_request())
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_submit_body_injects_uuid_into_body(body_submit_handler):
    response = await body_submit_handler(_request())
    body = json.loads(response.body)
    assert "JobReferenceID" in body
    assert len(body["JobReferenceID"]) == 36  # UUID


@pytest.mark.asyncio
async def test_submit_body_persists_uuid(body_submit_handler, store):
    response = await body_submit_handler(_request())
    uuid = json.loads(response.body)["JobReferenceID"]
    row = store.get_async_request(uuid)
    assert row is not None
    assert row["partner"] == "partner"
    assert row["datapoint"] == "job"


@pytest.mark.asyncio
async def test_submit_body_merges_static_body_fields(store):
    ep = EndpointDef(
        method="POST", path="/jobs", step=1,
        response={
            "status": 200,
            "generates_id": True,
            "id_body_field": "JobReferenceID",
            "body": {"extraField": "extraValue"},
        },
    )
    handler = make_async_handlers("partner", _make_datapoint([ep]), store)[1]
    response = await handler(_request())
    body = json.loads(response.body)
    assert body["extraField"] == "extraValue"
    assert len(body["JobReferenceID"]) == 36
