"""Tests for Sub-Phase 1C: Online & walk-in booking, sequential token generation, 409 conflicts, status lifecycle, history, and queue."""

from datetime import timedelta
from backend.app.utils.timezone import today_hospital


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_online_booking_sequential_tokens_and_duplicate_slot_409(client, seeded_data):
    """Online booking issues DOC1-001, DOC1-002; duplicate slot returns 409; daily capacity cap returns 409."""
    patient_headers = auth_headers(seeded_data["patient_token"])
    admin_headers = auth_headers(seeded_data["admin_token"])
    doctor_id = seeded_data["doctor_id"]
    tomorrow = (today_hospital() + timedelta(days=1)).isoformat()

    # 1. Book slot 09:00 -> DOC1-001 (status BOOKED)
    res1 = client.post(
        "/api/appointments",
        json={
            "doctor_id": doctor_id,
            "appointment_date": tomorrow,
            "slot_time": "09:00",
            "reason": "Chest pain check",
        },
        headers=patient_headers,
    )
    assert res1.status_code == 201
    appt1 = res1.get_json()["appointment"]
    assert appt1["token_number"] == "DOC1-001"
    assert appt1["status"] == "BOOKED"
    assert appt1["booking_type"] == "ONLINE"
    assert len(appt1["status_history"]) == 1
    assert appt1["status_history"][0]["new_status"] == "BOOKED"

    # 2. Attempting to book the same slot 09:00 returns 409 SLOT_ALREADY_BOOKED
    res_dup = client.post(
        "/api/appointments",
        json={
            "doctor_id": doctor_id,
            "appointment_date": tomorrow,
            "slot_time": "09:00",
            "reason": "Duplicate attempt",
        },
        headers=patient_headers,
    )
    assert res_dup.status_code == 409
    assert res_dup.get_json()["error"]["code"] == "SLOT_ALREADY_BOOKED"

    # 3. Book slot 09:30 -> DOC1-002
    res2 = client.post(
        "/api/appointments",
        json={
            "doctor_id": doctor_id,
            "appointment_date": tomorrow,
            "slot_time": "09:30",
        },
        headers=patient_headers,
    )
    assert res2.status_code == 201
    assert res2.get_json()["appointment"]["token_number"] == "DOC1-002"

    # 4. Walk-in booking by Admin without specifying slot_time auto-assigns next free slot (10:00) -> DOC1-003, CONFIRMED
    res3 = client.post(
        "/api/appointments/walk-in",
        json={
            "doctor_id": doctor_id,
            "appointment_date": tomorrow,
            "patient_name": "Walkin Patient One",
            "patient_phone": "9111222333",
            "reason": "Walk-in consultation",
        },
        headers=admin_headers,
    )
    assert res3.status_code == 201
    appt3 = res3.get_json()["appointment"]
    assert appt3["token_number"] == "DOC1-003"
    assert appt3["status"] == "CONFIRMED"
    assert appt3["booking_type"] == "WALK_IN"
    assert appt3["slot_time"] == "10:00"

    # 5. Seeded schedule has 4 slots (09:00, 09:30, 10:00, 10:30) but max_patients = 3!
    # So booking the 4th slot (10:30) must fail with 409 DAILY_CAPACITY_REACHED
    res_cap = client.post(
        "/api/appointments",
        json={
            "doctor_id": doctor_id,
            "appointment_date": tomorrow,
            "slot_time": "10:30",
        },
        headers=patient_headers,
    )
    assert res_cap.status_code == 409
    assert res_cap.get_json()["error"]["code"] == "DAILY_CAPACITY_REACHED"


