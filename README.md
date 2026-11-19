# Project 25: Smart Hospital Appointment and Patient Queue Management System

A full-stack, modular web application for hospital outpatient appointment booking, walk-in registration, sequential token generation, real-time deterministic queue tracking, email/SMS notification logging, and daily analytics with CSV exports.

**No AI/ML:** All slot computations, token allocations, queue orderings, and reporting metrics are 100% deterministic, clean, and reliable.

---

## 1. Quickstart Commands

### Prerequisites
- Python 3.11+
- Node.js 20+
- MySQL Server 8.0+

### Database Initialization
```bash
mysql -u root -p < backend/database/schema.sql
mysql -u root -p < backend/database/seed.sql
```

### Backend Setup & Server Start
```bash
# Set up virtual environment
python -m venv .venv
.\.venv\Scripts\activate   # Linux/macOS: source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Run pytest test suite
pytest

# Start Flask backend API (http://127.0.0.1:5000)
python backend/run.py
```

### Frontend Setup & Development Server
```bash
cd frontend
npm install
npm test
npm run build
npm run dev                # http://127.0.0.1:5173
```

---

## 2. Seed Credentials

| Role | Email | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Administrator / Receptionist** | `admin@hospital.test` | `Admin@123` | Master data, walk-in booking, queue oversight, reports |
| **Doctor 1 (Cardiology)** | `doctor1@hospital.test` | `Doctor@123` | Doctor console, own queue, call/complete patient |
| **Doctor 2 (General Medicine)** | `doctor2@hospital.test` | `Doctor@123` | Doctor console, own queue, call/complete patient |
| **Doctor 3 (Orthopedics)** | `doctor3@hospital.test` | `Doctor@123` | Doctor console, own queue, call/complete patient |
| **Patient 1** | `patient1@hospital.test` | `Patient@123` | Patient dashboard, slot booking, own appointments |
| **Patient 2** | `patient2@hospital.test` | `Patient@123` | Patient dashboard, slot booking, own appointments |
| **Patient 3** | `patient3@hospital.test` | `Patient@123` | Patient dashboard, slot booking, own appointments |

---

## 3. Architecture & Key Features

- **Database Concurrency & Integrity**:
  - `STORED` generated column `active_slot_key` on `appointments` prevents double booking of active slots at the database engine level, while allowing cancelled slots to be freely rebooked.
  - Safe sequential daily token counter per doctor (`DOC1-001`, `DOC1-002`) updated atomically inside the booking transaction. Cancelled tokens are never reused.
- **Strict Status Lifecycle**:
  - `BOOKED -> CONFIRMED -> IN_CONSULTATION -> COMPLETED`
  - Cancellation allowed from `BOOKED` or `CONFIRMED`.
  - `NO_SHOW` permitted only on or after the scheduled appointment date.
  - At most one patient per doctor can be `IN_CONSULTATION` at any given time.
- **Resilient Notifications**:
  - `NotificationService` attempts SMTP delivery with a 10s connection timeout and gracefully falls back to simulated logging on network or credential absence.
  - SMS notifications are permanently simulated and logged for patient audit.
- **Reporting & Visual Analytics**:
  - Daily summary metrics with Chart.js doughnut, bar, and line visualizations.
  - One-click CSV export of daily visits.

---

## 4. Suggested Commit Milestones

### Phase 1 (MVP — Weeks 1 to 6)
- **Week 1 (1A)**: Repository layout, `.gitignore`, `.env.example`, MySQL `schema.sql` (with `active_slot_key`), `seed.sql` with Werkzeug hashes, Flask factory, and health endpoint.
- **Week 2-3 (1B)**: JWT authentication, RBAC decorators, department/doctor endpoints, and slot generation.
- **Week 4 (1C)**: Online and walk-in appointment booking, token counters, 409 duplicate slot rejection, and queue endpoint.
- **Week 5 (1D)**: Vite setup, Axios client with Bearer tokens, route guards, Login/Register pages, and Patient Dashboard.
- **Week 6 (1E)**: Doctor Console, Admin/Receptionist Console, Live Queue Board polling, and Phase 1 test suite.

### Phase 2 (Enhancements & Documentation — Weeks 7 to 12)
- **Week 7 (2A)**: Rescheduling and cancellation endpoints and UI, token preservation/reissuance, and concurrency tests.
- **Week 8 (2B)**: NotificationService with SMTP and simulated fallback, SMS logging, and Notifications page.
- **Week 9-10 (2C)**: Daily reports API, CSV export endpoint, and ReportsPage with Chart.js.
- **Week 11-12 (2D)**: Consolidated end-to-end integration tests, final documentation accuracy pass, and release verification.

---

## 5. Comprehensive Documentation

- [docs/DEVELOPER_MANUAL.md](file:///d:/projects/Smart%20Hospital%20Appointment%20and%20Patient%20Queue%20Management%20System/docs/DEVELOPER_MANUAL.md) — Step-by-step developer guide for manual end-to-end testing
- [docs/SRS.md](file:///d:/projects/Smart%20Hospital%20Appointment%20and%20Patient%20Queue%20Management%20System/docs/SRS.md) — Software Requirements Specification
- [docs/ER_AND_UML_DIAGRAMS.md](file:///d:/projects/Smart%20Hospital%20Appointment%20and%20Patient%20Queue%20Management%20System/docs/ER_AND_UML_DIAGRAMS.md) — Mermaid ER, Use-Case, Sequence, and State Diagrams
- [docs/ARCHITECTURE.md](file:///d:/projects/Smart%20Hospital%20Appointment%20and%20Patient%20Queue%20Management%20System/docs/ARCHITECTURE.md) — System Architecture & REST API Reference Table
- [docs/TEST_PLAN_AND_CASES.md](file:///d:/projects/Smart%20Hospital%20Appointment%20and%20Patient%20Queue%20Management%20System/docs/TEST_PLAN_AND_CASES.md) — Test Cases & Execution Matrix
- [docs/USER_MANUAL.md](file:///d:/projects/Smart%20Hospital%20Appointment%20and%20Patient%20Queue%20Management%20System/docs/USER_MANUAL.md) — Step-by-step role guides
- [docs/DEPLOYMENT_NOTES.md](file:///d:/projects/Smart%20Hospital%20Appointment%20and%20Patient%20Queue%20Management%20System/docs/DEPLOYMENT_NOTES.md) — Production setup & Nginx configuration
