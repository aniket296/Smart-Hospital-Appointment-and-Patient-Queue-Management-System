"""JWT authentication and Role-Based Access Control (RBAC) decorators."""

from datetime import datetime, timedelta, timezone
from functools import wraps
import jwt
from flask import current_app, g, request
from backend.app.extensions import db
from backend.app.models import User
from backend.app.utils.errors import APIError


def create_access_token(user: User) -> str:
    """Issue a signed JWT bearer token with 8-hour expiry (configurable via JWT_EXPIRY_HOURS)."""
    expiry_hours = int(current_app.config.get("JWT_EXPIRY_HOURS", 8))
    now_utc = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "user_id": user.id,
        "role": user.role,
        "email": user.email,
        "iat": now_utc,
        "exp": now_utc + timedelta(hours=expiry_hours),
    }
    secret = current_app.config.get("JWT_SECRET_KEY", "dev-jwt-secret-key")
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT token, raising APIError(401) on invalid or expired tokens."""
    secret = current_app.config.get("JWT_SECRET_KEY", "dev-jwt-secret-key")
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise APIError("TOKEN_EXPIRED", "Authentication token has expired.", 401) from exc
    except jwt.InvalidTokenError as exc:
        raise APIError("INVALID_TOKEN", "Invalid authentication token.", 401) from exc


def get_current_user() -> User:
    """Extract Bearer token from Authorization header and load active User into g.current_user."""
    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header.startswith("Bearer "):
        raise APIError("UNAUTHORIZED", "Missing or malformed Authorization Bearer token.", 401)

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise APIError("UNAUTHORIZED", "Missing authentication token.", 401)

    payload = decode_access_token(token)
    user_id = payload.get("user_id") or payload.get("sub")
    try:
        user_id = int(user_id)
    except (TypeError, ValueError) as exc:
        raise APIError("INVALID_TOKEN", "Invalid token subject.", 401) from exc

    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        raise APIError("UNAUTHORIZED", "User account not found or inactive.", 401)

    g.current_user = user
    return user


def auth_required(fn):
    """Decorator requiring a valid JWT bearer token."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        get_current_user()
        return fn(*args, **kwargs)

    return wrapper


def roles_required(*allowed_roles: str):
    """Decorator requiring a valid JWT bearer token AND user.role in allowed_roles."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if user.role not in allowed_roles:
                raise APIError(
                    "FORBIDDEN",
                    f"Access denied. Required role(s): {', '.join(allowed_roles)}.",
                    403,
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator
