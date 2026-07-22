"""Database layer for FICE.

Provides a single SQLite engine with WAL mode enabled, SQLModel metadata,
and a FastAPI dependency that yields a database session per request.
"""

import os
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

# Ensure the data directory exists at import time so the SQLite file can be created.
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.environ.get("FICE_DATABASE_URL", f"sqlite:///{DATA_DIR / 'fice.db'}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


@event.listens_for(Engine, "connect")
def _enable_wal_mode(dbapi_connection, connection_record):
    """Enable SQLite WAL mode on every new connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def create_db_and_tables() -> None:
    """Create all SQLModel tables if they do not exist."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Yield a SQLModel session bound to the shared engine.

    Intended for use as a FastAPI dependency:
        `SessionDep = Annotated[Session, Depends(get_session)]`
    """
    with Session(engine) as session:
        yield session


@contextmanager
def session_scope():
    """Synchronous context manager for a standalone DB session.

    Useful for tests, scripts, or the pywebview startup path.
    """
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
