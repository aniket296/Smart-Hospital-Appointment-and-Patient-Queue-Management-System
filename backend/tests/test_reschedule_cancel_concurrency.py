"""Tests for Sub-Phase 2A: Rescheduling, Cancellation, and Multi-Threaded Concurrency."""

import concurrent.futures
from datetime import timedelta
from backend.app import create_app
from backend.app.extensions import db
from backend.app.models import Appointment, Doctor, DoctorSchedule, Patient, User
from backend.app.utils.auth import create_access_token
from backend.app.utils.timezone import today_hospital


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_reschedule_same_doctor_and_date_keeps_token(client, seeded_data):
    """Rescheduling to a different slot on the same day with same doctor keeps the token."""
    patient_headers = auth_headers(seeded_data["patient_token"])
    doctor_id = seeded_data["doctor_id"]
    tomorrow = (today_hospital() + timedelta(days=1)).isoformat()

    # Initial booking 09:00 -> DOC1-001
    res1 = client.post(
        "/api/appointments",
        json={"doctor_id": doctor_id, "appointment_date": tomorrow, "slot_time": "09:00"},
        headers=patient_headers,
    )
    assert res1.status_code == 201
    appt_id = res1.get_json()["appointment"]["id"]
    assert res1.get_json()["appointment"]["token_number"] == "DOC1-001"

    # Reschedule to 09:30 on same date -> token DOC1-001 retained
    res_resched = client.patch(
        f"/api/appointments/{appt_id}/reschedule",
        json={"doctor_id": doctor_id, "appointment_date": tomorrow, "slot_time": "09:30"},
        headers=patient_headers,
    )
    assert res_resched.status_code == 200
    updated = res_resched.get_json()["appointment"]
    assert updated["token_number"] == "DOC1-001"
    assert updated["slot_time"] == "09:30"
    assert updated["previous_token"] is None

    # The old slot 09:00 should now be free for someone else
    res_old_slot = client.post(
        "/api/appointments",
        json={"doctor_id": doctor_id, "appointment_date": tomorrow, "slot_time": "09:00"},
        headers=patient_headers,
    )
    assert res_old_slot.status_code == 201
    assert res_old_slot.get_json()["appointment"]["token_number"] == "DOC1-002"


def test_reschedule_different_date_issues_new_token_and_saves_previous(client, seeded_data):
    """Rescheduling to a different date issues a new token and records old token in previous_token."""
    patient_headers = auth_headers(seeded_data["patient_token"])
    doctor_id = seeded_data["doctor_id"]
    tomorrow = today_hospital() + timedelta(days=1)
    day_after = today_hospital() + timedelta(days=2)

    # Initial booking on tomorrow -> DOC1-001
    res1 = client.post(
        "/api/appointments",
        json={"doctor_id": doctor_id, "appointment_date": tomorrow.isoformat(), "slot_time": "09:00"},
        headers=patient_headers,
    )
    assert res1.status_code == 201
    appt_id = res1.get_json()["appointment"]["id"]
    assert res1.get_json()["appointment"]["token_number"] == "DOC1-001"

    # Reschedule to day_after -> new token issued, previous_token = DOC1-001
    res_resched = client.patch(
        f"/api/appointments/{appt_id}/reschedule",
        json={"doctor_id": doctor_id, "appointment_date": day_after.isoformat(), "slot_time": "10:00"},
        headers=patient_headers,
    )
    assert res_resched.status_code == 200
    updated = res_resched.get_json()["appointment"]
    assert updated["previous_token"] == "DOC1-001"
    assert updated["token_number"] == "DOC1-001"  # first token for that doctor on day_after
    assert updated["appointment_date"] == day_after.isoformat()
    assert updated["slot_time"] == "10:00"


def test_cancel_endpoint_frees_slot(client, seeded_data):
    """POST /api/appointments/<id>/cancel sets CANCELLED and frees the slot."""
    patient_headers = auth_headers(seeded_data["patient_token"])
    doctor_id = seeded_data["doctor_id"]
    tomorrow = (today_hospital() + timedelta(days=1)).isoformat()

    res1 = client.post(
        "/api/appointments",
        json={"doctor_id": doctor_id, "appointment_date": tomorrow, "slot_time": "09:00"},
        headers=patient_headers,
    )
    assert res1.status_code == 201
    appt_id = res1.get_json()["appointment"]["id"]

    res_cancel = client.post(
        f"/api/appointments/{appt_id}/cancel",
        json={"reason": "Schedule conflict"},
        headers=patient_headers,
    )
    assert res_cancel.status_code == 200
    assert res_cancel.get_json()["appointment"]["status"] == "CANCELLED"

    # Rebook 09:00 succeeds
    res_rebook = client.post(
        "/api/appointments",
        json={"doctor_id": doctor_id, "appointment_date": tomorrow, "slot_time": "09:00"},
        headers=patient_headers,
    )
    assert res_rebook.status_code == 201


def test_concurrent_bookings_exact_one_succeeds(tmp_path):
    """Concurrency test: multiple concurrent requests book the exact same slot; exactly one succeeds with 201 and others get 409."""
    db_file = tmp_path / "concurrent_hospital.sqlite"
    app = create_app(
        "testing",
        {
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_file}",
            "HOSPITAL_TIMEZONE": "Asia/Kolkata",
            "JWT_SECRET_KEY": "concurrent-secret",
        },
    )

    with app.app_context():
        db.create_all()
        # Create users
        from datetime import time
        from werkzeug.security import generate_password_hash
        admin = User(name="Admin", email="admin@c.test", password_hash=generate_password_hash("pass"), role="ADMIN")
        doc_user = User(name="Doc", email="doc@c.test", password_hash=generate_password_hash("pass"), role="DOCTOR")
        db.session.add_all([admin, doc_user])
        db.session.flush()

        from backend.app.models import Department
        dept = Department(name="General", description="General")
        db.session.add(dept)
        db.session.flush()

        doctor = Doctor(user_id=doc_user.id, department_id=dept.id, doc_code="DOCX", specialization="Gen", room_number="1")
        db.session.add(doctor)
        db.session.flush()

        for d in range(7):
            db.session.add(DoctorSchedule(doctor_id=doctor.id, day_of_week=d, start_time=time(9, 0), end_time=time(11, 0), slot_duration_minutes=30, max_patients=5))

        # Create 5 patient users
        patients_info = []
        for i in range(5):
            u = User(name=f"Pat {i}", email=f"pat{i}@c.test", password_hash=generate_password_hash("pass"), role="PATIENT")
            db.session.add(u)
            db.session.flush()
            p = Patient(user_id=u.id, full_name=f"Pat {i}", phone=f"900000000{i}", email=u.email)
            db.session.add(p)
            db.session.flush()
            patients_info.append({"user_id": u.id, "token": create_access_token(u)})
        db.session.commit()
        doc_id = doctor.id

    target_date = (today_hospital() + timedelta(days=2)).isoformat()
    target_slot = "09:30"

    def attempt_booking(pat):
        with app.test_client() as c:
            r = c.post(
                "/api/appointments",
                json={"doctor_id": doc_id, "appointment_date": target_date, "slot_time": target_slot},
                headers={"Authorization": f"Bearer {pat['token']}"},
            )
            return r.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(attempt_booking, patients_info))

    successes = [code for code in results if code == 201]
    conflicts = [code for code in results if code == 409]

    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}: {results}"
    assert len(conflicts) == 4, f"Expected 4 conflicts (409), got {len(conflicts)}: {results}"
