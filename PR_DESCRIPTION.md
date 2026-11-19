# Pull Request: Phase 1 (MVP) & Phase 2 (Enhancements & Docs) to Main

## 1. Executive Summary
This PR merges the full-stack, production-ready implementation of **Project 25: Smart Hospital Appointment and Patient Queue Management System (Simple Variant)** into `main`. The system completely fulfills all functional requirements (FR), non-functional requirements (NFR), and strict technical stack specifications without any AI/ML dependencies.

---

## 2. Changes Summary by Phase

### Phase 1: MVP Core
- **Foundation (1A)**:
  - MySQL 8.0+ InnoDB database schema (`backend/database/schema.sql`) defining all 9 tables with foreign keys and the `STORED` generated column `active_slot_key` + unique index (`uq_appointments_active_slot_key`).
  - `seed.sql` with real Werkzeug `scrypt` password hashes (`backend/scripts/generate_seed_hashes.py`) and `CURDATE()`-relative dynamic dates.
  - Flask application factory (`backend/app/__init__.py`), `Config` classes, timezone utilities (`HOSPITAL_TIMEZONE=Asia/Kolkata`), unified error handlers, and `/api/health` endpoint.
- **Authentication & Master Data (1B)**:
  - 8-hour JWT bearer tokens, `@auth_required` and `@roles_required` decorators.
  - Self-registration strictly enforcing `PATIENT` role and creating linked `patients` record.
  - Department, Doctor, and Schedule configuration with schedule overlap detection on identical weekdays (`409 SCHEDULE_OVERLAP`).
  - Deterministic slot generation calculating effective capacity $\min(\text{total\_slots}, \text{max\_patients})$.
- **Booking & Queue Core (1C)**:
  - Online booking (`BOOKED`) and walk-in booking (`CONFIRMED`, auto-assigning next free slot if omitted).
  - Atomic sequential daily token allocation `<DOC_CODE>-<3-digit-seq>`.
  - Duplicate active slot prevention (`409 SLOT_ALREADY_BOOKED`) and daily capacity limits (`409 DAILY_CAPACITY_REACHED`).
  - Status state machine with single `IN_CONSULTATION` guard per doctor, `NO_SHOW` date restrictions, and `appointment_status_history` logging.
  - Public daily queue endpoint (`/api/queue`).
- **Frontend Foundation & Patient Console (1D)**:
  - Vite React setup, Axios client with JWT interceptor and 401 handling, ProtectedRoute guards.
  - `LoginPage`, `RegisterPage`, and `PatientDashboard` with slot grid and token confirmation.
- **Staff Screens (1E)**:
  - `DoctorDashboard` for calling next token and marking completion.
  - `AdminDashboard` for walk-in booking, status updates, doctor profiles, and schedule management.
  - `QueueBoard` with live polling every 6 seconds.

### Phase 2: Enhancements & Documentation
- **Rescheduling, Cancellation & Concurrency (2A)**:
  - `PATCH /api/appointments/<id>/reschedule`: Retains token if doctor/date unchanged; issues new token and stores prior token in `previous_token` if doctor/date changes.
  - `POST /api/appointments/<id>/cancel`: Frees slot for rebooking (`active_slot_key` becomes `NULL`); cancelled tokens are never reused.
  - Multi-threaded concurrency test verifying that when multiple threads book the same slot, exactly 1 succeeds (201) and the rest receive 409 Conflict.
- **Notifications (2B)**:
  - `NotificationService` supporting SMTP with a strict 10s timeout, graceful fallback to `SIMULATED`, and permanently simulated SMS alerts.
  - `GET /api/notifications` paginated endpoint and `NotificationsPage` UI.
- **Daily Reports & CSV Export (2C)**:
  - `GET /api/reports/daily` returning status, doctor, online vs. walk-in, and hourly distributions.
  - `GET /api/reports/daily/export` generating streaming CSV downloads.
  - `ReportsPage` UI with Chart.js Doughnut, Bar, and Line charts.
- **Full Accuracy Pass & Documentation (2D)**:
  - Consolidated end-to-end integration test (`test_appointments_and_queue.py`).
  - Comprehensive documentation: `SRS.md`, `ER_AND_UML_DIAGRAMS.md`, `ARCHITECTURE.md`, `TEST_PLAN_AND_CASES.md`, `USER_MANUAL.md`, `DEPLOYMENT_NOTES.md`, and `README.md`.

---

## 3. Test Results & Build Verification

- **Backend Pytest Suite**:
  - `21 passed in 11.65s` (0 failures, 0 errors, 0 warnings)
  - Suites: `test_foundation.py`, `test_auth_and_master.py`, `test_booking_and_queue_core.py`, `test_reschedule_cancel_concurrency.py`, `test_notifications.py`, `test_reports.py`, `test_appointments_and_queue.py`.
- **Frontend Vitest Suite**:
  - `7 passed (7)` across 2 test files (`auth_and_patient.test.jsx`, `staff_and_queue.test.jsx`).
- **Frontend Production Build**:
  - `vite build` completed successfully (`105 modules transformed`, output in `frontend/dist/`).

---

## 4. How to Verify
1. Run backend tests:
   ```bash
   pytest
   ```
2. Run frontend tests:
   ```bash
   npm --prefix frontend test
   ```
3. Run frontend build:
   ```bash
   npm --prefix frontend run build
   ```
4. Start backend server:
   ```bash
   python backend/run.py
   ```
5. Start frontend dev server:
   ```bash
   cd frontend && npm run dev
   ```
6. Log in as `admin@hospital.test` (`Admin@123`), `doctor1@hospital.test` (`Doctor@123`), or `patient1@hospital.test` (`Patient@123`).
