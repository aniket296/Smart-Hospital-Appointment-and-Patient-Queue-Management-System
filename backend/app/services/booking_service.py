"""Booking, token generation, status lifecycle, and queue service."""

from datetime import date, time, timedelta
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from backend.app.extensions import db
from backend.app.models import (
    Appointment,
    AppointmentStatusHistory,
    Doctor,
    DoctorSchedule,
    DoctorTokenCounter,
    Patient,
    User,
)
from backend.app.services.master_service import (
    generate_slots_for_schedule,
    get_doctor_or_404,
    parse_date_str,
    parse_time_str,
)
from backend.app.utils.errors import APIError
from backend.app.services.notification_service import NotificationService
from backend.app.utils.timezone import current_time_hospital, now_hospital_naive, today_hospital

TERMINAL_STATUSES = {"COMPLETED", "CANCELLED", "NO_SHOW"}
ALL_STATUSES = {"BOOKED", "CONFIRMED", "IN_CONSULTATION", "COMPLETED", "CANCELLED", "NO_SHOW"}


def _next_token_number(doctor: Doctor, target_date: date) -> str:
    """Generate sequential daily token <DOC_CODE>-<3-digit-seq> safely inside the transaction."""
    dialect = db.engine.dialect.name
    date_param = target_date.isoformat()
    if dialect == "mysql":
        db.session.execute(
            text(
                """
                INSERT INTO doctor_token_counters (doctor_id, token_date, last_seq)
                VALUES (:doc_id, :t_date, 1)
                ON DUPLICATE KEY UPDATE last_seq = last_seq + 1
                """
            ),
            {"doc_id": doctor.id, "t_date": date_param},
        )
        row = db.session.execute(
            text(
                """
                SELECT last_seq FROM doctor_token_counters
                WHERE doctor_id = :doc_id AND token_date = :t_date
                """
            ),
            {"doc_id": doctor.id, "t_date": date_param},
        ).fetchone()
        seq = int(row[0])
    else:
        # SQLite / generic fallback using atomic upsert and read
        db.session.execute(
            text(
                """
                INSERT INTO doctor_token_counters (doctor_id, token_date, last_seq)
                VALUES (:doc_id, :t_date, 1)
                ON CONFLICT(doctor_id, token_date)
                DO UPDATE SET last_seq = doctor_token_counters.last_seq + 1
                """
            ),
            {"doc_id": doctor.id, "t_date": date_param},
        )
        row = db.session.execute(
            text(
                """
                SELECT last_seq FROM doctor_token_counters
                WHERE doctor_id = :doc_id AND token_date = :t_date
                """
            ),
            {"doc_id": doctor.id, "t_date": date_param},
        ).fetchone()
        seq = int(row[0])

    return f"{doctor.doc_code}-{seq:03d}"


def validate_booking_date(target_date: date) -> None:
    """Ensure date is not in the past and at most 30 days ahead in HOSPITAL_TIMEZONE."""
    today = today_hospital()
    if target_date < today:
        raise APIError("PAST_DATE", "Appointment date cannot be in the past.", 400)
    max_date = today + timedelta(days=30)
    if target_date > max_date:
        raise APIError(
            "DATE_TOO_FAR",
            "Appointment date cannot be more than 30 days in the future.",
            400,
        )


def _get_doctor_day_schedule_info(doctor: Doctor, target_date: date):
    """Return (all_valid_slots: list[time], effective_capacity: int) for doctor on target_date."""
    if not doctor.is_active:
        raise APIError("DOCTOR_INACTIVE", "Selected doctor is currently inactive.", 400)

    weekday = target_date.weekday()
    active_schedules = (
        DoctorSchedule.query.filter_by(
            doctor_id=doctor.id,
            day_of_week=weekday,
            is_active=True,
        )
        .order_by(DoctorSchedule.start_time.asc())
        .all()
    )
    if not active_schedules:
        raise APIError(
            "NO_SCHEDULE",
            f"Doctor {doctor.doc_code} has no active schedule on this weekday.",
            400,
        )

    all_slots: list[time] = []
    total_max_patients = 0
    for sched in active_schedules:
        all_slots.extend(generate_slots_for_schedule(sched))
        total_max_patients += sched.max_patients

    effective_capacity = min(len(all_slots), total_max_patients)
    return all_slots, effective_capacity


