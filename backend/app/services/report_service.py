"""Daily reporting and CSV export service."""

import csv
import io
from collections import defaultdict
from datetime import date
from sqlalchemy import text
from backend.app.extensions import db
from backend.app.models import Appointment, Doctor, Patient
from backend.app.services.master_service import parse_date_str
from backend.app.utils.timezone import today_hospital


def generate_daily_report(date_str: str | None = None) -> dict:
    """
    Produce daily analytics (Admin only):
    - total appointments
    - counts per status
    - appointments per doctor
    - online vs walk-in counts
    - hourly / slot distribution
    """
    target_date = parse_date_str(date_str, "date") if date_str else today_hospital()

    appointments = (
        Appointment.query.filter(Appointment.appointment_date == target_date)
        .order_by(Appointment.slot_time.asc())
        .all()
    )

    total_count = len(appointments)
    status_counts = defaultdict(int)
    doctor_counts = defaultdict(int)
    type_counts = {"ONLINE": 0, "WALK_IN": 0}
    hourly_distribution = defaultdict(int)

    for appt in appointments:
        status_counts[appt.status] += 1
        doc_label = appt.doctor.doc_code if appt.doctor else f"Doc {appt.doctor_id}"
        doctor_counts[doc_label] += 1
        if appt.booking_type in type_counts:
            type_counts[appt.booking_type] += 1
        if appt.slot_time:
            hour_key = f"{appt.slot_time.hour:02d}:00"
            hourly_distribution[hour_key] += 1

    return {
        "date": target_date.isoformat(),
        "total_appointments": total_count,
        "status_breakdown": dict(status_counts),
        "doctor_distribution": dict(doctor_counts),
        "booking_type_breakdown": type_counts,
        "hourly_distribution": dict(sorted(hourly_distribution.items())),
    }


def export_daily_appointments_csv(date_str: str | None = None) -> str:
    """
    Return CSV string of appointments on target date:
    appointment id, token, patient, doctor, department, slot, type, status
    """
    target_date = parse_date_str(date_str, "date") if date_str else today_hospital()

    appointments = (
        Appointment.query.filter(Appointment.appointment_date == target_date)
        .order_by(Appointment.slot_time.asc(), Appointment.token_number.asc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Appointment ID",
        "Token Number",
        "Patient Name",
        "Doctor Name",
        "Department",
        "Slot Time",
        "Booking Type",
        "Status",
        "Reason",
    ])

    for a in appointments:
        writer.writerow([
            a.id,
            a.token_number,
            a.patient.full_name if a.patient else "",
            a.doctor.user.name if a.doctor and a.doctor.user else (a.doctor.doc_code if a.doctor else ""),
            a.doctor.department.name if a.doctor and a.doctor.department else "",
            a.slot_time.strftime("%H:%M") if a.slot_time else "",
            a.booking_type,
            a.status,
            a.reason or "",
        ])

    return output.getvalue()
