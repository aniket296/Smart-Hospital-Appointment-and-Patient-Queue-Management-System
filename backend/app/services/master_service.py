"""Master data service: Departments, Doctors, Schedules, Slot Generation, and Patients listing."""

from datetime import date, datetime, time, timedelta
from werkzeug.security import generate_password_hash
from backend.app.extensions import db
from backend.app.models import Appointment, Department, Doctor, DoctorSchedule, Patient, User
from backend.app.services.auth_service import validate_email, validate_password
from backend.app.utils.errors import APIError
from backend.app.utils.timezone import current_time_hospital, today_hospital


def parse_time_str(value: str, field_name: str = "time") -> time:
    """Parse HH:MM or HH:MM:SS string into a datetime.time object with seconds=0."""
    if not value or not isinstance(value, str):
        raise APIError("VALIDATION_ERROR", f"{field_name} is required (HH:MM).", 400)
    raw = value.strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            parsed = datetime.strptime(raw, fmt).time()
            return time(parsed.hour, parsed.minute, 0)
        except ValueError:
            continue
    raise APIError("VALIDATION_ERROR", f"Invalid {field_name} format '{value}'. Expected HH:MM.", 400)


def parse_date_str(value: str, field_name: str = "date") -> date:
    """Parse YYYY-MM-DD into a datetime.date object."""
    if not value or not isinstance(value, str):
        raise APIError("VALIDATION_ERROR", f"{field_name} is required (YYYY-MM-DD).", 400)
    raw = value.strip()
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise APIError(
            "VALIDATION_ERROR",
            f"Invalid {field_name} '{value}'. Expected YYYY-MM-DD.",
            400,
        ) from exc


def list_departments() -> list[dict]:
    """Return all departments ordered by name."""
    departments = Department.query.order_by(Department.name.asc()).all()
    return [d.to_dict() for d in departments]


def create_department(data: dict) -> dict:
    """Create a new hospital department (Admin only)."""
    if not isinstance(data, dict):
        raise APIError("VALIDATION_ERROR", "Invalid JSON payload.", 400)

    name = (data.get("name") or "").strip()
    if not name:
        raise APIError("VALIDATION_ERROR", "Department name is required.", 400)

    existing = Department.query.filter(db.func.lower(Department.name) == name.lower()).first()
    if existing:
        raise APIError("CONFLICT", f"Department '{name}' already exists.", 409)

    description = (data.get("description") or "").strip() or None
    dept = Department(name=name, description=description)
    db.session.add(dept)
    db.session.commit()
    return dept.to_dict()


def list_doctors(
    department_id: int | None = None,
    active_only: bool = False,
    include_schedules: bool = False,
) -> list[dict]:
    """List doctors with optional department and active filtering."""
    query = Doctor.query
    if department_id is not None:
        query = query.filter(Doctor.department_id == department_id)
    if active_only:
        query = query.filter(Doctor.is_active.is_(True))
    doctors = query.order_by(Doctor.doc_code.asc()).all()
    return [d.to_dict(include_schedules=include_schedules) for d in doctors]


def get_doctor_or_404(doctor_id: int) -> Doctor:
    """Fetch a Doctor by ID or raise 404 APIError."""
    doctor = db.session.get(Doctor, doctor_id)
    if not doctor:
        raise APIError("NOT_FOUND", f"Doctor with id {doctor_id} not found.", 404)
    return doctor


