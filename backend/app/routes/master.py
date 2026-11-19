"""Master data routes: departments, doctors, schedules, slots, and patient lookup."""

from flask import Blueprint, jsonify, request
from backend.app.services.master_service import (
    create_department,
    create_doctor,
    create_doctor_schedule,
    get_doctor_or_404,
    get_doctor_slots_for_date,
    list_departments,
    list_doctor_schedules,
    list_doctors,
    list_patients,
)
from backend.app.utils.auth import roles_required
from backend.app.utils.errors import APIError

master_bp = Blueprint("master", __name__)


@master_bp.route("/departments", methods=["GET"])
def get_departments():
    """List all hospital departments."""
    return jsonify({"departments": list_departments()}), 200


@master_bp.route("/departments", methods=["POST"])
@roles_required("ADMIN")
def post_department():
    """Create a new hospital department (Admin only)."""
    data = request.get_json(silent=True) or {}
    dept = create_department(data)
    return jsonify({"department": dept}), 201


@master_bp.route("/doctors", methods=["GET"])
def get_doctors():
    """List doctors with optional department_id, active_only, and include_schedules query params."""
    dept_id_raw = request.args.get("department_id")
    dept_id = None
    if dept_id_raw:
        try:
            dept_id = int(dept_id_raw)
        except ValueError as exc:
            raise APIError("VALIDATION_ERROR", "department_id must be an integer.", 400) from exc

    active_only = request.args.get("active_only", "").lower() in ("true", "1", "yes")
    include_schedules = request.args.get("include_schedules", "").lower() in ("true", "1", "yes")
    doctors = list_doctors(
        department_id=dept_id,
        active_only=active_only,
        include_schedules=include_schedules,
    )
    return jsonify({"doctors": doctors}), 200


@master_bp.route("/doctors/<int:doctor_id>", methods=["GET"])
def get_doctor_detail(doctor_id: int):
    """Get a single doctor profile including schedules."""
    doctor = get_doctor_or_404(doctor_id)
    return jsonify({"doctor": doctor.to_dict(include_schedules=True)}), 200


@master_bp.route("/doctors", methods=["POST"])
@roles_required("ADMIN")
def post_doctor():
    """Create a new DOCTOR user account and doctor profile (Admin only)."""
    data = request.get_json(silent=True) or {}
    doctor = create_doctor(data)
    return jsonify({"doctor": doctor}), 201


@master_bp.route("/doctors/<int:doctor_id>/schedules", methods=["GET"])
def get_schedules(doctor_id: int):
    """List schedules configured for a doctor."""
    schedules = list_doctor_schedules(doctor_id)
    return jsonify({"schedules": schedules}), 200


@master_bp.route("/doctors/<int:doctor_id>/schedules", methods=["POST"])
@roles_required("ADMIN")
def post_schedule(doctor_id: int):
    """Configure a weekday schedule for a doctor (Admin only)."""
    data = request.get_json(silent=True) or {}
    schedule = create_doctor_schedule(doctor_id, data)
    return jsonify({"schedule": schedule}), 201


@master_bp.route("/doctors/<int:doctor_id>/slots", methods=["GET"])
def get_slots(doctor_id: int):
    """Get generated slots and availability for a doctor on ?date=YYYY-MM-DD."""
    date_str = request.args.get("date", "")
    result = get_doctor_slots_for_date(doctor_id, date_str)
    return jsonify(result), 200


@master_bp.route("/patients", methods=["GET"])
@roles_required("ADMIN")
def get_patients():
    """List or search patients (Admin only)."""
    search = request.args.get("search")
    patients = list_patients(search=search)
    return jsonify({"patients": patients}), 200