def validate_slot_and_capacity(
    doctor: Doctor,
    target_date: date,
    slot_time: time,
    exclude_appointment_id: int | None = None,
) -> None:
    """Validate date, past-time check for today, schedule membership, daily cap, and slot conflict."""
    validate_booking_date(target_date)

    today = today_hospital()
    now_t = current_time_hospital()
    if target_date == today and slot_time < now_t:
        raise APIError(
            "PAST_SLOT",
            f"Slot {slot_time.strftime('%H:%M')} has already passed for today.",
            400,
        )

    valid_slots, effective_capacity = _get_doctor_day_schedule_info(doctor, target_date)
    valid_slot_labels = {s.strftime("%H:%M") for s in valid_slots}
    slot_label = slot_time.strftime("%H:%M")

    if slot_label not in valid_slot_labels:
        raise APIError(
            "INVALID_SLOT",
            f"Slot {slot_label} does not exist in active schedule for doctor {doctor.doc_code}.",
            400,
        )

    # Check active appointments on this date
    query = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_date == target_date,
        Appointment.status != "CANCELLED",
    )
    if exclude_appointment_id is not None:
        query = query.filter(Appointment.id != exclude_appointment_id)

    active_appointments = query.all()
    if len(active_appointments) >= effective_capacity:
        raise APIError(
            "DAILY_CAPACITY_REACHED",
            f"Daily patient capacity ({effective_capacity}) reached for doctor {doctor.doc_code} on {target_date.isoformat()}.",
            409,
        )

    for appt in active_appointments:
        if appt.slot_time and appt.slot_time.strftime("%H:%M") == slot_label:
            raise APIError(
                "SLOT_ALREADY_BOOKED",
                f"Slot {slot_label} on {target_date.isoformat()} is already booked.",
                409,
            )


def create_online_booking(current_user: User, data: dict) -> dict:
    """Create an online appointment with status BOOKED."""
    if not isinstance(data, dict):
        raise APIError("VALIDATION_ERROR", "Invalid JSON payload.", 400)

    try:
        doctor_id = int(data.get("doctor_id"))
    except (TypeError, ValueError) as exc:
        raise APIError("VALIDATION_ERROR", "Valid doctor_id is required.", 400) from exc

    doctor = get_doctor_or_404(doctor_id)
    target_date = parse_date_str(data.get("appointment_date"), "appointment_date")
    slot_time = parse_time_str(data.get("slot_time"), "slot_time")
    reason = (data.get("reason") or "").strip() or None

    # Resolve patient_id based on role
    if current_user.role == "PATIENT":
        if not current_user.patient_profile:
            raise APIError("PATIENT_PROFILE_MISSING", "Patient profile not found for current user.", 400)
        patient = current_user.patient_profile
    elif current_user.role == "ADMIN":
        try:
            patient_id = int(data.get("patient_id"))
        except (TypeError, ValueError) as exc:
            raise APIError("VALIDATION_ERROR", "patient_id is required when Admin creates online booking.", 400) from exc
        patient = db.session.get(Patient, patient_id)
        if not patient:
            raise APIError("NOT_FOUND", f"Patient with id {patient_id} not found.", 404)
    else:
        raise APIError("FORBIDDEN", "Only Patients or Admins can book appointments.", 403)

    validate_slot_and_capacity(doctor, target_date, slot_time)

    try:
        token_number = _next_token_number(doctor, target_date)
        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_date=target_date,
            slot_time=slot_time,
            booking_type="ONLINE",
            status="BOOKED",
            token_number=token_number,
            reason=reason,
            created_by_user_id=current_user.id,
        )
        db.session.add(appointment)
        db.session.flush()

        history = AppointmentStatusHistory(
            appointment_id=appointment.id,
            old_status=None,
            new_status="BOOKED",
            changed_by_user_id=current_user.id,
            changed_at=now_hospital_naive(),
            note="Online appointment booked",
        )
        db.session.add(history)
        db.session.commit()

        # Trigger notification
        NotificationService.send_notification(
            event_type="BOOKING_CREATED",
            subject=f"Appointment Booked: Token {appointment.token_number}",
            message=f"Your appointment with Dr. {doctor.doc_code} on {target_date.isoformat()} at {slot_time.strftime('%H:%M')} is booked. Token: {appointment.token_number}.",
            appointment=appointment,
        )
    except IntegrityError as exc:
        db.session.rollback()
        raise APIError(
            "SLOT_ALREADY_BOOKED",
            f"Slot {slot_time.strftime('%H:%M')} on {target_date.isoformat()} was just booked by another request.",
            409,
        ) from exc

    return appointment.to_dict(include_history=True)


