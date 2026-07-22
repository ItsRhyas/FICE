"""FICE application factory."""

import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db import create_db_and_tables
from app.templating import templates


def create_app() -> FastAPI:
    """Create and configure the FICE FastAPI application."""
    app = FastAPI(
        title="FICE",
        description="Personal Finance Tracker",
        version="0.1.0",
    )

    # Ensure static directory exists before mounting.
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    os.makedirs(static_dir, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    from app.routes import accounts, dashboard, transactions

    app.include_router(dashboard.router)
    app.include_router(accounts.router)
    app.include_router(transactions.router)

    @app.on_event("startup")
    def on_startup() -> None:
        create_db_and_tables()

    return app
