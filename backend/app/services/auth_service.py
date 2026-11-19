"""Authentication service for registration, login, and profile retrieval."""

import re
from datetime import date
from werkzeug.security import check_password_hash, generate_password_hash
from backend.app.extensions import db
from backend.app.models import Patient, User
from backend.app.utils.auth import create_access_token
from backend.app.utils.errors import APIError

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email(email: str) -> str:
    """Validate and normalize email string."""
    if not email or not isinstance(email, str):
        raise APIError("VALIDATION_ERROR", "Email is required.", 400)
    normalized = email.strip().lower()
    if not EMAIL_REGEX.match(normalized):
        raise APIError("VALIDATION_ERROR", "Invalid email format.", 400)
    return normalized


def validate_password(password: str) -> str:
    """Validate minimum password length of 8 characters."""
    if not password or not isinstance(password, str) or len(password) < 8:
        raise APIError("VALIDATION_ERROR", "Password must be at least 8 characters long.", 400)
    return password


def register_patient(data: dict) -> dict:
    """Self-register a new PATIENT user and linked Patient profile (ignoring any client role)."""
    if not isinstance(data, dict):
        raise APIError("VALIDATION_ERROR", "Invalid JSON payload.", 400)

    name = (data.get("name") or data.get("full_name") or "").strip()
    if not name:
        raise APIError("VALIDATION_ERROR", "Name is required.", 400)

    email = validate_email(data.get("email", ""))
    password = validate_password(data.get("password", ""))
    phone = (data.get("phone") or "").strip()
    if not phone:
        raise APIError("VALIDATION_ERROR", "Phone number is required for patient registration.", 400)

    existing = User.query.filter_by(email=email).first()
    if existing:
        raise APIError("EMAIL_ALREADY_EXISTS", "An account with this email already exists.", 409)

    dob_raw = data.get("date_of_birth")
    dob_val = None
    if dob_raw:
        try:
            dob_val = date.fromisoformat(str(dob_raw).strip())
        except ValueError as exc:
            raise APIError("VALIDATION_ERROR", "date_of_birth must be YYYY-MM-DD.", 400) from exc

    gender = (data.get("gender") or "").strip() or None

    # Ignore any role supplied by the client; self-registration ALWAYS creates a PATIENT
    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password, method="scrypt"),
        role="PATIENT",
        is_active=True,
    )
    db.session.add(user)
    db.session.flush()

    patient = Patient(
        user_id=user.id,
        full_name=name,
        phone=phone,
        email=email,
        date_of_birth=dob_val,
        gender=gender,
    )
    db.session.add(patient)
    db.session.commit()

    token = create_access_token(user)
    return {
        "token": token,
        "user": user.to_dict(),
        "patient": patient.to_dict(),
    }


def login_user(data: dict) -> dict:
    """Authenticate user by email and password and return JWT token + user details."""
    if not isinstance(data, dict):
        raise APIError("VALIDATION_ERROR", "Invalid JSON payload.", 400)

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        raise APIError("VALIDATION_ERROR", "Email and password are required.", 400)

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        raise APIError("INVALID_CREDENTIALS", "Invalid email or password.", 401)

    if not user.is_active:
        raise APIError("ACCOUNT_INACTIVE", "User account is inactive.", 403)

    token = create_access_token(user)
    return {
        "token": token,
        "user": user.to_dict(),
    }
