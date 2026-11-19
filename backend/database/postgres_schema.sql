-- =============================================================================
-- Project 25: Smart Hospital Appointment and Patient Queue Management System
-- Database Schema for Render PostgreSQL (PostgreSQL 14+)
-- =============================================================================

BEGIN;

DROP TABLE IF EXISTS notification_logs CASCADE;
DROP TABLE IF EXISTS appointment_status_history CASCADE;
DROP TABLE IF EXISTS doctor_token_counters CASCADE;
DROP TABLE IF EXISTS appointments CASCADE;
DROP TABLE IF EXISTS doctor_schedules CASCADE;
DROP TABLE IF EXISTS doctors CASCADE;
DROP TABLE IF EXISTS departments CASCADE;
DROP TABLE IF EXISTS patients CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 1. users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(190) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'PATIENT'
        CONSTRAINT chk_users_role CHECK (role IN ('PATIENT', 'DOCTOR', 'ADMIN')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_users_email UNIQUE (email)
);
CREATE INDEX idx_users_role ON users (role);

-- 2. patients
CREATE TABLE patients (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NULL,
    full_name VARCHAR(120) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    email VARCHAR(190) NULL,
    date_of_birth DATE NULL,
    gender VARCHAR(20) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_patients_user_id UNIQUE (user_id),
    CONSTRAINT fk_patients_user FOREIGN KEY (user_id)
        REFERENCES users (id) ON DELETE SET NULL ON UPDATE CASCADE
);
CREATE INDEX idx_patients_phone ON patients (phone);
CREATE INDEX idx_patients_full_name ON patients (full_name);

-- 3. departments
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    description TEXT NULL,
    CONSTRAINT uq_departments_name UNIQUE (name)
);

