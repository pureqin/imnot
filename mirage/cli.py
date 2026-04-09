"""
CLI entry point for Mirage.

Responsibilities:
- Provide the `mirage` command group via Click.
- `mirage start`: load partner YAMLs, build the FastAPI app, launch Uvicorn.
- `mirage status`: query the session store and print active sessions.
"""
