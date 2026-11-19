"""Tests for Sub-Phase 2B: Notification service with SMTP mock, simulated fallback, and notifications API."""

from unittest.mock import MagicMock, patch
from datetime import timedelta
from backend.app.services.notification_service import NotificationService
from backend.app.utils.timezone import today_hospital


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_notification_service_fallback_when_smtp_unconfigured(client, seeded_data):
    """When SMTP_HOST is empty, notifications cleanly fall back to SIMULATED without throwing exceptions."""
    patient_headers = auth_headers(seeded_data["patient_token"])
    doctor_id = seeded_data["doctor_id"]
    tomorrow = (today_hospital() + timedelta(days=1)).isoformat()

    # Online booking triggers NotificationService.send_notification
    res = client.post(
        "/api/appointments",
        json={"doctor_id": doctor_id, "appointment_date": tomorrow, "slot_time": "09:00"},
        headers=patient_headers,
    )
    assert res.status_code == 201

    # Check GET /api/notifications
    res_notif = client.get("/api/notifications", headers=patient_headers)
    assert res_notif.status_code == 200
    data = res_notif.get_json()
    assert len(data["notifications"]) >= 2  # 1 EMAIL (SIMULATED) and 1 SMS (SIMULATED)
    email_entry = next((n for n in data["notifications"] if n["channel"] == "EMAIL"), None)
    sms_entry = next((n for n in data["notifications"] if n["channel"] == "SMS"), None)

    assert email_entry is not None
    assert email_entry["delivery_mode"] == "SIMULATED"
    assert "simulated delivery" in email_entry["error_message"].lower()

    assert sms_entry is not None
    assert sms_entry["delivery_mode"] == "SIMULATED"


def test_notification_service_with_smtp_mocked_success(app, seeded_data):
    """When SMTP is configured and connected, delivery_mode is SMTP_SENT."""
    with app.app_context():
        app.config["SMTP_HOST"] = "smtp.hospital.test"
        app.config["SMTP_PORT"] = 587
        app.config["SMTP_USERNAME"] = "mailer"
        app.config["SMTP_PASSWORD"] = "secret"

        mock_server = MagicMock()
        with patch("smtplib.SMTP", return_value=mock_server):
            mock_server.__enter__.return_value = mock_server
            mode, err = NotificationService._send_email_smtp(
                "patient@example.com", "Test Subject", "Test Body"
            )
            assert mode == "SMTP_SENT"
            assert err is None
            mock_server.send_message.assert_called_once()
