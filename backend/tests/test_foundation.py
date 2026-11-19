"""Tests for foundation setup, health endpoint, and SQL schema/seed scripts."""

from pathlib import Path
from werkzeug.security import check_password_hash
from backend.app import create_app
from backend.scripts.generate_seed_hashes import DEFAULT_ACCOUNTS, generate_hashes


def test_health_endpoint():
    """Verify /api/health returns 200 OK with service metadata and hospital timezone."""
    app = create_app(
        "testing",
        {
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "HOSPITAL_TIMEZONE": "Asia/Kolkata",
        },
    )
    client = app.test_client()
    res = client.get("/api/health")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["status"] == "ok"
    assert payload["timezone"] == "Asia/Kolkata"
    assert "timestamp" in payload


def test_schema_and_seed_sql_files_exist_and_valid():
    """Verify schema.sql and seed.sql contain required tables, active_slot_key, and real hashes."""
    repo_root = Path(__file__).resolve().parents[2]
    schema_path = repo_root / "backend" / "database" / "schema.sql"
    seed_path = repo_root / "backend" / "database" / "seed.sql"

    assert schema_path.exists()
    assert seed_path.exists()

    schema_text = schema_path.read_text(encoding="utf-8")
    required_tables = [
        "CREATE TABLE users",
        "CREATE TABLE patients",
        "CREATE TABLE departments",
        "CREATE TABLE doctors",
        "CREATE TABLE doctor_schedules",
        "CREATE TABLE appointments",
        "CREATE TABLE doctor_token_counters",
        "CREATE TABLE appointment_status_history",
        "CREATE TABLE notification_logs",
    ]
    for table_stmt in required_tables:
        assert table_stmt in schema_text

    assert "active_slot_key" in schema_text
    assert "GENERATED ALWAYS AS" in schema_text
    assert "STORED" in schema_text
    assert "uq_appointments_active_slot_key" in schema_text
    assert "uq_appointments_doctor_date_token" in schema_text

    seed_text = seed_path.read_text(encoding="utf-8")
    assert "CURDATE()" in seed_text
    assert "scrypt:" in seed_text


def test_generate_seed_hashes_verifies():
    """Verify generate_seed_hashes produces valid Werkzeug hashes for all default accounts."""
    hashes = generate_hashes()
    for email, password in DEFAULT_ACCOUNTS:
        assert email in hashes
        assert check_password_hash(hashes[email], password)
