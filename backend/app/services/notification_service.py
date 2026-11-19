"""Notification service handling email (SMTP with 10s timeout / simulated fallback) and simulated SMS."""

import smtplib
from email.message import EmailMessage
from flask import current_app
from backend.app.extensions import db
from backend.app.models import Appointment, NotificationLog, Patient, User
from backend.app.utils.timezone import now_hospital_naive


class NotificationService:
    @staticmethod
    def _send_email_smtp(to_email: str, subject: str, message_body: str) -> tuple[str, str | None]:
        """
        Attempt to send email via standard smtplib with a strict 10s connection timeout.
        Returns (delivery_mode, error_message).
        """
        cfg = current_app.config
        smtp_host = cfg.get("SMTP_HOST", "").strip()
        smtp_port = int(cfg.get("SMTP_PORT", 587))
        smtp_user = cfg.get("SMTP_USERNAME", "").strip()
        smtp_pass = cfg.get("SMTP_PASSWORD", "")
        use_tls = cfg.get("SMTP_USE_TLS", True)
        from_email = cfg.get("SMTP_FROM", "noreply@hospital.test")
        timeout = int(cfg.get("SMTP_TIMEOUT_SECONDS", 10))

        if not smtp_host:
            return "SIMULATED", "SMTP_HOST not configured; simulated delivery"

        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = from_email
            msg["To"] = to_email
            msg.set_content(message_body)

            with smtplib.SMTP(smtp_host, smtp_port, timeout=timeout) as server:
                if use_tls:
                    server.starttls()
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.send_message(msg)

            return "SMTP_SENT", None
        except Exception as exc:
            current_app.logger.warning("SMTP delivery failed; falling back to SIMULATED: %s", exc)
            return "SIMULATED", str(exc)

    @classmethod
    def send_notification(
        cls,
        event_type: str,
        subject: str,
        message: str,
        appointment: Appointment | None = None,
        patient: Patient | None = None,
        user: User | None = None,
    ) -> list[NotificationLog]:
        """
        Send notification through EMAIL and simulated SMS channels.
        Logs every notification in notification_logs.
        Never crashes or raises an exception that would abort the caller.
        """
        logs = []
        patient_obj = patient or (appointment.patient if appointment else None)
        user_obj = user or (patient_obj.user if patient_obj and patient_obj.user else None)
        recipient_email = (
            (user_obj.email if user_obj else None)
            or (patient_obj.email if patient_obj else None)
        )
        recipient_phone = patient_obj.phone if patient_obj else None

        # 1. Email Channel
        if recipient_email:
            mode, err = cls._send_email_smtp(recipient_email, subject, message)
            email_log = NotificationLog(
                user_id=user_obj.id if user_obj else None,
                patient_id=patient_obj.id if patient_obj else None,
                appointment_id=appointment.id if appointment else None,
                channel="EMAIL",
                event_type=event_type,
                recipient=recipient_email,
                subject=subject,
                message=message,
                delivery_mode=mode,
                status="SENT",
                error_message=err,
                created_at=now_hospital_naive(),
            )
            db.session.add(email_log)
            logs.append(email_log)

        # 2. Simulated SMS Channel
        if recipient_phone:
            sms_log = NotificationLog(
                user_id=user_obj.id if user_obj else None,
                patient_id=patient_obj.id if patient_obj else None,
                appointment_id=appointment.id if appointment else None,
                channel="SMS",
                event_type=event_type,
                recipient=recipient_phone,
                subject=f"SMS: {subject}",
                message=f"[Smart Hospital SMS] {message}",
                delivery_mode="SIMULATED",
                status="SENT",
                error_message=None,
                created_at=now_hospital_naive(),
            )
            db.session.add(sms_log)
            logs.append(sms_log)

        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            current_app.logger.error("Failed to commit notification logs: %s", exc)

        return logs
