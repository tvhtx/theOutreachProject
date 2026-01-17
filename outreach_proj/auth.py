"""
Authentication utilities for the Outreach application.

Provides JWT-based authentication with password hashing.
"""

from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Optional, Callable, Any

import bcrypt
import jwt
from flask import request, jsonify, g

from .config import config
from .database import get_db_session
from .models import User


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def create_access_token(user_id: int, email: str) -> str:
    """
    Create a JWT access token for a user.
    
    Args:
        user_id: The user's database ID
        email: The user's email address
        
    Returns:
        JWT token string
    """
    expiration = datetime.now(timezone.utc) + timedelta(hours=config.JWT_EXPIRATION_HOURS)
    
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expiration,
        "iat": datetime.now(timezone.utc),
    }
    
    return jwt.encode(payload, config.SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT access token.
    
    Args:
        token: The JWT token string
        
    Returns:
        Token payload dict if valid, None if invalid/expired
    """
    try:
        payload = jwt.decode(
            token, 
            config.SECRET_KEY, 
            algorithms=[config.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_user_from_token(token: str) -> Optional[User]:
    """
    Get the current user from a JWT token.
    
    Args:
        token: The JWT token string
        
    Returns:
        User object if found and token valid, None otherwise
    """
    payload = decode_access_token(token)
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        return user
    finally:
        db.close()


def require_auth(f: Callable) -> Callable:
    """
    Decorator that requires JWT authentication.
    
    Sets g.current_user to the authenticated user.
    
    Usage:
        @app.route('/api/protected')
        @require_auth
        def protected_route():
            user = g.current_user
            ...
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        # Check for Authorization header
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({"error": "Missing Authorization header"}), 401
        
        # Extract token from "Bearer <token>" format
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({"error": "Invalid Authorization header format"}), 401
        
        token = parts[1]
        
        # Validate token and get user
        user = get_current_user_from_token(token)
        if not user:
            return jsonify({"error": "Invalid or expired token"}), 401
        
        # Store user in Flask's g object for the request
        g.current_user = user
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_auth_optional(f: Callable) -> Callable:
    """
    Decorator that optionally extracts user from JWT if present.
    
    Does not fail if no token is provided.
    Sets g.current_user to the user or None.
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        g.current_user = None
        
        auth_header = request.headers.get('Authorization')
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
                user = get_current_user_from_token(token)
                g.current_user = user
        
        return f(*args, **kwargs)
    
    return decorated_function


# ========================================
# User Service Functions
# ========================================

def create_user(email: str, password: str, full_name: str) -> tuple[Optional[User], Optional[str]]:
    """
    Create a new user account.
    
    Args:
        email: User's email address
        password: Plain text password (will be hashed)
        full_name: User's full name
        
    Returns:
        Tuple of (User, None) on success, or (None, error_message) on failure
    """
    from .models import UserProfile
    
    db = get_db_session()
    try:
        # Check if email already exists
        existing = db.query(User).filter(User.email == email.lower()).first()
        if existing:
            return None, "Email already registered"
        
        # Create user
        user = User(
            email=email.lower(),
            password_hash=hash_password(password),
        )
        db.add(user)
        db.flush()  # Get user ID
        
        # Create profile
        profile = UserProfile(
            user_id=user.id,
            full_name=full_name,
            sender_email=email.lower(),
        )
        db.add(profile)
        db.commit()
        
        # Refresh to get relationships
        db.refresh(user)
        
        return user, None
        
    except Exception as e:
        db.rollback()
        return None, str(e)
    finally:
        db.close()


def authenticate_user(email: str, password: str) -> tuple[Optional[dict], Optional[str]]:
    """
    Authenticate a user with email and password.
    
    Args:
        email: User's email address
        password: Plain text password
        
    Returns:
        Tuple of (user_dict, None) on success, or (None, error_message) on failure
        user_dict contains: id, email, name
    """
    db = get_db_session()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        
        if not user:
            return None, "Invalid email or password"
        
        if not user.is_active:
            return None, "Account is disabled"
        
        if not verify_password(password, user.password_hash):
            return None, "Invalid email or password"
        
        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
        
        # Extract values while session is open
        user_data = {
            "id": user.id,
            "email": user.email,
            "name": user.profile.full_name if user.profile else "",
        }
        
        return user_data, None
        
    except Exception as e:
        db.rollback()
        return None, str(e)
    finally:
        db.close()

