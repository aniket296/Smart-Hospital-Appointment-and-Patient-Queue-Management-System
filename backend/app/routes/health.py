"""Health check blueprint."""

from flask import Blueprint, current_app, jsonify
from sqlalchemy import text
from backend.app.extensions import db
from backend.app.utils.timezone import now_hospital

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    """Return service health status, timezone, and optional database check."""
    db_status = "unknown"
    try:
        db.session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return jsonify(
        {
            "status": "ok",
            "service": "Smart Hospital Appointment and Patient Queue Management System",
            "timezone": current_app.config.get("HOSPITAL_TIMEZONE", "Asia/Kolkata"),
            "timestamp": now_hospital().isoformat(),
            "database": db_status,
        }
    ), 200
