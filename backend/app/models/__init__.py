"""SQLAlchemy ORM models matching backend/database/schema.sql."""

from sqlalchemy import Computed, UniqueConstraint
from backend.app.extensions import db
from backend.app.utils.timezone import now_hospital_naive


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(190), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.Enum("PATIENT", "DOCTOR", "ADMIN", name="user_role_enum"),
        nullable=False,
        default="PATIENT",
    )
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=now_hospital_naive)

    patient_profile = db.relationship("Patient", back_populates="user", uselist=False)
    doctor_profile = db.relationship("Doctor", back_populates="user", uselist=False)

    def to_dict(self):
        data = {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if self.patient_profile:
            data["patient_id"] = self.patient_profile.id
        if self.doctor_profile:
            data["doctor_id"] = self.doctor_profile.id
            data["doc_code"] = self.doctor_profile.doc_code
        return data


class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        unique=True,
        nullable=True,
    )
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False, index=True)
    email = db.Column(db.String(190), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=now_hospital_naive)

    user = db.relationship("User", back_populates="patient_profile")
    appointments = db.relationship("Appointment", back_populates="patient")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "full_name": self.full_name,
            "phone": self.phone,
            "email": self.email,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "gender": self.gender,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    doctors = db.relationship("Doctor", back_populates="department")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
        }


class Doctor(db.Model):
    __tablename__ = "doctors"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        unique=True,
        nullable=False,
    )
    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
    )
    doc_code = db.Column(db.String(30), unique=True, nullable=False)
    specialization = db.Column(db.String(150), nullable=False)
    room_number = db.Column(db.String(50), nullable=False)
    default_slot_duration_minutes = db.Column(db.Integer, nullable=False, default=15)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    user = db.relationship("User", back_populates="doctor_profile")
    department = db.relationship("Department", back_populates="doctors")
    schedules = db.relationship(
        "DoctorSchedule",
        back_populates="doctor",
        cascade="all, delete-orphan",
        order_by="DoctorSchedule.day_of_week, DoctorSchedule.start_time",
    )
    appointments = db.relationship("Appointment", back_populates="doctor")

    def to_dict(self, include_schedules: bool = False):
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.user.name if self.user else None,
            "email": self.user.email if self.user else None,
            "department_id": self.department_id,
            "department_name": self.department.name if self.department else None,
            "doc_code": self.doc_code,
            "specialization": self.specialization,
            "room_number": self.room_number,
            "default_slot_duration_minutes": self.default_slot_duration_minutes,
            "is_active": bool(self.is_active),
        }
        if include_schedules:
            data["schedules"] = [s.to_dict() for s in self.schedules]
        return data


