"""Tests for Sub-Phase 3A: Render & PostgreSQL backend readiness."""

from pathlib import Path
from backend.app import create_app
from backend.app.config import normalize_database_url, parse_cors_origins


def test_normalize_database_url_converts_postgres_schemes():
    """Verify postgres:// and postgresql:// are normalized to postgresql+psycopg2://."""
    assert (
        normalize_database_url("postgres://user:pass@dpg-xyz.render.com:5432/hospital_queue_db")
        == "postgresql+psycopg2://user:pass@dpg-xyz.render.com:5432/hospital_queue_db"
    )
    assert (
        normalize_database_url("postgresql://user:pass@dpg-xyz.render.com:5432/hospital_queue_db")
        == "postgresql+psycopg2://user:pass@dpg-xyz.render.com:5432/hospital_queue_db"
    )
    # Leave mysql and sqlite URLs untouched
    assert (
        normalize_database_url("mysql+pymysql://root:pass@127.0.0.1:3306/hospital_queue_db")
        == "mysql+pymysql://root:pass@127.0.0.1:3306/hospital_queue_db"
    )
    assert normalize_database_url("sqlite:///:memory:") == "sqlite:///:memory:"
    assert normalize_database_url(None) is None
    assert normalize_database_url("") is None


def test_parse_cors_origins():
    """Verify CORS_ORIGINS parsing supports wildcard and comma-separated origin lists."""
    assert parse_cors_origins(None) == "*"
    assert parse_cors_origins("") == "*"
    assert parse_cors_origins("*") == "*"
    assert parse_cors_origins("https://smart-hospital-web.onrender.com") == [
        "https://smart-hospital-web.onrender.com"
    ]
    assert parse_cors_origins(
        "https://smart-hospital-web.onrender.com, http://localhost:5173 "
    ) == [
        "https://smart-hospital-web.onrender.com",
        "http://localhost:5173",
    ]


def test_postgres_schema_and_seed_files_exist_and_valid():
    """Verify postgres_schema.sql and postgres_seed.sql contain required PostgreSQL constructs."""
    repo_root = Path(__file__).resolve().parents[2]
    pg_schema = repo_root / "backend" / "database" / "postgres_schema.sql"
    pg_seed = repo_root / "backend" / "database" / "postgres_seed.sql"

    assert pg_schema.exists()
    assert pg_seed.exists()

    schema_sql = pg_schema.read_text(encoding="utf-8")
    for table_name in [
        "CREATE TABLE users",
        "CREATE TABLE patients",
        "CREATE TABLE departments",
        "CREATE TABLE doctors",
        "CREATE TABLE doctor_schedules",
        "CREATE TABLE appointments",
        "CREATE TABLE doctor_token_counters",
        "CREATE TABLE appointment_status_history",
        "CREATE TABLE notification_logs",
    ]:
        assert table_name in schema_sql

    assert "SERIAL PRIMARY KEY" in schema_sql
    assert "active_slot_key" in schema_sql
    assert "GENERATED ALWAYS AS" in schema_sql
    assert "STORED" in schema_sql
    assert "uq_appointments_active_slot_key" in schema_sql

    seed_sql = pg_seed.read_text(encoding="utf-8")
    assert "ON CONFLICT" in seed_sql
    assert "CURRENT_DATE" in seed_sql
    assert "scrypt:" in seed_sql
    assert "setval(pg_get_serial_sequence" in seed_sql


def test_requirements_include_gunicorn_and_psycopg2_binary():
    """Verify backend/requirements.txt lists gunicorn and psycopg2-binary for Render."""
    repo_root = Path(__file__).resolve().parents[2]
    req_text = (repo_root / "backend" / "requirements.txt").read_text(encoding="utf-8")
    assert "gunicorn" in req_text
    assert "psycopg2-binary" in req_text


def test_create_app_with_custom_cors_and_health_check():
    """Verify create_app configures CORS_ORIGINS and /api/health verifies DB connectivity."""
    app = create_app(
        "testing",
        {
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "CORS_ORIGINS": ["https://smart-hospital-web.onrender.com"],
        },
    )
    client = app.test_client()
    res = client.get(
        "/api/health",
        headers={"Origin": "https://smart-hospital-web.onrender.com"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert res.headers.get("Access-Control-Allow-Origin") == "https://smart-hospital-web.onrender.com"
