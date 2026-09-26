"""Database Engine and Session Factory
"""

from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from core.config.settings import get_settings

settings = get_settings()

connect_args = {"connect_timeout": 3} if "postgresql" in settings.database_url else {}

engine = create_engine(
    settings.database_url,
    echo=(settings.LKIO_ENV == "development"),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for yielding database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