class DoctorSchedule(db.Model):
    __tablename__ = "doctor_schedules"
    __table_args__ = (
        UniqueConstraint("doctor_id", "day_of_week", "start_time", name="uq_doctor_schedule_day_start"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey("doctors.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    day_of_week = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    slot_duration_minutes = db.Column(db.Integer, nullable=False)
    max_patients = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    doctor = db.relationship("Doctor", back_populates="schedules")

    def to_dict(self):
        return {
            "id": self.id,
            "doctor_id": self.doctor_id,
            "day_of_week": self.day_of_week,
            "start_time": self.start_time.strftime("%H:%M") if self.start_time else None,
            "end_time": self.end_time.strftime("%H:%M") if self.end_time else None,
            "slot_duration_minutes": self.slot_duration_minutes,
            "max_patients": self.max_patients,
            "is_active": bool(self.is_active),
        }


class Appointment(db.Model):
    __tablename__ = "appointments"
    __table_args__ = (
        UniqueConstraint("active_slot_key", name="uq_appointments_active_slot_key"),
        UniqueConstraint("doctor_id", "appointment_date", "token_number", name="uq_appointments_doctor_date_token"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patients.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
    )
    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey("doctors.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
    )
    appointment_date = db.Column(db.Date, nullable=False)
    slot_time = db.Column(db.Time, nullable=False)
    booking_type = db.Column(
        db.Enum("ONLINE", "WALK_IN", name="booking_type_enum"),
        nullable=False,
        default="ONLINE",
    )
    status = db.Column(
        db.Enum(
            "BOOKED",
            "CONFIRMED",
            "IN_CONSULTATION",
            "COMPLETED",
            "CANCELLED",
            "NO_SHOW",
            name="appointment_status_enum",
        ),
        nullable=False,
        default="BOOKED",
    )
    token_number = db.Column(db.String(40), nullable=False)
    previous_token = db.Column(db.String(40), nullable=True)
    reason = db.Column(db.String(255), nullable=True)
    created_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
    )
    created_at = db.Column(db.DateTime, nullable=False, default=now_hospital_naive)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=now_hospital_naive,
        onupdate=now_hospital_naive,
    )
    active_slot_key = db.Column(
        db.String(64),
        Computed(
            "CASE WHEN status = 'CANCELLED' THEN NULL "
            "ELSE CONCAT(doctor_id, '|', appointment_date, '|', slot_time) END",
            persisted=True,
        ),
    )

    patient = db.relationship("Patient", back_populates="appointments")
    doctor = db.relationship("Doctor", back_populates="appointments")
    created_by_user = db.relationship("User", foreign_keys=[created_by_user_id])
    status_history = db.relationship(
        "AppointmentStatusHistory",
        back_populates="appointment",
        cascade="all, delete-orphan",
        order_by="AppointmentStatusHistory.changed_at, AppointmentStatusHistory.id",
    )

    def to_dict(self, include_history: bool = False):
        data = {
            "id": self.id,
            "patient_id": self.patient_id,
            "patient_name": self.patient.full_name if self.patient else None,
            "patient_phone": self.patient.phone if self.patient else None,
            "patient_email": self.patient.email if self.patient else None,
            "doctor_id": self.doctor_id,
            "doctor_name": self.doctor.user.name if (self.doctor and self.doctor.user) else None,
            "doc_code": self.doctor.doc_code if self.doctor else None,
            "room_number": self.doctor.room_number if self.doctor else None,
            "department_id": self.doctor.department_id if self.doctor else None,
            "department_name": (
                self.doctor.department.name if (self.doctor and self.doctor.department) else None
            ),
            "appointment_date": self.appointment_date.isoformat() if self.appointment_date else None,
            "slot_time": self.slot_time.strftime("%H:%M") if self.slot_time else None,
            "booking_type": self.booking_type,
            "status": self.status,
            "token_number": self.token_number,
            "previous_token": self.previous_token,
            "reason": self.reason,
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_history:
            data["status_history"] = [h.to_dict() for h in self.status_history]
        return data


class DoctorTokenCounter(db.Model):
    __tablename__ = "doctor_token_counters"

    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey("doctors.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    token_date = db.Column(db.Date, primary_key=True)
    last_seq = db.Column(db.Integer, nullable=False, default=0)


class AppointmentStatusHistory(db.Model):
    __tablename__ = "appointment_status_history"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    appointment_id = db.Column(
        db.Integer,
        db.ForeignKey("appointments.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    old_status = db.Column(db.String(30), nullable=True)
    new_status = db.Column(db.String(30), nullable=False)
    changed_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
    )
    changed_at = db.Column(db.DateTime, nullable=False, default=now_hospital_naive)
    note = db.Column(db.String(255), nullable=True)

    appointment = db.relationship("Appointment", back_populates="status_history")
    changed_by_user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "appointment_id": self.appointment_id,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "changed_by_user_id": self.changed_by_user_id,
            "changed_by_name": self.changed_by_user.name if self.changed_by_user else None,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
            "note": self.note,
        }


class NotificationLog(db.Model):
    __tablename__ = "notification_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patients.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    appointment_id = db.Column(
        db.Integer,
        db.ForeignKey("appointments.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    channel = db.Column(db.Enum("EMAIL", "SMS", name="notification_channel_enum"), nullable=False)
    event_type = db.Column(db.String(60), nullable=False)
    recipient = db.Column(db.String(190), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    delivery_mode = db.Column(
        db.Enum("SMTP_SENT", "SIMULATED", name="delivery_mode_enum"),
        nullable=False,
        default="SIMULATED",
    )
    status = db.Column(db.String(30), nullable=False, default="SENT")
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=now_hospital_naive)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "patient_id": self.patient_id,
            "appointment_id": self.appointment_id,
            "channel": self.channel,
            "event_type": self.event_type,
            "recipient": self.recipient,
            "subject": self.subject,
            "message": self.message,
            "delivery_mode": self.delivery_mode,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
