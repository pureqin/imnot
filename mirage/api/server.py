"""
FastAPI application factory.

Responsibilities:
- Create and configure the FastAPI app instance.
- Initialise the SessionStore and load partner definitions.
- Delegate route registration to the dynamic router.
- Tear down the store cleanly on shutdown via the FastAPI lifespan hook.
- Expose `create_app()` as the single entry point used by both the CLI and tests.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI

from mirage.engine.router import register_routes
from mirage.engine.session_store import SessionStore
from mirage.loader.yaml_loader import load_partners

logger = logging.getLogger(__name__)

DEFAULT_PARTNERS_DIR = Path("partners")
DEFAULT_DB_PATH = Path("mirage.db")


def create_app(
    partners_dir: Path = DEFAULT_PARTNERS_DIR,
    db_path: Path = DEFAULT_DB_PATH,
) -> FastAPI:
    """Build and return a fully configured FastAPI application.

    A fresh SessionStore and partner list are created on every call, so tests
    can call this multiple times without shared state.
    """
    store = SessionStore(db_path=db_path)
    partners = load_partners(partners_dir)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        store.init()
        logger.info("Mirage starting — %d partner(s) loaded", len(partners))
        yield
        store.close()
        logger.info("Mirage shut down")

    app = FastAPI(
        title="Mirage",
        description="Stateful API mock server for integration testing",
        version="0.1.0",
        lifespan=lifespan,
    )

    register_routes(app, partners, store)
    return app