def test_cancelled_token_never_reused_and_cancelled_slot_can_be_rebooked(client, seeded_data):
    """Cancelling frees the slot for rebooking, and the new booking gets the next sequential token."""
    patient_headers = auth_headers(seeded_data["patient_token"])
    doctor_id = seeded_data["doctor_id"]
    tomorrow = (today_hospital() + timedelta(days=1)).isoformat()

    # Book 09:00 -> DOC1-001
    res1 = client.post(
        "/api/appointments",
        json={"doctor_id": doctor_id, "appointment_date": tomorrow, "slot_time": "09:00"},
        headers=patient_headers,
    )
    assert res1.status_code == 201
    appt1_id = res1.get_json()["appointment"]["id"]
    assert res1.get_json()["appointment"]["token_number"] == "DOC1-001"

    # Cancel DOC1-001 via PATCH /status
    res_cancel = client.patch(
        f"/api/appointments/{appt1_id}/status",
        json={"status": "CANCELLED", "note": "Patient cancelled"},
        headers=patient_headers,
    )
    assert res_cancel.status_code == 200
    assert res_cancel.get_json()["appointment"]["status"] == "CANCELLED"

    # Rebook the exact same slot 09:00 -> succeeds and issues DOC1-002 (never reuses DOC1-001)
    res2 = client.post(
        "/api/appointments",
        json={"doctor_id": doctor_id, "appointment_date": tomorrow, "slot_time": "09:00"},
        headers=patient_headers,
    )
    assert res2.status_code == 201
    assert res2.get_json()["appointment"]["token_number"] == "DOC1-002"


def test_booking_date_and_slot_validation_errors(client, seeded_data):
    """Past dates, >30 days ahead, and invalid schedule slots return 400."""
    patient_headers = auth_headers(seeded_data["patient_token"])
    doctor_id = seeded_data["doctor_id"]
    today = today_hospital()

    # Past date -> 400 PAST_DATE
    yesterday = (today - timedelta(days=1)).isoformat()
    res_past = client.post(
        "/api/appointments",
        json={"doctor_id": doctor_id, "appointment_date": yesterday, "slot_time": "09:00"},
        headers=patient_headers,
    )
    assert res_past.status_code == 400
    assert res_past.get_json()["error"]["code"] == "PAST_DATE"

    # > 30 days ahead -> 400 DATE_TOO_FAR
    too_far = (today + timedelta(days=31)).isoformat()
    res_far = client.post(
        "/api/appointments",
        json={"doctor_id": doctor_id, "appointment_date": too_far, "slot_time": "09:00"},
        headers=patient_headers,
    )
    assert res_far.status_code == 400
    assert res_far.get_json()["error"]["code"] == "DATE_TOO_FAR"

    # Off-grid slot 09:10 (when schedule is 30-min intervals 09:00, 09:30...) -> 400 INVALID_SLOT
    tomorrow = (today + timedelta(days=1)).isoformat()
    res_bad_slot = client.post(
        "/api/appointments",
        json={"doctor_id": doctor_id, "appointment_date": tomorrow, "slot_time": "09:10"},
        headers=patient_headers,
    )
    assert res_bad_slot.status_code == 400
    assert res_bad_slot.get_json()["error"]["code"] == "INVALID_SLOT"


