"""Tests for Sub-Phase 1B: Authentication, RBAC decorators, Departments, Doctors, Schedules, and Slots."""

from datetime import timedelta
from backend.app.utils.timezone import today_hospital


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_register_always_creates_patient_and_linked_profile(client):
    """Self-registration must ignore any client-supplied role (e.g. ADMIN) and create PATIENT + Patient row."""
    res = client.post(
        "/api/auth/register",
        json={
            "name": "Rahul Verma",
            "email": "rahul@example.com",
            "password": "Password123",
            "phone": "9998887776",
            "role": "ADMIN",  # Must be ignored!
        },
    )
    assert res.status_code == 201
    body = res.get_json()
    assert "token" in body
    assert body["user"]["role"] == "PATIENT"
    assert body["user"]["email"] == "rahul@example.com"
    assert body["patient"]["full_name"] == "Rahul Verma"
    assert body["patient"]["phone"] == "9998887776"
    assert body["user"]["patient_id"] == body["patient"]["id"]


def test_register_validation_and_duplicate_email(client):
    """Registration rejects invalid email, short password (<8 chars), or duplicate email."""
    # Invalid email
    res_bad_email = client.post(
        "/api/auth/register",
        json={"name": "Test", "email": "not-an-email", "password": "Password123", "phone": "12345"},
    )
    assert res_bad_email.status_code == 400
    assert "error" in res_bad_email.get_json()

    # Short password
    res_short_pw = client.post(
        "/api/auth/register",
        json={"name": "Test", "email": "valid@example.com", "password": "short", "phone": "12345"},
    )
    assert res_short_pw.status_code == 400

    # Valid registration then duplicate
    res_ok = client.post(
        "/api/auth/register",
        json={"name": "Test", "email": "dup@example.com", "password": "Password123", "phone": "12345"},
    )
    assert res_ok.status_code == 201

    res_dup = client.post(
        "/api/auth/register",
        json={"name": "Test 2", "email": "dup@example.com", "password": "Password123", "phone": "12345"},
    )
    assert res_dup.status_code == 409
    assert res_dup.get_json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_login_and_me_endpoint(client, seeded_data):
    """POST /api/auth/login returns JWT token and GET /api/auth/me returns role-linked profile."""
    res_login = client.post(
        "/api/auth/login",
        json={"email": "patient1@hospital.test", "password": "Patient@123"},
    )
    assert res_login.status_code == 200
    token = res_login.get_json()["token"]

    # Wrong password returns 401
    res_bad = client.post(
        "/api/auth/login",
        json={"email": "patient1@hospital.test", "password": "WrongPassword"},
    )
    assert res_bad.status_code == 401
    assert res_bad.get_json()["error"]["code"] == "INVALID_CREDENTIALS"

    # GET /api/auth/me with valid token
    res_me = client.get("/api/auth/me", headers=auth_headers(token))
    assert res_me.status_code == 200
    me_data = res_me.get_json()
    assert me_data["user"]["email"] == "patient1@hospital.test"
    assert me_data["user"]["role"] == "PATIENT"
    assert me_data["patient"]["id"] == seeded_data["patient_id"]

    # GET /api/auth/me without token returns 401
    res_no_auth = client.get("/api/auth/me")
    assert res_no_auth.status_code == 401


