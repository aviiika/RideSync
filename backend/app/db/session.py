"""Database session management.

SQLite, deliberately. History is append-only, single-writer and local to a demo
machine; Postgres would add a container to every run for no benefit at this
size. It sits behind a session factory, so moving to another engine is a URL
change plus a driver.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base


def build_engine(database_url: str) -> Engine:
    """Create the engine, making sure a SQLite file has somewhere to live."""
    if database_url.startswith("sqlite") and ":memory:" not in database_url:
        path = Path(database_url.split("///", 1)[-1])
        path.parent.mkdir(parents=True, exist_ok=True)

    return create_engine(
        database_url,
        # The simulation loop and request handlers share one connection pool
        # across threads; SQLite needs to be told that is intended.
        connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
        future=True,
    )


class Database:
    """Owns the engine and hands out sessions."""

    def __init__(self, database_url: str) -> None:
        self._engine = build_engine(database_url)
        self._sessions = sessionmaker(bind=self._engine, expire_on_commit=False, future=True)

    @property
    def engine(self) -> Engine:
        return self._engine

    def create_all(self) -> None:
        """Create tables if they are missing.

        No migration tool: the schema is two append-only tables owned entirely
        by this application, and a demo that needs `alembic upgrade` before it
        runs is a worse demo.
        """
        Base.metadata.create_all(self._engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        """A transactional scope. Rolls back and re-raises on failure."""
        session = self._sessions()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
