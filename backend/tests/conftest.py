"""Shared pytest fixtures for backend unit and integration tests."""

import pytest
from werkzeug.security import generate_password_hash
from backend.app import create_app
from backend.app.extensions import db
from backend.app.models import Department, Doctor, DoctorSchedule, Patient, User
from backend.app.utils.auth import create_access_token


@pytest.fixture()
def app(tmp_path):
    """Create a fresh Flask test application backed by a temporary SQLite database file."""
    db_file = tmp_path / "test_hospital.sqlite"
    test_app = create_app(
        "testing",
        {
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_file}",
            "HOSPITAL_TIMEZONE": "Asia/Kolkata",
            "JWT_SECRET_KEY": "test-jwt-secret-key",
        },
    )
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    """Return a Flask test client."""
    return app.test_client()


@pytest.fixture()
def seeded_data(app):
    """Seed baseline admin, doctor, department, schedule, and patient accounts for tests."""
    with app.app_context():
        admin_user = User(
            name="Test Admin",
            email="admin@hospital.test",
            password_hash=generate_password_hash("Admin@123", method="scrypt"),
            role="ADMIN",
            is_active=True,
        )
        doc_user = User(
            name="Dr. Aarav Sharma",
            email="doctor1@hospital.test",
            password_hash=generate_password_hash("Doctor@123", method="scrypt"),
            role="DOCTOR",
            is_active=True,
        )
        pat_user = User(
            name="Ananya Gupta",
            email="patient1@hospital.test",
            password_hash=generate_password_hash("Patient@123", method="scrypt"),
            role="PATIENT",
            is_active=True,
        )
        db.session.add_all([admin_user, doc_user, pat_user])
        db.session.flush()

        dept = Department(name="Cardiology", description="Heart care")
        db.session.add(dept)
        db.session.flush()

        doctor = Doctor(
            user_id=doc_user.id,
            department_id=dept.id,
            doc_code="DOC1",
            specialization="Senior Cardiologist",
            room_number="Room 101",
            default_slot_duration_minutes=15,
            is_active=True,
        )
        patient = Patient(
            user_id=pat_user.id,
            full_name="Ananya Gupta",
            phone="9876543210",
            email="patient1@hospital.test",
        )
        db.session.add_all([doctor, patient])
        db.session.flush()

        # Add schedule for all 7 days (0..6): 09:00-11:00, 30-min slots (4 slots), max_patients=3
        from datetime import time

        for day_idx in range(7):
            db.session.add(
                DoctorSchedule(
                    doctor_id=doctor.id,
                    day_of_week=day_idx,
                    start_time=time(9, 0),
                    end_time=time(11, 0),
                    slot_duration_minutes=30,
                    max_patients=3,
                    is_active=True,
                )
            )
        db.session.commit()

        return {
            "admin_id": admin_user.id,
            "admin_token": create_access_token(admin_user),
            "doctor_user_id": doc_user.id,
            "doctor_id": doctor.id,
            "doctor_token": create_access_token(doc_user),
            "patient_user_id": pat_user.id,
            "patient_id": patient.id,
            "patient_token": create_access_token(pat_user),
            "department_id": dept.id,
        }