def create_walkin_booking(current_user: User, data: dict) -> dict:
    """Register walk-in appointment (Admin only) with status CONFIRMED and auto-slot if slot_time omitted."""
    if not isinstance(data, dict):
        raise APIError("VALIDATION_ERROR", "Invalid JSON payload.", 400)

    try:
        doctor_id = int(data.get("doctor_id"))
    except (TypeError, ValueError) as exc:
        raise APIError("VALIDATION_ERROR", "Valid doctor_id is required.", 400) from exc

    doctor = get_doctor_or_404(doctor_id)

    # Walk-in date defaults to today in hospital timezone if not provided
    raw_date = data.get("appointment_date")
    target_date = parse_date_str(raw_date, "appointment_date") if raw_date else today_hospital()
    validate_booking_date(target_date)

    # Resolve existing patient or quickly create walk-in patient
    patient_id_raw = data.get("patient_id")
    if patient_id_raw:
        try:
            patient_id = int(patient_id_raw)
        except (TypeError, ValueError) as exc:
            raise APIError("VALIDATION_ERROR", "patient_id must be an integer.", 400) from exc
        patient = db.session.get(Patient, patient_id)
        if not patient:
            raise APIError("NOT_FOUND", f"Patient with id {patient_id} not found.", 404)
    else:
        full_name = (data.get("patient_name") or data.get("full_name") or "").strip()
        phone = (data.get("patient_phone") or data.get("phone") or "").strip()
        email = (data.get("patient_email") or data.get("email") or "").strip() or None
        if not full_name or not phone:
            raise APIError(
                "VALIDATION_ERROR",
                "Walk-in booking requires either patient_id or patient_name and patient_phone.",
                400,
            )
        patient = Patient(
            user_id=None,
            full_name=full_name,
            phone=phone,
            email=email,
        )
        db.session.add(patient)
        db.session.flush()

    valid_slots, effective_capacity = _get_doctor_day_schedule_info(doctor, target_date)

    active_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_date == target_date,
        Appointment.status != "CANCELLED",
    ).all()

    if len(active_appointments) >= effective_capacity:
        db.session.rollback()
        raise APIError(
            "DAILY_CAPACITY_REACHED",
            f"Daily patient capacity ({effective_capacity}) reached for doctor {doctor.doc_code} on {target_date.isoformat()}.",
            409,
        )

    booked_labels = {a.slot_time.strftime("%H:%M") for a in active_appointments if a.slot_time}
    today = today_hospital()
    now_t = current_time_hospital()

    raw_slot = data.get("slot_time")
    if raw_slot and str(raw_slot).strip():
        slot_time = parse_time_str(str(raw_slot), "slot_time")
        validate_slot_and_capacity(doctor, target_date, slot_time)
    else:
        # Auto-assign the next free slot at or after current time today (or earliest free slot on future date)
        chosen_slot: time | None = None
        for candidate in valid_slots:
            label = candidate.strftime("%H:%M")
            if label in booked_labels:
                continue
            if target_date == today and candidate < now_t:
                continue
            chosen_slot = candidate
            break

        if chosen_slot is None:
            db.session.rollback()
            raise APIError(
                "NO_FREE_SLOTS",
                f"No free slots available at or after current time for doctor {doctor.doc_code} on {target_date.isoformat()}.",
                409,
            )
        slot_time = chosen_slot

    reason = (data.get("reason") or "Walk-in consultation").strip()

    try:
        token_number = _next_token_number(doctor, target_date)
        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_date=target_date,
            slot_time=slot_time,
            booking_type="WALK_IN",
            status="CONFIRMED",
            token_number=token_number,
            reason=reason,
            created_by_user_id=current_user.id,
        )
        db.session.add(appointment)
        db.session.flush()

        history = AppointmentStatusHistory(
            appointment_id=appointment.id,
            old_status=None,
            new_status="CONFIRMED",
            changed_by_user_id=current_user.id,
            changed_at=now_hospital_naive(),
            note="Walk-in appointment registered and confirmed",
        )
        db.session.add(history)
        db.session.commit()

        # Trigger notification
        NotificationService.send_notification(
            event_type="BOOKING_CREATED",
            subject=f"Appointment Booked: Token {appointment.token_number}",
            message=f"Your appointment with Dr. {doctor.doc_code} on {target_date.isoformat()} at {slot_time.strftime('%H:%M')} is booked. Token: {appointment.token_number}.",
            appointment=appointment,
        )
    except IntegrityError as exc:
        db.session.rollback()
        raise APIError(
            "SLOT_ALREADY_BOOKED",
            f"Slot {slot_time.strftime('%H:%M')} on {target_date.isoformat()} is already booked.",
            409,
        ) from exc

    return appointment.to_dict(include_history=True)


