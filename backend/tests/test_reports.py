"""Tests for Sub-Phase 2C: Daily reports API, CSV export, and RBAC restrictions."""

from datetime import timedelta
from backend.app.utils.timezone import today_hospital


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_reports_api_rbac_and_summary_breakdown(client, seeded_data):
    """GET /api/reports/daily is ADMIN-only and returns counts per status, doctor, and type."""
    admin_headers = auth_headers(seeded_data["admin_token"])
    patient_headers = auth_headers(seeded_data["patient_token"])
    doctor_id = seeded_data["doctor_id"]
    tomorrow = (today_hospital() + timedelta(days=1)).isoformat()

    # Patient is forbidden from viewing reports
    res_pat = client.get(f"/api/reports/daily?date={tomorrow}", headers=patient_headers)
    assert res_pat.status_code == 403

    # Book 1 online appointment and 1 walk-in appointment for tomorrow
    client.post(
        "/api/appointments",
        json={"doctor_id": doctor_id, "appointment_date": tomorrow, "slot_time": "09:00"},
        headers=patient_headers,
    )
    client.post(
        "/api/appointments/walk-in",
        json={
            "doctor_id": doctor_id,
            "appointment_date": tomorrow,
            "patient_name": "Report Walkin",
            "patient_phone": "9990001112",
        },
        headers=admin_headers,
    )

    # Admin requests daily report
    res_rep = client.get(f"/api/reports/daily?date={tomorrow}", headers=admin_headers)
    assert res_rep.status_code == 200
    report = res_rep.get_json()
    assert report["total_appointments"] == 2
    assert report["booking_type_breakdown"]["ONLINE"] == 1
    assert report["booking_type_breakdown"]["WALK_IN"] == 1
    assert "DOC1" in report["doctor_distribution"]


def test_reports_csv_export(client, seeded_data):
    """GET /api/reports/daily/export returns CSV file attachment with correct headers."""
    admin_headers = auth_headers(seeded_data["admin_token"])
    tomorrow = (today_hospital() + timedelta(days=1)).isoformat()

    res_csv = client.get(f"/api/reports/daily/export?date={tomorrow}", headers=admin_headers)
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.content_type
    assert "attachment;" in res_csv.headers.get("Content-Disposition", "")
    content = res_csv.data.decode("utf-8")
    assert "Appointment ID,Token Number,Patient Name,Doctor Name,Department,Slot Time,Booking Type,Status,Reason" in content
