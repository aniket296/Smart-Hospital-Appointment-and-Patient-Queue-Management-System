"""Appointments and Queue routes."""

from flask import Blueprint, g, jsonify, request
from backend.app.services.booking_service import (
    cancel_appointment,
    create_online_booking,
    create_walkin_booking,
    get_daily_queue,
    list_appointments,
    reschedule_appointment,
    transition_appointment_status,
)
from backend.app.utils.auth import auth_required, roles_required
from backend.app.utils.errors import APIError

appointments_bp = Blueprint("appointments", __name__)


@appointments_bp.route("/appointments", methods=["POST"])
@roles_required("PATIENT", "ADMIN")
def post_online_appointment():
    """Create an online appointment (status = BOOKED)."""
    data = request.get_json(silent=True) or {}
    appt = create_online_booking(g.current_user, data)
    return jsonify({"appointment": appt}), 201


@appointments_bp.route("/appointments/walk-in", methods=["POST"])
@roles_required("ADMIN")
def post_walkin_appointment():
    """Register a walk-in appointment (Admin only, status = CONFIRMED)."""
    data = request.get_json(silent=True) or {}
    appt = create_walkin_booking(g.current_user, data)
    return jsonify({"appointment": appt}), 201


@appointments_bp.route("/appointments", methods=["GET"])
@auth_required
def get_appointments():
    """List appointments scoped by user role."""
    date_str = request.args.get("date")
    status = request.args.get("status")
    include_history = request.args.get("include_history", "").lower() in ("true", "1", "yes")
    doctor_id_raw = request.args.get("doctor_id")
    doctor_id = None
    if doctor_id_raw:
        try:
            doctor_id = int(doctor_id_raw)
        except ValueError as exc:
            raise APIError("VALIDATION_ERROR", "doctor_id must be an integer.", 400) from exc

    appointments = list_appointments(
        current_user=g.current_user,
        date_str=date_str,
        doctor_id=doctor_id,
        status=status,
        include_history=include_history,
    )
    return jsonify({"appointments": appointments}), 200


@appointments_bp.route("/appointments/<int:appointment_id>/status", methods=["PATCH"])
@auth_required
def patch_appointment_status(appointment_id: int):
    """Transition appointment status according to state machine rules."""
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if not new_status:
        raise APIError("VALIDATION_ERROR", "status field is required.", 400)
    note = data.get("note")
    appt = transition_appointment_status(
        current_user=g.current_user,
        appointment_id=appointment_id,
        new_status=new_status,
        note=note,
    )
    return jsonify({"appointment": appt}), 200


@appointments_bp.route("/appointments/<int:appointment_id>/reschedule", methods=["PATCH"])
@auth_required
def patch_reschedule(appointment_id: int):
    """Reschedule a BOOKED or CONFIRMED appointment."""
    data = request.get_json(silent=True) or {}
    new_doctor_id = data.get("doctor_id")
    new_date = data.get("appointment_date")
    new_slot = data.get("slot_time")

    if not new_doctor_id or not new_date or not new_slot:
        raise APIError(
            "VALIDATION_ERROR",
            "doctor_id, appointment_date, and slot_time are required to reschedule.",
            400,
        )

    appt = reschedule_appointment(
        current_user=g.current_user,
        appointment_id=appointment_id,
        new_doctor_id=int(new_doctor_id),
        new_date_str=str(new_date),
        new_slot_str=str(new_slot),
    )
    return jsonify({"appointment": appt}), 200


@appointments_bp.route("/appointments/<int:appointment_id>/cancel", methods=["POST"])
@auth_required
def post_cancel(appointment_id: int):
    """Cancel a BOOKED or CONFIRMED appointment."""
    data = request.get_json(silent=True) or {}
    reason = data.get("reason")
    appt = cancel_appointment(
        current_user=g.current_user,
        appointment_id=appointment_id,
        reason=reason,
    )
    return jsonify({"appointment": appt}), 200


@appointments_bp.route("/queue", methods=["GET"])
def get_queue():
    """Return ordered daily queue (?date=&doctor_id=&department_id=)."""
    date_str = request.args.get("date")
    doctor_id_raw = request.args.get("doctor_id")
    department_id_raw = request.args.get("department_id")

    doctor_id = None
    if doctor_id_raw:
        try:
            doctor_id = int(doctor_id_raw)
        except ValueError as exc:
            raise APIError("VALIDATION_ERROR", "doctor_id must be an integer.", 400) from exc

    department_id = None
    if department_id_raw:
        try:
            department_id = int(department_id_raw)
        except ValueError as exc:
            raise APIError("VALIDATION_ERROR", "department_id must be an integer.", 400) from exc

    queue_data = get_daily_queue(
        date_str=date_str,
        doctor_id=doctor_id,
        department_id=department_id,
    )
    return jsonify(queue_data), 200
