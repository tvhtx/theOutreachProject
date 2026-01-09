"""
Database initialization and session management.
"""

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .config import config
from .models import Base

# Create engine
engine = create_engine(
    config.DATABASE_URL,
    echo=config.FLASK_DEBUG,  # Log SQL in debug mode
    pool_pre_ping=True,  # Verify connections before using
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all database tables if they don't exist."""
    try:
        # checkfirst=True ensures we don't error on existing tables
        Base.metadata.create_all(bind=engine, checkfirst=True)
    except Exception as e:
        # Log but don't fail if tables exist - this handles edge cases
        import logging
        logging.warning(f"Database init warning (may be ignorable): {e}")



def drop_db() -> None:
    """Drop all database tables. Use with caution!"""
    Base.metadata.drop_all(bind=engine)


@contextmanager
def get_db() -> Session:
    """
    Get a database session with automatic cleanup.
    
    Usage:
        with get_db() as db:
            user = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """
    Get a database session (for Flask request context).
    
    The caller is responsible for closing the session.
    """
    return SessionLocal()
