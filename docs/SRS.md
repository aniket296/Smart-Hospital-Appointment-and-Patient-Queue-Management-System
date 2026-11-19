# Software Requirements Specification (SRS)

## Project 25: Smart Hospital Appointment and Patient Queue Management System (Simple Variant)

**Version:** 1.0 (Sub-Phase 1A Baseline)

---

## 1. Introduction

### 1.1 Purpose
The Smart Hospital Appointment and Patient Queue Management System streamlines outpatient clinic operations by enabling online appointment booking for patients, walk-in registration for reception/admin staff, sequential daily token generation per doctor, deterministic queue tracking across a strict status state machine, email/SMS notifications, and daily operational analytics with CSV exports.

### 1.2 Scope
- **No AI/ML:** All slot calculation, token allocation, queue ordering, notification triggers, and reporting logic are 100% deterministic.
- **Single Hospital Timezone:** Controlled via `HOSPITAL_TIMEZONE` in `.env` (default `Asia/Kolkata`). All date/time validations and daily boundaries use this timezone.

---

## 2. User Roles and Access Control (RBAC)

| Role | Account Creation | Core Capabilities | Data Scoping |
| :--- | :--- | :--- | :--- |
| **PATIENT** | Self-registration (`POST /api/auth/register`) or seed data | Browse departments, doctors, schedules, and open slots; book online appointments; reschedule or cancel own active appointments; view own notifications and live queue board | Sees only own appointments and own notifications |
| **DOCTOR** | Created by Admin (via Doctor Profile setup) or seed data | View own daily queue and appointments; call next patient (`CONFIRMED -> IN_CONSULTATION`), mark consultation finished (`IN_CONSULTATION -> COMPLETED`), or record `NO_SHOW` | Sees only own queue, own appointments, and own notifications |
| **ADMIN** (Receptionist / Administrator) | Seed data or Admin provisioning | Manage departments, doctors, and doctor schedules; register walk-in patients and walk-in bookings; confirm/update/reschedule/cancel any appointment; view all notifications; generate daily reports and export CSV | Full system access across all doctors, patients, notifications, and reports |

---

## 3. Functional Requirements

### 3.1 Authentication and Authorization
- **FR-AUTH-01:** `POST /api/auth/register` validates name, email format, password length ($\ge 8$), phone, and creates a `users` row with `role = 'PATIENT'` (ignoring any client-supplied role) plus a linked `patients` row in one transaction.
- **FR-AUTH-02:** `POST /api/auth/login` verifies credentials using Werkzeug `check_password_hash` and issues an 8-hour JWT bearer token containing `sub` (user ID), `role`, and `exp`.
- **FR-AUTH-03:** `GET /api/auth/me` returns the authenticated user profile and linked `patient_id` or `doctor_id`.
- **FR-AUTH-04:** Role-checking decorators protect endpoints; unauthorized requests return `401` and insufficient permissions return `403`.

### 3.2 Departments, Doctors, Schedules, and Slot Generation
- **FR-MASTER-01:** Admin can create and list hospital departments (`GET/POST /api/departments`).
- **FR-MASTER-02:** Admin can create and list doctors (`GET/POST /api/doctors`), which creates both the `DOCTOR` user account and `doctors` profile with a unique `doc_code` (e.g., `DOC1`).
- **FR-MASTER-03:** Admin configures doctor schedules per `day_of_week` (`0 = Monday ... 6 = Sunday`, matching Python `date.weekday()`), `start_time`, `end_time`, `slot_duration_minutes`, and `max_patients`. Overlapping schedules for the same doctor and weekday are rejected (`409` or `400`).
- **FR-MASTER-04:** `GET /api/doctors/<id>/slots?date=YYYY-MM-DD` splits each active schedule window `(start_time, end_time)` by `slot_duration_minutes`. Effective daily capacity is $\min(\text{number of generated slots}, \text{max\_patients})$.

