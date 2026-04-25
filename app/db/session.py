"""
session.py — Database connection and session management.

Creates a SQLite engine and provides sessions for services.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.models import Base


engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,
    connect_args={"check_same_thread": False},  # Required for SQLite + FastAPI
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    """Create all database tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    Provide a database session per request.

    Usage in FastAPI routes:
        @app.get("/something")
        async def something(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
