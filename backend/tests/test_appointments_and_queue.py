"""Consolidated End-to-End Tests for Appointments, Queue, Rescheduling, Status Lifecycle, and Reporting."""

from datetime import timedelta
from backend.app.utils.timezone import today_hospital


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_full_patient_and_staff_workflow(client, seeded_data):
    """
    End-to-end integration test:
    1. Patient books online appointment -> DOC1-001 (BOOKED)
    2. Admin registers walk-in patient -> DOC1-002 (CONFIRMED)
    3. Admin confirms online patient -> CONFIRMED
    4. Doctor checks queue -> 2 waiting
    5. Doctor calls DOC1-001 -> IN_CONSULTATION
    6. Doctor completes DOC1-001 -> COMPLETED
    7. Admin views daily report -> 2 appointments, 1 completed, 1 confirmed
    8. Admin exports CSV -> contains both appointments
    """
    patient_headers = auth_headers(seeded_data["patient_token"])
    doctor_headers = auth_headers(seeded_data["doctor_token"])
    admin_headers = auth_headers(seeded_data["admin_token"])
    doctor_id = seeded_data["doctor_id"]
    tomorrow = (today_hospital() + timedelta(days=1)).isoformat()

    # Step 1: Patient books online
    r1 = client.post(
        "/api/appointments",
        json={"doctor_id": doctor_id, "appointment_date": tomorrow, "slot_time": "09:00", "reason": "Heart palpitations"},
        headers=patient_headers,
    )
    assert r1.status_code == 201
    appt1_id = r1.get_json()["appointment"]["id"]
    assert r1.get_json()["appointment"]["token_number"] == "DOC1-001"

    # Step 2: Admin books walk-in
    r2 = client.post(
        "/api/appointments/walk-in",
        json={"doctor_id": doctor_id, "appointment_date": tomorrow, "patient_name": "Sita Ram", "patient_phone": "9812345678", "slot_time": "09:30"},
        headers=admin_headers,
    )
    assert r2.status_code == 201
    appt2_id = r2.get_json()["appointment"]["id"]
    assert r2.get_json()["appointment"]["token_number"] == "DOC1-002"

    # Step 3: Admin confirms online appointment
    rc = client.patch(
        f"/api/appointments/{appt1_id}/status",
        json={"status": "CONFIRMED"},
        headers=admin_headers,
    )
    assert rc.status_code == 200

    # Step 4: Doctor checks queue
    rq = client.get(f"/api/queue?date={tomorrow}&doctor_id={doctor_id}")
    assert rq.status_code == 200
    assert len(rq.get_json()["next_waiting"]) == 2

    # Step 5: Doctor calls token DOC1-001
    r_call = client.patch(
        f"/api/appointments/{appt1_id}/status",
        json={"status": "IN_CONSULTATION"},
        headers=doctor_headers,
    )
    assert r_call.status_code == 200
    assert r_call.get_json()["appointment"]["status"] == "IN_CONSULTATION"

    # Step 6: Doctor marks completed
    r_done = client.patch(
        f"/api/appointments/{appt1_id}/status",
        json={"status": "COMPLETED"},
        headers=doctor_headers,
    )
    assert r_done.status_code == 200

    # Step 7: Admin views daily report
    r_rep = client.get(f"/api/reports/daily?date={tomorrow}", headers=admin_headers)
    assert r_rep.status_code == 200
    rep_data = r_rep.get_json()
    assert rep_data["total_appointments"] == 2
    assert rep_data["status_breakdown"]["COMPLETED"] == 1
    assert rep_data["status_breakdown"]["CONFIRMED"] == 1

    # Step 8: Admin exports CSV
    r_csv = client.get(f"/api/reports/daily/export?date={tomorrow}", headers=admin_headers)
    assert r_csv.status_code == 200
    csv_text = r_csv.data.decode("utf-8")
    assert "DOC1-001" in csv_text
    assert "DOC1-002" in csv_text
