"""
TICKR — Database Setup
SQLAlchemy engine + session factory.
Supports SQLite (dev) and PostgreSQL (prod) via DATABASE_URL in .env
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# SQLite needs check_same_thread=False for FastAPI async usage
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables on startup."""
    # Import models so SQLAlchemy registers them before create_all
    from app.models import candle, user, watchlist  # noqa: F401
    Base.metadata.create_all(bind=engine)