### 3.3 Appointment Booking (Online & Walk-In) and Token Allocation
- **FR-BOOK-01:** Booking dates must be valid `YYYY-MM-DD`, not in the past, and at most 30 days ahead in `HOSPITAL_TIMEZONE`. For today, slots earlier than the current hospital time are rejected.
- **FR-BOOK-02:** Online booking by a `PATIENT` creates an appointment with initial status `BOOKED`.
- **FR-BOOK-03:** Walk-in booking by an `ADMIN` supports selecting an existing patient or creating a new walk-in patient (`full_name`, `phone`, optional `email`, `user_id = NULL`). If no `slot_time` is provided, the system automatically assigns the earliest available slot at or after the current time today (or returns `409` if none remains). Walk-in appointments start in status `CONFIRMED`.
- **FR-BOOK-04:** Every booking generates a sequential daily token per doctor formatted as `<DOC_CODE>-<3-digit-seq>` (e.g., `DOC1-001`) using `doctor_token_counters` inside the booking transaction. Cancelled tokens are never reused.
- **FR-BOOK-05:** Double-booking of an active slot is prevented both in application logic and at the database level via the `STORED` generated column `active_slot_key` (`NULL` when `status = 'CANCELLED'`, otherwise `CONCAT(doctor_id, '|', appointment_date, '|', slot_time)`) with a `UNIQUE` index. Concurrent conflicts return `409 Conflict`.

### 3.4 Queue Lifecycle and Status State Machine
- **FR-STATUS-01:** Valid status transitions:
  - `BOOKED -> CONFIRMED` (Admin)
  - `CONFIRMED -> IN_CONSULTATION` (Doctor own, Admin)
  - `IN_CONSULTATION -> COMPLETED` (Doctor own, Admin)
  - `BOOKED / CONFIRMED -> CANCELLED` (Patient own, Admin)
  - `BOOKED / CONFIRMED -> NO_SHOW` (Doctor own, Admin; only on or after `appointment_date`)
- **FR-STATUS-02:** `COMPLETED`, `CANCELLED`, and `NO_SHOW` are terminal states.
- **FR-STATUS-03:** At most one appointment per doctor may be in `IN_CONSULTATION` at any moment.
- **FR-STATUS-04:** Every status creation or transition records an audit entry in `appointment_status_history`.

### 3.5 Rescheduling and Cancellation
- **FR-RESCHED-01:** Patients (own) and Admins can reschedule `BOOKED` or `CONFIRMED` appointments.
- **FR-RESCHED-02:** If `doctor_id` and `appointment_date` remain the same, `token_number` is preserved. If either changes, a new token is generated for the target doctor/date and the prior token is stored in `previous_token`.
- **FR-RESCHED-03:** Cancellation sets `status = 'CANCELLED'`, setting `active_slot_key = NULL` and immediately freeing the slot for rebooking.

### 3.6 Live Queue Board
- **FR-QUEUE-01:** `GET /api/queue?date=&doctor_id=&department_id=` returns the daily queue ordered by `slot_time ASC, token_number ASC`, highlighting the token currently `IN_CONSULTATION` and upcoming waiting tokens.
- **FR-QUEUE-02:** The React Queue Board polls every 5-10 seconds without WebSockets.

### 3.7 Notifications
- **FR-NOTIF-01:** `NotificationService` triggers on booking creation/confirmation, rescheduling, cancellation, and status updates.
- **FR-NOTIF-02:** Emails use `smtplib` with a 10-second timeout (`SMTP_SENT` when configured and reachable; graceful fallback to `SIMULATED` with `error_message` logged on failure). SMS notifications are always logged as `SIMULATED`.
- **FR-NOTIF-03:** `GET /api/notifications` returns paginated logs scoped by role.

### 3.8 Daily Reports and Export
- **FR-REPORT-01:** `GET /api/reports/daily?date=YYYY-MM-DD` (Admin only) returns total appointments, status breakdown, per-doctor counts, online vs. walk-in counts, and hourly/slot distribution.
- **FR-REPORT-02:** `GET /api/reports/daily/export?date=YYYY-MM-DD` streams a CSV download.

---

## 4. Non-Functional Requirements

- **NFR-01 Unified Error Format:** All API errors return `{ "error": { "code": "...", "message": "..." } }` with appropriate HTTP status codes (`400`, `401`, `403`, `404`, `409`, `500`).
- **NFR-02 Concurrency Safety:** Row locking / atomic counter updates on `doctor_token_counters` and the unique index on `active_slot_key` guarantee zero duplicate tokens or double-booked slots under concurrent load.
- **NFR-03 Fault Isolation:** Notification SMTP failures never roll back or fail a booking or status update transaction.
- **NFR-04 Security:** Passwords hashed with Werkzeug (`generate_password_hash`), JWT tokens expire after 8 hours, `.env` excluded from version control.
