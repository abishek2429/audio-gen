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
    connect_args["connect_timeout"] = 5

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_engine():
    """Return the global SQLAlchemy engine."""
    return engine


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
