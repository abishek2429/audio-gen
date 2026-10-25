"""Database connection engine and session dependency."""
import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.config import settings, _is_serverless_or_readonly
from src.database.models import Base

# Safe database URL resolution: in serverless, avoid unreachable localhost URLs
db_url = settings.database_url
if _is_serverless_or_readonly() and ("localhost" in db_url or "127.0.0.1" in db_url):
    db_url = "sqlite:////tmp/incubrix.db"

# Determine connect args for SQLite vs PostgreSQL
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
elif "postgres" in db_url:
    connect_args["connect_timeout"] = 2

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_db_initialized = False


def get_engine():
    """Return the global SQLAlchemy engine."""
    return engine


def init_db():
    """Initialize database tables idempotently."""
    global _db_initialized
    if _db_initialized:
        return
    try:
        Base.metadata.create_all(bind=engine)
        _db_initialized = True
    except Exception as exc:
        if _is_serverless_or_readonly():
            pass
        else:
            raise exc


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