def list_appointments(
    current_user: User,
    date_str: str | None = None,
    doctor_id: int | None = None,
    status: str | None = None,
    include_history: bool = False,
) -> list[dict]:
    """List appointments scoped by the caller's role."""
    query = Appointment.query

    if current_user.role == "PATIENT":
        if not current_user.patient_profile:
            return []
        query = query.filter(Appointment.patient_id == current_user.patient_profile.id)
    elif current_user.role == "DOCTOR":
        if not current_user.doctor_profile:
            return []
        query = query.filter(Appointment.doctor_id == current_user.doctor_profile.id)
    elif current_user.role == "ADMIN":
        if doctor_id is not None:
            query = query.filter(Appointment.doctor_id == doctor_id)

    if date_str:
        target_date = parse_date_str(date_str, "date")
        query = query.filter(Appointment.appointment_date == target_date)

    if status:
        status_upper = status.strip().upper()
        if status_upper not in ALL_STATUSES:
            raise APIError("VALIDATION_ERROR", f"Invalid status filter '{status}'.", 400)
        query = query.filter(Appointment.status == status_upper)

    appointments = query.order_by(
        Appointment.appointment_date.desc(),
        Appointment.slot_time.asc(),
        Appointment.token_number.asc(),
    ).all()
    return [a.to_dict(include_history=include_history) for a in appointments]


