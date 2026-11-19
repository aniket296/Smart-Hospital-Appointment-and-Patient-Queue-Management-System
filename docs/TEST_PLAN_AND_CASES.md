# Test Plan and Test Cases

## Project 25: Smart Hospital Appointment and Patient Queue Management System

---

## 1. Test Strategy Overview

The testing architecture encompasses four distinct testing tiers:
1. **Unit & State Machine Tests (Backend Pytest)**: Role validation, date parsing, timezone checking, password hashing, and appointment lifecycle state transitions.
2. **Concurrency & Race-Condition Tests (Backend Pytest + ThreadPoolExecutor)**: Multiple concurrent requests attempting to book the identical slot; verifying atomic sequence numbers and that exactly one succeeds while others receive 409 Conflict.
3. **Integration & API Tests (Backend Pytest)**: Complete end-to-end user journeys including self-registration, walk-in creation, queue inspection, status progression, notification dispatching, and CSV report export.
4. **Frontend Component & Guard Tests (Frontend Vitest + React Testing Library)**: Authentication flows, route guards, token persistence, dynamic slot selection, queue polling, and audit trail rendering.

---

## 2. Test Execution Matrix

| Test ID | Module / Suite | Test Case Description | Expected Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **TC-FND-01** | `test_foundation.py` | Health endpoint returns 200 with hospital timezone and timestamp | HTTP 200, timezone `Asia/Kolkata` | **PASSED** |
| **TC-FND-02** | `test_foundation.py` | SQL schema and seed files exist, include `active_slot_key` generated column | Tables created, `STORED` generated column present | **PASSED** |
| **TC-FND-03** | `test_foundation.py` | Seed password hashes verify correctly with default credentials | All accounts verify with `check_password_hash` | **PASSED** |
| **TC-AUTH-01** | `test_auth_and_master.py` | Self-registration always creates a `PATIENT` and linked profile | User created as `PATIENT` (client role ignored), linked `patients` row created | **PASSED** |
| **TC-AUTH-02** | `test_auth_and_master.py` | Registration rejects invalid email and passwords shorter than 8 chars | HTTP 400 validation error | **PASSED** |
| **TC-AUTH-03** | `test_auth_and_master.py` | Login returns 8-hour JWT; `GET /api/auth/me` returns linked profile | HTTP 200, JWT token returned | **PASSED** |
| **TC-RBAC-01** | `test_auth_and_master.py` | Non-admin users cannot create departments or doctors | HTTP 403 Forbidden | **PASSED** |
| **TC-SCHED-01** | `test_auth_and_master.py` | Overlapping doctor schedules on same weekday are rejected | HTTP 409 `SCHEDULE_OVERLAP` | **PASSED** |
| **TC-BOOK-01** | `test_booking_and_queue_core.py` | Sequential token issuance per doctor (`DOC1-001`, `DOC1-002`) | Consecutive tokens issued within transaction | **PASSED** |
| **TC-BOOK-02** | `test_booking_and_queue_core.py` | Duplicate booking of the same active slot is rejected | HTTP 409 `SLOT_ALREADY_BOOKED` | **PASSED** |
| **TC-BOOK-03** | `test_booking_and_queue_core.py` | Booking beyond doctor daily `max_patients` cap is rejected | HTTP 409 `DAILY_CAPACITY_REACHED` | **PASSED** |
| **TC-BOOK-04** | `test_booking_and_queue_core.py` | Cancelled token is never reused; cancelled slot can be rebooked | New booking gets next token; slot is reusable | **PASSED** |
| **TC-STATE-01** | `test_booking_and_queue_core.py` | Full status lifecycle state transitions (`BOOKED -> CONFIRMED -> IN_CONSULTATION -> COMPLETED`) | Valid transitions succeed, history recorded | **PASSED** |
| **TC-STATE-02** | `test_booking_and_queue_core.py` | Only 1 appointment per doctor can be `IN_CONSULTATION` | HTTP 400 `DOCTOR_BUSY` on second token | **PASSED** |
| **TC-RESCHED-01** | `test_reschedule_cancel_concurrency.py` | Reschedule on same doctor & date preserves token | Token retained, old slot freed | **PASSED** |
| **TC-RESCHED-02** | `test_reschedule_cancel_concurrency.py` | Reschedule to different date issues new token and sets `previous_token` | New daily token issued, old in `previous_token` | **PASSED** |
| **TC-CONCUR-01** | `test_reschedule_cancel_concurrency.py` | 5 concurrent threads booking identical slot | Exactly 1 HTTP 201, 4 HTTP 409 | **PASSED** |
| **TC-NOTIF-01** | `test_notifications.py` | Notifications fall back to `SIMULATED` when SMTP unconfigured | HTTP 200, logged in `notification_logs` | **PASSED** |
| **TC-NOTIF-02** | `test_notifications.py` | Mocked SMTP server sends email and logs `SMTP_SENT` | Mode is `SMTP_SENT`, zero crashes | **PASSED** |
| **TC-REP-01** | `test_reports.py` | Daily report summary endpoint returns status and doctor breakdowns | HTTP 200, accurate aggregation | **PASSED** |
| **TC-REP-02** | `test_reports.py` | Daily CSV export returns file attachment with appointment headers | HTTP 200, `text/csv` attachment | **PASSED** |
| **TC-E2E-01** | `test_appointments_and_queue.py` | Complete end-to-end outpatient journey from booking to completed report | Full lifecycle passes end-to-end | **PASSED** |
| **TC-UI-01** | `auth_and_patient.test.jsx` | Unauthenticated visits redirect to `/login`; role guards enforce access | Route guard redirection works | **PASSED** |
| **TC-UI-02** | `auth_and_patient.test.jsx` | Patient dashboard loads slots and confirms online booking with token | Token displayed in UI status alert | **PASSED** |
| **TC-UI-03** | `staff_and_queue.test.jsx` | Queue board renders current in consultation and next waiting tokens | Live queue correctly displayed | **PASSED** |
| **TC-UI-04** | `staff_and_queue.test.jsx` | Notifications audit trail renders paginated alerts | Notifications table rendered | **PASSED** |
