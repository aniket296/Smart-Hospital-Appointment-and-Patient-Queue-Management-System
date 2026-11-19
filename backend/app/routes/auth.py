"""Authentication routes: POST /api/auth/register, POST /api/auth/login, GET /api/auth/me."""

from flask import Blueprint, g, jsonify, request
from backend.app.services.auth_service import login_user, register_patient
from backend.app.utils.auth import auth_required

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/auth/register", methods=["POST"])
def register():
    """Register a new PATIENT user and linked patient record."""
    data = request.get_json(silent=True) or {}
    result = register_patient(data)
    return jsonify(result), 201


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    """Authenticate an existing user and return a JWT bearer token."""
    data = request.get_json(silent=True) or {}
    result = login_user(data)
    return jsonify(result), 200


@auth_bp.route("/auth/me", methods=["GET"])
@auth_required
def me():
    """Return currently authenticated user profile."""
    user = g.current_user
    payload = {"user": user.to_dict()}
    if user.patient_profile:
        payload["patient"] = user.patient_profile.to_dict()
    if user.doctor_profile:
        payload["doctor"] = user.doctor_profile.to_dict()
    return jsonify(payload), 200