-- 4. doctors
CREATE TABLE doctors (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    department_id INTEGER NOT NULL,
    doc_code VARCHAR(30) NOT NULL,
    specialization VARCHAR(150) NOT NULL,
    room_number VARCHAR(50) NOT NULL,
    default_slot_duration_minutes INTEGER NOT NULL DEFAULT 15,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_doctors_user_id UNIQUE (user_id),
    CONSTRAINT uq_doctors_doc_code UNIQUE (doc_code),
    CONSTRAINT fk_doctors_user FOREIGN KEY (user_id)
        REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_doctors_department FOREIGN KEY (department_id)
        REFERENCES departments (id) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_doctors_department_id ON doctors (department_id);

-- 5. doctor_schedules
-- day_of_week: 0 = Monday ... 6 = Sunday (same as Python date.weekday())
CREATE TABLE doctor_schedules (
    id SERIAL PRIMARY KEY,
    doctor_id INTEGER NOT NULL,
    day_of_week SMALLINT NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    slot_duration_minutes INTEGER NOT NULL,
    max_patients INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_doctor_schedule_day_start UNIQUE (doctor_id, day_of_week, start_time),
    CONSTRAINT fk_doctor_schedules_doctor FOREIGN KEY (doctor_id)
        REFERENCES doctors (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_day_of_week CHECK (day_of_week BETWEEN 0 AND 6),
    CONSTRAINT chk_slot_duration CHECK (slot_duration_minutes > 0),
    CONSTRAINT chk_max_patients CHECK (max_patients > 0)
);
CREATE INDEX idx_doctor_schedules_doctor_day ON doctor_schedules (doctor_id, day_of_week);

-- 6. appointments
-- Duplicate-slot constraint via STORED generated column active_slot_key:
-- NULL when status = 'CANCELLED', else doctor_id || '|' || appointment_date || '|' || slot_time
CREATE TABLE appointments (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    doctor_id INTEGER NOT NULL,
    appointment_date DATE NOT NULL,
    slot_time TIME NOT NULL,
    booking_type VARCHAR(20) NOT NULL DEFAULT 'ONLINE'
        CONSTRAINT chk_appointments_booking_type CHECK (booking_type IN ('ONLINE', 'WALK_IN')),
    status VARCHAR(30) NOT NULL DEFAULT 'BOOKED'
        CONSTRAINT chk_appointments_status CHECK (
            status IN ('BOOKED', 'CONFIRMED', 'IN_CONSULTATION', 'COMPLETED', 'CANCELLED', 'NO_SHOW')
        ),
    token_number VARCHAR(40) NOT NULL,
    previous_token VARCHAR(40) NULL,
    reason VARCHAR(255) NULL,
    created_by_user_id INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_appointments_active_slot_key UNIQUE (active_slot_key),
    CONSTRAINT uq_appointments_doctor_date_token UNIQUE (doctor_id, appointment_date, token_number),
    CONSTRAINT fk_appointments_patient FOREIGN KEY (patient_id)
        REFERENCES patients (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_appointments_doctor FOREIGN KEY (doctor_id)
        REFERENCES doctors (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_appointments_created_by FOREIGN KEY (created_by_user_id)
        REFERENCES users (id) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE UNIQUE INDEX uq_appointments_active_slot
ON appointments (doctor_id, appointment_date, slot_start_time)
WHERE status <> 'CANCELLED';
CREATE INDEX idx_appointments_doctor_date_slot ON appointments (doctor_id, appointment_date, slot_time);
CREATE INDEX idx_appointments_patient_date ON appointments (patient_id, appointment_date);
CREATE INDEX idx_appointments_date_status ON appointments (appointment_date, status);

-- 7. doctor_token_counters
CREATE TABLE doctor_token_counters (
    doctor_id INTEGER NOT NULL,
    token_date DATE NOT NULL,
    last_seq INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (doctor_id, token_date),
    CONSTRAINT fk_token_counters_doctor FOREIGN KEY (doctor_id)
        REFERENCES doctors (id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- 8. appointment_status_history
CREATE TABLE appointment_status_history (
    id SERIAL PRIMARY KEY,
    appointment_id INTEGER NOT NULL,
    old_status VARCHAR(30) NULL,
    new_status VARCHAR(30) NOT NULL,
    changed_by_user_id INTEGER NOT NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    note VARCHAR(255) NULL,
    CONSTRAINT fk_status_history_appointment FOREIGN KEY (appointment_id)
        REFERENCES appointments (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_status_history_user FOREIGN KEY (changed_by_user_id)
        REFERENCES users (id) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_status_history_appointment ON appointment_status_history (appointment_id);

-- 9. notification_logs
CREATE TABLE notification_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NULL,
    patient_id INTEGER NULL,
    appointment_id INTEGER NULL,
    channel VARCHAR(20) NOT NULL
        CONSTRAINT chk_notification_channel CHECK (channel IN ('EMAIL', 'SMS')),
    event_type VARCHAR(60) NOT NULL,
    recipient VARCHAR(190) NOT NULL,
    subject VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    delivery_mode VARCHAR(30) NOT NULL DEFAULT 'SIMULATED'
        CONSTRAINT chk_notification_delivery_mode CHECK (delivery_mode IN ('SMTP_SENT', 'SIMULATED')),
    status VARCHAR(30) NOT NULL DEFAULT 'SENT',
    error_message TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notification_logs_user FOREIGN KEY (user_id)
        REFERENCES users (id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_notification_logs_patient FOREIGN KEY (patient_id)
        REFERENCES patients (id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_notification_logs_appointment FOREIGN KEY (appointment_id)
        REFERENCES appointments (id) ON DELETE SET NULL ON UPDATE CASCADE
);
CREATE INDEX idx_notification_logs_user ON notification_logs (user_id);
CREATE INDEX idx_notification_logs_patient ON notification_logs (patient_id);
CREATE INDEX idx_notification_logs_appointment ON notification_logs (appointment_id);
CREATE INDEX idx_notification_logs_created_at ON notification_logs (created_at);

COMMIT;
