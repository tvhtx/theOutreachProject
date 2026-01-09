"""
API helpers for creating service instances with proper database sessions.
"""

from contextlib import contextmanager
from functools import wraps
from flask import g, jsonify

from .database import get_db_session
from .models import User
from .services.contact_service import ContactService
from .services.template_service import TemplateService
from .services.email_service import EmailService


@contextmanager
def get_contact_service():
    """Get a ContactService with the current user's context."""
    db = get_db_session()
    try:
        user = db.query(User).filter(User.id == g.current_user.id).first()
        if not user:
            raise ValueError("User not found")
        yield ContactService(db, user)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_template_service():
    """Get a TemplateService with the current user's context."""
    db = get_db_session()
    try:
        user = db.query(User).filter(User.id == g.current_user.id).first()
        if not user:
            raise ValueError("User not found")
        yield TemplateService(db, user)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_email_service():
    """Get an EmailService with the current user's context."""
    db = get_db_session()
    try:
        user = db.query(User).filter(User.id == g.current_user.id).first()
        if not user:
            raise ValueError("User not found")
        yield EmailService(db, user)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
