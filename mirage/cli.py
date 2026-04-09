"""
CLI entry point for Mirage.

Responsibilities:
- Provide the `mirage` command group via Click.
- `mirage start`: load partner YAMLs, build the FastAPI app, launch Uvicorn.
- `mirage status`: open the store directly and print active sessions.
"""

from __future__ import annotations

from pathlib import Path

import click
import uvicorn

from mirage.api.server import create_app
from mirage.engine.session_store import SessionStore

DEFAULT_PARTNERS_DIR = Path("partners")
DEFAULT_DB = Path("mirage.db")


@click.group()
def cli() -> None:
    """Mirage — stateful API mock server for integration testing."""


@cli.command()
@click.option(
    "--partners-dir",
    default=str(DEFAULT_PARTNERS_DIR),
    show_default=True,
    help="Directory containing partner YAML definitions.",
)
@click.option(
    "--db",
    default=str(DEFAULT_DB),
    show_default=True,
    help="Path to the SQLite database file.",
)
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind host.")
@click.option("--port", default=8000, show_default=True, help="Bind port.")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload (development only).")
def start(partners_dir: str, db: str, host: str, port: int, reload: bool) -> None:
    """Load partner definitions and start the mock server."""
    app = create_app(
        partners_dir=Path(partners_dir),
        db_path=Path(db),
    )
    click.echo(f"Starting Mirage on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, reload=reload)


@cli.command()
@click.option(
    "--db",
    default=str(DEFAULT_DB),
    show_default=True,
    help="Path to the SQLite database file.",
)
def status(db: str) -> None:
    """Show active sessions in the store."""
    db_path = Path(db)
    if not db_path.exists():
        click.echo(f"No database found at {db_path}. Has the server been started yet?")
        raise SystemExit(1)

    store = SessionStore(db_path=db_path)
    store.init()
    sessions = store.list_sessions()
    store.close()

    if not sessions:
        click.echo("No active sessions.")
        return

    click.echo(f"{'SESSION ID':<38} {'PARTNER':<12} {'DATAPOINT':<16} {'CREATED AT'}")
    click.echo("-" * 90)
    for s in sessions:
        click.echo(
            f"{s['session_id']:<38} {s['partner']:<12} {s['datapoint']:<16} {s['created_at']}"
        )