def test_status_state_machine_and_queue_endpoint(client, seeded_data):
    """Verify full status lifecycle, single IN_CONSULTATION constraint, NO_SHOW date rule, and queue endpoint."""
    patient_headers = auth_headers(seeded_data["patient_token"])
    doctor_headers = auth_headers(seeded_data["doctor_token"])
    admin_headers = auth_headers(seeded_data["admin_token"])
    doctor_id = seeded_data["doctor_id"]
    tomorrow = (today_hospital() + timedelta(days=1)).isoformat()

    # Book online appointment 1 (09:00 -> BOOKED)
    res1 = client.post(
        "/api/appointments",
        json={"doctor_id": doctor_id, "appointment_date": tomorrow, "slot_time": "09:00"},
        headers=patient_headers,
    )
    appt1_id = res1.get_json()["appointment"]["id"]

    # Book walk-in appointment 2 (09:30 -> CONFIRMED)
    res2 = client.post(
        "/api/appointments/walk-in",
        json={
            "doctor_id": doctor_id,
            "appointment_date": tomorrow,
            "slot_time": "09:30",
            "patient_name": "Second Patient",
            "patient_phone": "9000111222",
        },
        headers=admin_headers,
    )
    appt2_id = res2.get_json()["appointment"]["id"]

    # Doctor cannot confirm a BOOKED appointment (only Admin can: BOOKED -> CONFIRMED)
    res_doc_confirm = client.patch(
        f"/api/appointments/{appt1_id}/status",
        json={"status": "CONFIRMED"},
        headers=doctor_headers,
    )
    assert res_doc_confirm.status_code == 403

    # Admin confirms appt1 (BOOKED -> CONFIRMED)
    res_adm_confirm = client.patch(
        f"/api/appointments/{appt1_id}/status",
        json={"status": "CONFIRMED", "note": "Patient arrived at reception"},
        headers=admin_headers,
    )
    assert res_adm_confirm.status_code == 200
    assert res_adm_confirm.get_json()["appointment"]["status"] == "CONFIRMED"

    # NO_SHOW before appointment_date is rejected (400 NO_SHOW_TOO_EARLY)
    res_early_noshow = client.patch(
        f"/api/appointments/{appt1_id}/status",
        json={"status": "NO_SHOW"},
        headers=doctor_headers,
    )
    assert res_early_noshow.status_code == 400
    assert res_early_noshow.get_json()["error"]["code"] == "NO_SHOW_TOO_EARLY"

    # Doctor starts consultation on appt1 (CONFIRMED -> IN_CONSULTATION)
    res_consult1 = client.patch(
        f"/api/appointments/{appt1_id}/status",
        json={"status": "IN_CONSULTATION"},
        headers=doctor_headers,
    )
    assert res_consult1.status_code == 200
    assert res_consult1.get_json()["appointment"]["status"] == "IN_CONSULTATION"

    # Attempting to put appt2 into IN_CONSULTATION while appt1 is still IN_CONSULTATION fails (400 DOCTOR_BUSY)
    res_busy = client.patch(
        f"/api/appointments/{appt2_id}/status",
        json={"status": "IN_CONSULTATION"},
        headers=doctor_headers,
    )
    assert res_busy.status_code == 400
    assert res_busy.get_json()["error"]["code"] == "DOCTOR_BUSY"

    # Check GET /api/queue for tomorrow
    res_queue = client.get(f"/api/queue?date={tomorrow}&doctor_id={doctor_id}")
    assert res_queue.status_code == 200
    q_data = res_queue.get_json()
    assert q_data["current_in_consultation"]["id"] == appt1_id
    assert q_data["current_in_consultation"]["token_number"] == "DOC1-001"
    assert len(q_data["next_waiting"]) == 1
    assert q_data["next_waiting"][0]["id"] == appt2_id
    assert q_data["next_waiting"][0]["token_number"] == "DOC1-002"

    # Doctor completes appt1 (IN_CONSULTATION -> COMPLETED)
    res_complete1 = client.patch(
        f"/api/appointments/{appt1_id}/status",
        json={"status": "COMPLETED", "note": "Prescription issued"},
        headers=doctor_headers,
    )
    assert res_complete1.status_code == 200
    completed_appt = res_complete1.get_json()["appointment"]
    assert completed_appt["status"] == "COMPLETED"
    # History should have 4 entries: None->BOOKED, BOOKED->CONFIRMED, CONFIRMED->IN_CONSULTATION, IN_CONSULTATION->COMPLETED
    assert len(completed_appt["status_history"]) == 4

    # Terminal state cannot transition further
    res_terminal = client.patch(
        f"/api/appointments/{appt1_id}/status",
        json={"status": "CANCELLED"},
        headers=admin_headers,
    )
    assert res_terminal.status_code == 400
    assert res_terminal.get_json()["error"]["code"] == "INVALID_TRANSITION"
