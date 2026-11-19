-- =============================================================================
-- Project 25: Smart Hospital Appointment and Patient Queue Management System
-- Database Schema (MySQL 8.0+)
-- Engine: InnoDB | Charset: utf8mb4
-- =============================================================================

CREATE DATABASE IF NOT EXISTS hospital_queue_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE hospital_queue_db;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS notification_logs;
DROP TABLE IF EXISTS appointment_status_history;
DROP TABLE IF EXISTS doctor_token_counters;
DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS doctor_schedules;
DROP TABLE IF EXISTS doctors;
DROP TABLE IF EXISTS departments;
DROP TABLE IF EXISTS patients;
DROP TABLE IF EXISTS users;

SET FOREIGN_KEY_CHECKS = 1;

-- 1. users
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(190) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('PATIENT', 'DOCTOR', 'ADMIN') NOT NULL DEFAULT 'PATIENT',
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_users_email (email),
    KEY idx_users_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. patients
CREATE TABLE patients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    full_name VARCHAR(120) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    email VARCHAR(190) NULL,
    date_of_birth DATE NULL,
    gender VARCHAR(20) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_patients_user_id (user_id),
    KEY idx_patients_phone (phone),
    KEY idx_patients_full_name (full_name),
    CONSTRAINT fk_patients_user FOREIGN KEY (user_id)
        REFERENCES users (id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. departments
CREATE TABLE departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    description TEXT NULL,
    UNIQUE KEY uq_departments_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. doctors
CREATE TABLE doctors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    department_id INT NOT NULL,
    doc_code VARCHAR(30) NOT NULL,
    specialization VARCHAR(150) NOT NULL,
    room_number VARCHAR(50) NOT NULL,
    default_slot_duration_minutes INT NOT NULL DEFAULT 15,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    UNIQUE KEY uq_doctors_user_id (user_id),
    UNIQUE KEY uq_doctors_doc_code (doc_code),
    KEY idx_doctors_department_id (department_id),
    CONSTRAINT fk_doctors_user FOREIGN KEY (user_id)
        REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_doctors_department FOREIGN KEY (department_id)
        REFERENCES departments (id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. doctor_schedules
-- day_of_week: 0 = Monday ... 6 = Sunday (same as Python date.weekday())
CREATE TABLE doctor_schedules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    doctor_id INT NOT NULL,
    day_of_week TINYINT NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    slot_duration_minutes INT NOT NULL,
    max_patients INT NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    UNIQUE KEY uq_doctor_schedule_day_start (doctor_id, day_of_week, start_time),
    KEY idx_doctor_schedules_doctor_day (doctor_id, day_of_week),
    CONSTRAINT fk_doctor_schedules_doctor FOREIGN KEY (doctor_id)
        REFERENCES doctors (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_day_of_week CHECK (day_of_week BETWEEN 0 AND 6),
    CONSTRAINT chk_slot_duration CHECK (slot_duration_minutes > 0),
    CONSTRAINT chk_max_patients CHECK (max_patients > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. appointments
-- Duplicate-slot constraint via STORED generated column active_slot_key:
-- NULL when status = 'CANCELLED', else CONCAT(doctor_id, '|', appointment_date, '|', slot_time)
CREATE TABLE appointments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    appointment_date DATE NOT NULL,
    slot_time TIME NOT NULL,
    booking_type ENUM('ONLINE', 'WALK_IN') NOT NULL DEFAULT 'ONLINE',
    status ENUM('BOOKED', 'CONFIRMED', 'IN_CONSULTATION', 'COMPLETED', 'CANCELLED', 'NO_SHOW') NOT NULL DEFAULT 'BOOKED',
    token_number VARCHAR(40) NOT NULL,
    previous_token VARCHAR(40) NULL,
    reason VARCHAR(255) NULL,
    created_by_user_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    active_slot_key VARCHAR(64) GENERATED ALWAYS AS (
        CASE
            WHEN status = 'CANCELLED' THEN NULL
            ELSE CONCAT(doctor_id, '|', appointment_date, '|', slot_time)
        END
    ) STORED,
    UNIQUE KEY uq_appointments_active_slot_key (active_slot_key),
    UNIQUE KEY uq_appointments_doctor_date_token (doctor_id, appointment_date, token_number),
    KEY idx_appointments_doctor_date_slot (doctor_id, appointment_date, slot_time),
    KEY idx_appointments_patient_date (patient_id, appointment_date),
    KEY idx_appointments_date_status (appointment_date, status),
    CONSTRAINT fk_appointments_patient FOREIGN KEY (patient_id)
        REFERENCES patients (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_appointments_doctor FOREIGN KEY (doctor_id)
        REFERENCES doctors (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_appointments_created_by FOREIGN KEY (created_by_user_id)
        REFERENCES users (id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. doctor_token_counters
CREATE TABLE doctor_token_counters (
    doctor_id INT NOT NULL,
    token_date DATE NOT NULL,
    last_seq INT NOT NULL DEFAULT 0,
    PRIMARY KEY (doctor_id, token_date),
    CONSTRAINT fk_token_counters_doctor FOREIGN KEY (doctor_id)
        REFERENCES doctors (id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. appointment_status_history
CREATE TABLE appointment_status_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    appointment_id INT NOT NULL,
    old_status VARCHAR(30) NULL,
    new_status VARCHAR(30) NOT NULL,
    changed_by_user_id INT NOT NULL,
    changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    note VARCHAR(255) NULL,
    KEY idx_status_history_appointment (appointment_id),
    CONSTRAINT fk_status_history_appointment FOREIGN KEY (appointment_id)
        REFERENCES appointments (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_status_history_user FOREIGN KEY (changed_by_user_id)
        REFERENCES users (id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. notification_logs
CREATE TABLE notification_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    patient_id INT NULL,
    appointment_id INT NULL,
    channel ENUM('EMAIL', 'SMS') NOT NULL,
    event_type VARCHAR(60) NOT NULL,
    recipient VARCHAR(190) NOT NULL,
    subject VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    delivery_mode ENUM('SMTP_SENT', 'SIMULATED') NOT NULL DEFAULT 'SIMULATED',
    status VARCHAR(30) NOT NULL DEFAULT 'SENT',
    error_message TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_notification_logs_user (user_id),
    KEY idx_notification_logs_patient (patient_id),
    KEY idx_notification_logs_appointment (appointment_id),
    KEY idx_notification_logs_created_at (created_at),
    CONSTRAINT fk_notification_logs_user FOREIGN KEY (user_id)
        REFERENCES users (id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_notification_logs_patient FOREIGN KEY (patient_id)
        REFERENCES patients (id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_notification_logs_appointment FOREIGN KEY (appointment_id)
        REFERENCES appointments (id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
