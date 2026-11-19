# Smart Hospital Appointment and Patient Queue Management System

A full-stack, modular web application for hospital outpatient appointment booking, queue management, and doctor consultations.

---

## 1. Quickstart Commands (Local Development)

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
.\.venv\Scripts\activate   # Windows (or: source .venv/bin/activate on Linux/macOS)

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment
copy .env.example .env    # Windows (or: cp .env.example .env on Linux/macOS)

# Start backend server
python backend/run.py      # http://127.0.0.1:5000
```

### Frontend Setup & Dev Server Start
```bash
cd frontend
npm install
npm run dev                # http://127.0.0.1:5173
```

---

## 2. Seed Credentials

| Role | Email | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@hospital.test` | `Admin@123` | Master data (doctors, departments, slots), daily reports, CSV export, notifications log |
| **Doctor** | `doctor1@hospital.test` | `Doctor@123` | Doctor console, patient calling, consultation status transitions (`IN_CONSULTATION`, `COMPLETED`, `NO_SHOW`) |
| **Doctor** | `doctor2@hospital.test` | `Doctor@123` | Doctor console (Pediatrics) |
| **Staff / Receptionist** | `staff@hospital.test` | `Staff@123` | Walk-in patient registration, immediate token generation, live queue board |
| **Patient** | `patient1@hospital.test` | `Patient@123` | Appointment booking, rescheduling, cancellation, token viewing |

---

## 3. Architecture & Key Features

- **Database Concurrency & Integrity**:
  - `STORED` generated column `active_slot_key` on `appointments` prevents double booking of active slots at the database engine level, while allowing cancelled slots to be freely rebooked.
  - Safe sequential daily token counter per doctor (`DOC1-001`, `DOC1-002`) updated atomically inside the booking transaction (`ON DUPLICATE KEY UPDATE`). Cancelled tokens are never reused.
- **Strict Status Lifecycle**:
  - `BOOKED -> CONFIRMED -> IN_CONSULTATION -> COMPLETED`
  - Cancellation allowed from `BOOKED` or `CONFIRMED`.
  - Terminal statuses: `COMPLETED`, `CANCELLED`, `NO_SHOW`.
- **Role-Based Access Control (RBAC)**:
  - Secure JWT authentication with strict role checks on every API endpoint.
- **Live Queue Monitoring**:
  - Real-time auto-refresh queue board displaying current token calling and waiting list.
- **Email & Notification Engine**:
  - Automated transactional email confirmations with safe `SIMULATED` fallback when external SMTP credentials are not configured.

---

## 4. Suggested Commit Milestones

### Phase 1 (MVP — Weeks 1 to 6)
- **Week 1 (1A)**: Repository layout, `.gitignore`, `.env.example`, MySQL `schema.sql` (with `active_slot_key`), `seed.sql` with Werkzeug hashes, Flask factory, and health endpoint.
- **Week 2 (1B)**: Master data APIs (doctors, departments, slots) and JWT auth endpoints (`/api/auth/register`, `/api/auth/login`, `/api/auth/me`).
- **Week 3 (1C)**: Atomic booking engine with daily token generation and double-booking guard.
- **Week 4 (1D)**: Doctor consultation console and public live queue board APIs.
- **Week 5 (1E)**: Frontend MVP UI (Vite, React Router, TailwindCSS, Axios interceptors, responsive Navbar, Role-based route guards).
- **Week 6 (1F)**: MVP release tag, backend & frontend unit tests, integration verification.

### Phase 2 (Enhancements & Production Polish — Weeks 7 to 12)
- **Week 7-8 (2A)**: Appointment cancellation and slot rescheduling with token recalculation.
- **Week 8 (2B)**: Automated email notification system with SMTP and safe simulated logging fallback.
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