def transition_appointment_status(
    current_user: User,
    appointment_id: int,
    new_status: str,
    note: str | None = None,
) -> dict:
    """Enforce Section 5.7 state machine, single IN_CONSULTATION guard, and write status history."""
    appointment = db.session.get(Appointment, appointment_id)
    if not appointment:
        raise APIError("NOT_FOUND", f"Appointment with id {appointment_id} not found.", 404)

    target_status = (new_status or "").strip().upper()
    if target_status not in ALL_STATUSES:
        raise APIError("INVALID_STATUS", f"Unknown status '{new_status}'.", 400)

    old_status = appointment.status
    if old_status in TERMINAL_STATUSES:
        raise APIError(
            "INVALID_TRANSITION",
            f"Appointment is already in terminal state '{old_status}' and cannot transition to '{target_status}'.",
            400,
        )

    if old_status == target_status:
        raise APIError(
            "INVALID_TRANSITION",
            f"Appointment is already in status '{old_status}'.",
            400,
        )

    # Role & Ownership verification
    role = current_user.role
    is_admin = role == "ADMIN"
    is_own_doctor = (
        role == "DOCTOR"
        and current_user.doctor_profile is not None
        and current_user.doctor_profile.id == appointment.doctor_id
    )
    is_own_patient = (
        role == "PATIENT"
        and current_user.patient_profile is not None
        and current_user.patient_profile.id == appointment.patient_id
    )

    if role == "DOCTOR" and not is_own_doctor:
        raise APIError("FORBIDDEN", "Doctors can only update appointments in their own queue.", 403)
    if role == "PATIENT" and not is_own_patient:
        raise APIError("FORBIDDEN", "Patients can only manage their own appointments.", 403)

    # Transition table rules (Section 5.7):
    # BOOKED -> CONFIRMED: Admin
    # CONFIRMED -> IN_CONSULTATION: Doctor (own), Admin
    # IN_CONSULTATION -> COMPLETED: Doctor (own), Admin
    # BOOKED or CONFIRMED -> CANCELLED: Patient (own), Admin
    # BOOKED or CONFIRMED -> NO_SHOW: Doctor (own), Admin, only on or after appointment_date
    if old_status == "BOOKED" and target_status == "CONFIRMED":
        if not is_admin:
            raise APIError("FORBIDDEN", "Only Admin can confirm a BOOKED appointment.", 403)

    elif old_status == "CONFIRMED" and target_status == "IN_CONSULTATION":
        if not (is_admin or is_own_doctor):
            raise APIError("FORBIDDEN", "Only the assigned Doctor or Admin can start consultation.", 403)
        # Ensure only one appointment per doctor is IN_CONSULTATION at a time
        existing_in_consult = Appointment.query.filter(
            Appointment.doctor_id == appointment.doctor_id,
            Appointment.status == "IN_CONSULTATION",
            Appointment.id != appointment.id,
        ).first()
        if existing_in_consult:
            raise APIError(
                "DOCTOR_BUSY",
                f"Doctor already has token {existing_in_consult.token_number} in consultation. Complete it first.",
                400,
            )

    elif old_status == "IN_CONSULTATION" and target_status == "COMPLETED":
        if not (is_admin or is_own_doctor):
            raise APIError("FORBIDDEN", "Only the assigned Doctor or Admin can complete consultation.", 403)

    elif old_status in ("BOOKED", "CONFIRMED") and target_status == "CANCELLED":
        if not (is_admin or is_own_patient):
            raise APIError("FORBIDDEN", "Only the Patient or Admin can cancel an appointment.", 403)

    elif old_status in ("BOOKED", "CONFIRMED") and target_status == "NO_SHOW":
        if not (is_admin or is_own_doctor):
            raise APIError("FORBIDDEN", "Only the assigned Doctor or Admin can mark NO_SHOW.", 403)
        today = today_hospital()
        if today < appointment.appointment_date:
            raise APIError(
                "NO_SHOW_TOO_EARLY",
                "NO_SHOW can only be marked on or after the appointment date.",
                400,
            )

    else:
        raise APIError(
            "INVALID_TRANSITION",
            f"Invalid status transition from '{old_status}' to '{target_status}'.",
            400,
        )

    appointment.status = target_status
    appointment.updated_at = now_hospital_naive()

    history = AppointmentStatusHistory(
        appointment_id=appointment.id,
        old_status=old_status,
        new_status=target_status,
        changed_by_user_id=current_user.id,
        changed_at=now_hospital_naive(),
        note=(note or f"Status changed from {old_status} to {target_status}").strip(),
    )
    db.session.add(history)
    db.session.commit()

    NotificationService.send_notification(
        event_type="STATUS_UPDATED",
        subject=f"Appointment Status: {target_status} (Token {appointment.token_number})",
        message=f"Appointment {appointment.token_number} status changed from {old_status} to {target_status}.",
        appointment=appointment,
    )

    return appointment.to_dict(include_history=True)


def reschedule_appointment(
    current_user: User,
    appointment_id: int,
    new_doctor_id: int,
    new_date_str: str,
    new_slot_str: str,
) -> dict:
    """
    Reschedule a BOOKED or CONFIRMED appointment (Patient own or Admin).
    If doctor and date are unchanged, the token is kept.
    If the date or doctor changes, a new token is issued for the new day
    and the old one is saved in previous_token.
    """
    appointment = db.session.get(Appointment, appointment_id)
    if not appointment:
        raise APIError("NOT_FOUND", f"Appointment with id {appointment_id} not found.", 404)

    if appointment.status not in ("BOOKED", "CONFIRMED"):
        raise APIError(
            "INVALID_RESCHEDULE",
            f"Only BOOKED or CONFIRMED appointments can be rescheduled. Current status: '{appointment.status}'.",
            400,
        )

    # Permission check: Patient (own) or Admin
    if current_user.role == "PATIENT":
        if not current_user.patient_profile or current_user.patient_profile.id != appointment.patient_id:
            raise APIError("FORBIDDEN", "Patients can only reschedule their own appointments.", 403)
    elif current_user.role != "ADMIN":
        raise APIError("FORBIDDEN", "Only the Patient or an Admin can reschedule appointments.", 403)

    target_doctor = get_doctor_or_404(new_doctor_id)
    target_date = parse_date_str(new_date_str, "new_date")
    target_slot = parse_time_str(new_slot_str, "new_slot")

    # Validate slot, schedule and capacity excluding the current appointment
    validate_slot_and_capacity(
        target_doctor,
        target_date,
        target_slot,
        exclude_appointment_id=appointment.id,
    )

    old_doc_id = appointment.doctor_id
    old_date = appointment.appointment_date
    old_token = appointment.token_number

    # Token logic (Section 5.8):
    # If doctor and date are unchanged, the token is kept.
    # If the date or doctor changes, a new token is issued for the new day and old is in previous_token.
    if old_doc_id == target_doctor.id and old_date == target_date:
        # Same doctor and date, keep token
        pass
    else:
        new_token = _next_token_number(target_doctor, target_date)
        appointment.previous_token = old_token
        appointment.token_number = new_token

    appointment.doctor_id = target_doctor.id
    appointment.appointment_date = target_date
    appointment.slot_time = target_slot
    appointment.updated_at = now_hospital_naive()

    history = AppointmentStatusHistory(
        appointment_id=appointment.id,
        old_status=appointment.status,
        new_status=appointment.status,
        changed_by_user_id=current_user.id,
        changed_at=now_hospital_naive(),
        note=f"Rescheduled to Dr. {target_doctor.doc_code} on {target_date.isoformat()} at {target_slot.strftime('%H:%M')}",
    )
    db.session.add(history)
    db.session.commit()

    NotificationService.send_notification(
        event_type="APPOINTMENT_RESCHEDULED",
        subject=f"Appointment Rescheduled: Token {appointment.token_number}",
        message=f"Your appointment was rescheduled to Dr. {target_doctor.doc_code} on {target_date.isoformat()} at {target_slot.strftime('%H:%M')}. Current Token: {appointment.token_number}.",
        appointment=appointment,
    )

    return appointment.to_dict(include_history=True)