def create_doctor(data: dict) -> dict:
    """Create a DOCTOR user account and linked Doctor profile in one transaction (Admin only)."""
    if not isinstance(data, dict):
        raise APIError("VALIDATION_ERROR", "Invalid JSON payload.", 400)

    name = (data.get("name") or "").strip()
    if not name:
        raise APIError("VALIDATION_ERROR", "Doctor name is required.", 400)

    email = validate_email(data.get("email", ""))
    password = validate_password(data.get("password", "Doctor@123"))

    doc_code = (data.get("doc_code") or "").strip().upper()
    if not doc_code:
        raise APIError("VALIDATION_ERROR", "doc_code is required (e.g. DOC1).", 400)

    specialization = (data.get("specialization") or "").strip()
    if not specialization:
        raise APIError("VALIDATION_ERROR", "specialization is required.", 400)

    room_number = (data.get("room_number") or "").strip()
    if not room_number:
        raise APIError("VALIDATION_ERROR", "room_number is required.", 400)

    try:
        department_id = int(data.get("department_id"))
    except (TypeError, ValueError) as exc:
        raise APIError("VALIDATION_ERROR", "Valid department_id is required.", 400) from exc

    department = db.session.get(Department, department_id)
    if not department:
        raise APIError("NOT_FOUND", f"Department with id {department_id} not found.", 404)

    try:
        default_slot = int(data.get("default_slot_duration_minutes", 15))
    except (TypeError, ValueError) as exc:
        raise APIError("VALIDATION_ERROR", "default_slot_duration_minutes must be an integer.", 400) from exc

    if default_slot <= 0 or default_slot > 240:
        raise APIError("VALIDATION_ERROR", "default_slot_duration_minutes must be between 1 and 240.", 400)

    if User.query.filter_by(email=email).first():
        raise APIError("CONFLICT", f"User with email '{email}' already exists.", 409)

    if Doctor.query.filter_by(doc_code=doc_code).first():
        raise APIError("CONFLICT", f"Doctor with doc_code '{doc_code}' already exists.", 409)

    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password, method="scrypt"),
        role="DOCTOR",
        is_active=True,
    )
    db.session.add(user)
    db.session.flush()

    doctor = Doctor(
        user_id=user.id,
        department_id=department.id,
        doc_code=doc_code,
        specialization=specialization,
        room_number=room_number,
        default_slot_duration_minutes=default_slot,
        is_active=bool(data.get("is_active", True)),
    )
    db.session.add(doctor)
    db.session.commit()

    return doctor.to_dict(include_schedules=True)


def list_doctor_schedules(doctor_id: int) -> list[dict]:
    """List all schedules for a given doctor ordered by day_of_week and start_time."""
    doctor = get_doctor_or_404(doctor_id)
    return [s.to_dict() for s in doctor.schedules]


def _times_overlap(start_a: time, end_a: time, start_b: time, end_b: time) -> bool:
    """Return True if half-open intervals [start_a, end_a) and [start_b, end_b) overlap."""
    return start_a < end_b and start_b < end_a


def create_doctor_schedule(doctor_id: int, data: dict) -> dict:
    """Create a schedule for a doctor, rejecting invalid ranges or overlaps on the same weekday."""
    doctor = get_doctor_or_404(doctor_id)
    if not isinstance(data, dict):
        raise APIError("VALIDATION_ERROR", "Invalid JSON payload.", 400)

    try:
        day_of_week = int(data.get("day_of_week"))
    except (TypeError, ValueError) as exc:
        raise APIError("VALIDATION_ERROR", "day_of_week must be an integer 0 (Monday) to 6 (Sunday).", 400) from exc

    if day_of_week < 0 or day_of_week > 6:
        raise APIError("VALIDATION_ERROR", "day_of_week must be between 0 (Monday) and 6 (Sunday).", 400)

    start_time = parse_time_str(data.get("start_time"), "start_time")
    end_time = parse_time_str(data.get("end_time"), "end_time")

    if start_time >= end_time:
        raise APIError("VALIDATION_ERROR", "start_time must be earlier than end_time.", 400)

    raw_slot_duration = data.get("slot_duration_minutes", doctor.default_slot_duration_minutes)
    try:
        slot_duration = int(raw_slot_duration)
    except (TypeError, ValueError) as exc:
        raise APIError("VALIDATION_ERROR", "slot_duration_minutes must be a positive integer.", 400) from exc

    if slot_duration <= 0 or slot_duration > 240:
        raise APIError("VALIDATION_ERROR", "slot_duration_minutes must be between 1 and 240.", 400)

    window_minutes = (
        (end_time.hour * 60 + end_time.minute) - (start_time.hour * 60 + start_time.minute)
    )
    if window_minutes < slot_duration:
        raise APIError(
            "VALIDATION_ERROR",
            "Schedule window must be at least one slot_duration_minutes long.",
            400,
        )

    try:
        max_patients = int(data.get("max_patients"))
    except (TypeError, ValueError) as exc:
        raise APIError("VALIDATION_ERROR", "max_patients must be a positive integer.", 400) from exc

    if max_patients <= 0:
        raise APIError("VALIDATION_ERROR", "max_patients must be greater than 0.", 400)

    # Check overlapping schedules for the same doctor and day_of_week
    existing_schedules = DoctorSchedule.query.filter_by(
        doctor_id=doctor.id,
        day_of_week=day_of_week,
    ).all()

    for sched in existing_schedules:
        if _times_overlap(start_time, end_time, sched.start_time, sched.end_time):
            raise APIError(
                "SCHEDULE_OVERLAP",
                f"Schedule {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')} "
                f"overlaps with existing schedule "
                f"{sched.start_time.strftime('%H:%M')}-{sched.end_time.strftime('%H:%M')} "
                f"on day {day_of_week}.",
                409,
            )

    schedule = DoctorSchedule(
        doctor_id=doctor.id,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        slot_duration_minutes=slot_duration,
        max_patients=max_patients,
        is_active=bool(data.get("is_active", True)),
    )
    db.session.add(schedule)
    db.session.commit()
    return schedule.to_dict()


