"""
Database configuration — SQLite via SQLAlchemy.

This module provides the engine, session factory, and declarative Base for the
entire app. The DB file lives at database/leads.db (relative to project root),
matching the path documented in ARCHITECTURE.md.

The get_db() generator is the FastAPI dependency that hands each request its
own session and ensures cleanup on completion.
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Resolve project root (3 levels up from this file: app/ -> backend/ -> project/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = _PROJECT_ROOT / "database" / "leads.db"

# Ensure the database directory exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed for SQLite + FastAPI
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


def get_db():
    """FastAPI dependency — yields a DB session, closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