def cancel_appointment(
    current_user: User,
    appointment_id: int,
    reason: str | None = None,
) -> dict:
    """
    Cancel a BOOKED or CONFIRMED appointment (Patient own or Admin).
    Setting CANCELLED frees the slot (active_slot_key becomes NULL).
    """
    appointment = db.session.get(Appointment, appointment_id)
    if not appointment:
        raise APIError("NOT_FOUND", f"Appointment with id {appointment_id} not found.", 404)

    if appointment.status not in ("BOOKED", "CONFIRMED"):
        raise APIError(
            "INVALID_CANCELLATION",
            f"Only BOOKED or CONFIRMED appointments can be cancelled. Current status: '{appointment.status}'.",
            400,
        )

    # Permission check: Patient (own) or Admin
    if current_user.role == "PATIENT":
        if not current_user.patient_profile or current_user.patient_profile.id != appointment.patient_id:
            raise APIError("FORBIDDEN", "Patients can only cancel their own appointments.", 403)
    elif current_user.role != "ADMIN":
        raise APIError("FORBIDDEN", "Only the Patient or an Admin can cancel appointments.", 403)

    return transition_appointment_status(
        current_user=current_user,
        appointment_id=appointment_id,
        new_status="CANCELLED",
        note=reason or "Appointment cancelled by user request",
    )


def get_daily_queue(
    date_str: str | None = None,
    doctor_id: int | None = None,
    department_id: int | None = None,
) -> dict:
    """Return ordered daily queue (by slot_time ASC, token_number ASC) with current & waiting summary."""
    target_date = parse_date_str(date_str, "date") if date_str else today_hospital()

    query = Appointment.query.join(Doctor, Appointment.doctor_id == Doctor.id).filter(
        Appointment.appointment_date == target_date
    )

    if doctor_id is not None:
        query = query.filter(Appointment.doctor_id == doctor_id)
    if department_id is not None:
        query = query.filter(Doctor.department_id == department_id)

    appointments = query.order_by(
        Appointment.slot_time.asc(),
        Appointment.token_number.asc(),
    ).all()

    items = [a.to_dict() for a in appointments]
    in_consultation = [item for item in items if item["status"] == "IN_CONSULTATION"]
    waiting = [item for item in items if item["status"] in ("CONFIRMED", "BOOKED")]
    completed = [item for item in items if item["status"] == "COMPLETED"]

    return {
        "date": target_date.isoformat(),
        "doctor_id": doctor_id,
        "department_id": department_id,
        "current_in_consultation": in_consultation[0] if in_consultation else None,
        "in_consultation_list": in_consultation,
        "next_waiting": waiting,
        "completed_count": len(completed),
        "waiting_count": len(waiting),
        "total_count": len(items),
        "queue": items,
    }