def generate_slots_for_schedule(sched: DoctorSchedule) -> list[time]:
    """Split [start_time, end_time) by slot_duration_minutes."""
    slots: list[time] = []
    base_day = date(2000, 1, 1)
    cursor = datetime.combine(base_day, sched.start_time)
    end_dt = datetime.combine(base_day, sched.end_time)
    step = timedelta(minutes=sched.slot_duration_minutes)

    while cursor + step <= end_dt:
        slots.append(cursor.time())
        cursor += step
    return slots


def get_doctor_slots_for_date(doctor_id: int, date_str: str) -> dict:
    """Compute all slots, availability, and effective daily capacity for a doctor and date."""
    doctor = get_doctor_or_404(doctor_id)
    target_date = parse_date_str(date_str, "date")
    weekday = target_date.weekday()  # 0 = Monday ... 6 = Sunday

    active_schedules = (
        DoctorSchedule.query.filter_by(
            doctor_id=doctor.id,
            day_of_week=weekday,
            is_active=True,
        )
        .order_by(DoctorSchedule.start_time.asc())
        .all()
    )

    # Fetch non-cancelled appointments for this doctor and date
    active_appointments = (
        Appointment.query.filter(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_date == target_date,
            Appointment.status != "CANCELLED",
        ).all()
    )
    booked_times = {
        appt.slot_time.strftime("%H:%M") for appt in active_appointments if appt.slot_time
    }
    booked_count = len(active_appointments)

    today = today_hospital()
    now_time = current_time_hospital()

    all_generated_slots: list[time] = []
    total_max_patients = 0
    for sched in active_schedules:
        sched_slots = generate_slots_for_schedule(sched)
        all_generated_slots.extend(sched_slots)
        total_max_patients += sched.max_patients

    total_slots_count = len(all_generated_slots)
    effective_capacity = min(total_slots_count, total_max_patients) if active_schedules else 0
    remaining_capacity = max(0, effective_capacity - booked_count)
    capacity_reached = booked_count >= effective_capacity

    slots_payload = []
    for slot_t in all_generated_slots:
        slot_label = slot_t.strftime("%H:%M")
        is_booked = slot_label in booked_times
        is_past = (target_date < today) or (target_date == today and slot_t < now_time)
        is_available = (not is_booked) and (not is_past) and (not capacity_reached) and doctor.is_active
        slots_payload.append(
            {
                "slot_time": slot_label,
                "is_booked": is_booked,
                "is_past": is_past,
                "is_available": is_available,
            }
        )

    return {
        "doctor_id": doctor.id,
        "doc_code": doctor.doc_code,
        "doctor_name": doctor.user.name if doctor.user else None,
        "date": target_date.isoformat(),
        "day_of_week": weekday,
        "total_slots": total_slots_count,
        "max_patients": total_max_patients,
        "effective_capacity": effective_capacity,
        "booked_count": booked_count,
        "remaining_capacity": remaining_capacity,
        "slots": slots_payload,
    }


def list_patients(search: str | None = None) -> list[dict]:
    """List or search patients (Admin only, used for walk-in registration)."""
    query = Patient.query
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            db.or_(
                Patient.full_name.ilike(term),
                Patient.phone.ilike(term),
                Patient.email.ilike(term),
            )
        )
    patients = query.order_by(Patient.full_name.asc()).limit(100).all()
    return [p.to_dict() for p in patients]