def test_rbac_department_and_doctor_creation(client, seeded_data):
    """Only ADMIN can create departments, doctors, and schedules; PATIENT and DOCTOR get 403."""
    patient_headers = auth_headers(seeded_data["patient_token"])
    doctor_headers = auth_headers(seeded_data["doctor_token"])
    admin_headers = auth_headers(seeded_data["admin_token"])

    # Patient cannot create department
    res_pat_dept = client.post(
        "/api/departments",
        json={"name": "Neurology", "description": "Brain care"},
        headers=patient_headers,
    )
    assert res_pat_dept.status_code == 403

    # Doctor cannot create department
    res_doc_dept = client.post(
        "/api/departments",
        json={"name": "Neurology", "description": "Brain care"},
        headers=doctor_headers,
    )
    assert res_doc_dept.status_code == 403

    # Admin creates department
    res_adm_dept = client.post(
        "/api/departments",
        json={"name": "Neurology", "description": "Brain and nervous system"},
        headers=admin_headers,
    )
    assert res_adm_dept.status_code == 201
    neuro_id = res_adm_dept.get_json()["department"]["id"]

    # Duplicate department name returns 409
    res_dup_dept = client.post(
        "/api/departments",
        json={"name": "Neurology"},
        headers=admin_headers,
    )
    assert res_dup_dept.status_code == 409

    # Admin creates Doctor profile + DOCTOR user account
    res_create_doc = client.post(
        "/api/doctors",
        json={
            "name": "Dr. Neha Kapoor",
            "email": "neha.kapoor@hospital.test",
            "password": "Doctor@123",
            "department_id": neuro_id,
            "doc_code": "DOC2",
            "specialization": "Consultant Neurologist",
            "room_number": "Room 402",
            "default_slot_duration_minutes": 20,
        },
        headers=admin_headers,
    )
    assert res_create_doc.status_code == 201
    new_doc = res_create_doc.get_json()["doctor"]
    assert new_doc["doc_code"] == "DOC2"
    assert new_doc["department_name"] == "Neurology"

    # Newly created doctor can log in as DOCTOR
    res_doc_login = client.post(
        "/api/auth/login",
        json={"email": "neha.kapoor@hospital.test", "password": "Doctor@123"},
    )
    assert res_doc_login.status_code == 200
    assert res_doc_login.get_json()["user"]["role"] == "DOCTOR"


def test_schedule_overlap_rejection_and_slot_generation(client, seeded_data):
    """Overlapping schedules on the same weekday are rejected (409), and slots respect effective capacity."""
    admin_headers = auth_headers(seeded_data["admin_token"])
    doctor_id = seeded_data["doctor_id"]

    # Seeded schedule has 09:00 - 11:00 on all days (0..6).
    # Attempting an overlapping schedule 10:00 - 12:00 on day 0 must return 409 SCHEDULE_OVERLAP
    res_overlap = client.post(
        f"/api/doctors/{doctor_id}/schedules",
        json={
            "day_of_week": 0,
            "start_time": "10:00",
            "end_time": "12:00",
            "slot_duration_minutes": 30,
            "max_patients": 4,
        },
        headers=admin_headers,
    )
    assert res_overlap.status_code == 409
    assert res_overlap.get_json()["error"]["code"] == "SCHEDULE_OVERLAP"

    # Non-overlapping afternoon schedule on tomorrow's weekday succeeds
    tomorrow = today_hospital() + timedelta(days=1)
    tomorrow_weekday = tomorrow.weekday()

    res_afternoon = client.post(
        f"/api/doctors/{doctor_id}/schedules",
        json={
            "day_of_week": tomorrow_weekday,
            "start_time": "14:00",
            "end_time": "15:00",
            "slot_duration_minutes": 30,
            "max_patients": 2,
        },
        headers=admin_headers,
    )
    assert res_afternoon.status_code == 201

    # Query slots for tomorrow:
    # Morning: 09:00-11:00 @ 30m = 4 slots (09:00, 09:30, 10:00, 10:30), max_patients=3
    # Afternoon: 14:00-15:00 @ 30m = 2 slots (14:00, 14:30), max_patients=2
    # Total slots = 6, total max_patients = 5 -> effective_capacity = min(6, 5) = 5
    res_slots = client.get(f"/api/doctors/{doctor_id}/slots?date={tomorrow.isoformat()}")
    assert res_slots.status_code == 200
    slots_data = res_slots.get_json()
    assert slots_data["total_slots"] == 6
    assert slots_data["max_patients"] == 5
    assert slots_data["effective_capacity"] == 5
    assert slots_data["remaining_capacity"] == 5
    slot_times = [s["slot_time"] for s in slots_data["slots"]]
    assert slot_times == ["09:00", "09:30", "10:00", "10:30", "14:00", "14:30"]
    assert all(s["is_available"] for s in slots_data["slots"])
