# Smart Hospital Appointment and Patient Queue Management System

A full-stack, modular web application for hospital outpatient appointment booking, queue management, and doctor consultations.

---

## Table of Contents
1. [Developer Manual: How to Run on Your Local Device](#1-developer-manual-how-to-run-on-your-local-device)
   - [System Prerequisites](#11-system-prerequisites)
   - [Step 1: Clone the Repository](#12-step-1-clone-the-repository)
   - [Step 2: Database Initialization (MySQL 8.0+)](#13-step-2-database-initialization-mysql-80)
   - [Step 3: Backend Setup & Server Start](#14-step-3-backend-setup--server-start)
   - [Step 4: Frontend Setup & Dev Server Start](#15-step-4-frontend-setup--dev-server-start)
   - [Step 5: First-Time User Walkthrough & Verification](#16-step-5-first-time-user-walkthrough--verification)
   - [Step 6: Running Automated Tests](#17-step-6-running-automated-tests)
   - [Troubleshooting & Common Fixes](#18-troubleshooting--common-fixes)
2. [Seed Credentials](#2-seed-credentials)
3. [Architecture & Key Features](#3-architecture--key-features)
4. [Suggested Commit Milestones](#4-suggested-commit-milestones)
5. [Comprehensive Documentation Links](#5-comprehensive-documentation-links)

---

## 1. Developer Manual: How to Run on Your Local Device

Welcome to the team! This guide walks you through setting up and running the **Smart Hospital Appointment and Patient Queue Management System** on your local machine from scratch.

### 1.1 System Prerequisites

Before starting, make sure your machine has the following tools installed:

| Tool | Minimum Version | How to Verify in Terminal | Download Link |
| :--- | :--- | :--- | :--- |
| **Python** | `3.11+` | `python --version` (or `python3 --version`) | [python.org](https://www.python.org/downloads/) |
| **Node.js & npm** | Node `20.x+`, npm `10.x+` | `node -v` and `npm -v` | [nodejs.org](https://nodejs.org/) |
| **MySQL Server** | `8.0+` | `mysql --version` | [mysql.com](https://dev.mysql.com/downloads/installer/) |
| **Git** | `2.x+` | `git --version` | [git-scm.com](https://git-scm.com/) |

> [!NOTE]
> Ensure your local MySQL server service is active before proceeding. You can run MySQL via MySQL Community Server, MySQL Workbench, XAMPP, or a local Docker container.

---

### 1.2 Step 1: Clone the Repository

Open your terminal (PowerShell, Command Prompt, or bash) and clone the repository:

```bash
git clone https://github.com/your-username/smart-hospital-queue-management.git
cd "Smart Hospital Appointment and Patient Queue Management System"
```

---

### 1.3 Step 2: Database Initialization (MySQL 8.0+)

The application requires two MySQL databases:
1. `hospital_queue_db`: Main application database for local development.
2. `hospital_queue_test_db`: Isolated database for running backend automated tests.

Both databases, required tables, foreign keys, constraints, and initial seed data are provisioned by running the provided SQL scripts:

```bash
# Windows / PowerShell / Linux / macOS
mysql -u root -p < backend/database/schema.sql
mysql -u root -p < backend/database/seed.sql
```

*(Enter your MySQL `root` password when prompted).*

#### What these scripts set up:
- **`schema.sql`**: Creates `hospital_queue_db` and `hospital_queue_test_db`, table schemas (`users`, `departments`, `doctors`, `doctor_schedules`, `slots`, `appointments`, `daily_token_counters`, `notifications`), and the `STORED` generated column `active_slot_key` to strictly eliminate double-booking at the database engine level.
- **`seed.sql`**: Seeds standard medical departments (Cardiology, Pediatrics, Orthopedics, General Medicine), sample doctors with weekly schedules, pre-calculated slots, and pre-hashed user credentials for all 4 roles.

---

### 1.4 Step 3: Backend Setup & Server Start

Open a dedicated terminal window for the Flask backend.

#### 1. Create and Activate Python Virtual Environment
```bash
# Create virtual environment in root directory
python -m venv .venv

# Activate virtual environment:
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Windows (Command Prompt):
.\.venv\Scripts\activate.bat
# On macOS / Linux:
source .venv/bin/activate
```

#### 2. Install Python Dependencies
```bash
pip install -r backend/requirements.txt
```

#### 3. Configure the `.env` File
Copy the example environment template to `.env`:
```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` in your text editor and ensure the MySQL connection credentials match your machine:
```ini
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production
JWT_SECRET_KEY=dev-jwt-secret-key-change-in-production
JWT_EXPIRY_HOURS=8
HOSPITAL_TIMEZONE=Asia/Kolkata
CORS_ORIGINS=*

# Local Database Configuration
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=hospital_queue_db
TEST_DB_NAME=hospital_queue_test_db

# Email Notification System (optional - leaves SIMULATED mode active if empty)
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_USE_TLS=true
SMTP_FROM=noreply@hospital.test

# Frontend Proxy URL
VITE_API_BASE_URL=http://127.0.0.1:5000/api
```
*(Replace `your_mysql_password` with your actual local MySQL `root` password).*

#### 4. Start the Flask Backend Server
```bash
python backend/run.py
```
Expected output:
```text
Starting Flask server on http://127.0.0.1:5000 (debug=True)...
 * Serving Flask app 'backend.app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

#### 5. Verify Backend Health Check
Open your browser or run in another terminal:
```bash
curl http://127.0.0.1:5000/api/health
```
Expected JSON response:
```json
{
  "database": "connected",
  "service": "Smart Hospital Appointment and Patient Queue Management System",
  "status": "ok",
  "timezone": "Asia/Kolkata"
}
```

---

### 1.5 Step 4: Frontend Setup & Dev Server Start

Keep the backend running and open a **second terminal window** for the React + Vite frontend.

#### 1. Navigate to Frontend & Install Dependencies
```bash
cd frontend
npm install
```

#### 2. Verify `.env` (Optional)
The frontend connects to `/api` by default using Vite's built-in proxy in `vite.config.js`. If needed, ensure `frontend/.env.example` is copied or defaults to:
```ini
VITE_API_BASE_URL=http://127.0.0.1:5000/api
```

#### 3. Start Vite Development Server
```bash
npm run dev
```
Expected output:
```text
  VITE v6.4.6  ready in 320 ms

  ➜  Local:   http://127.0.0.1:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

Now open **`http://127.0.0.1:5173`** in your browser.

---

### 1.6 Step 5: First-Time User Walkthrough & Verification

Use the pre-seeded accounts to verify end-to-end functionality across all system roles:

#### 1. Patient Experience (Booking & Rescheduling)
1. Navigate to `http://127.0.0.1:5173/login`.
2. Sign in with **`patient1@hospital.test`** / **`Patient@123`**.
3. Select a doctor (e.g. Dr. Ramesh Sharma - Cardiology), pick a date and an available slot, and submit booking.
4. An atomic sequential token (e.g., `DOC1-001`) is immediately generated and displayed.
5. Test rescheduling to another available slot or cancelling the appointment.

#### 2. Receptionist / Staff Experience (Walk-in Registration)
1. Sign out and sign in with **`staff@hospital.test`** / **`Staff@123`**.
2. Open the **Staff Walk-in** console.
3. Register a walk-in patient with name, phone, and doctor selection.
4. Immediate walk-in token is allocated and queued.

#### 3. Doctor Experience (Consultation & Calling)
1. Sign out and sign in with **`doctor1@hospital.test`** / **`Doctor@123`**.
2. Open the **Doctor Console**.
3. View the patient queue for today.
4. Click **Call Next Patient** (transitions appointment status to `IN_CONSULTATION`).
5. Click **Mark Completed** (transitions status to `COMPLETED`).

#### 4. Live Public Queue Board
1. Open `http://127.0.0.1:5173/queue` in a browser window or TV display mode.
2. Observe real-time auto-refresh of currently serving tokens and waiting lists by department and doctor.

#### 5. Admin Experience (Reports & Notifications)
1. Sign out and sign in with **`admin@hospital.test`** / **`Admin@123`**.
2. Visit **Admin Dashboard**: Manage doctors, departments, and schedules.
3. Visit **Reports**: View interactive Chart.js graphs of daily bookings, completion rates, and click **Export CSV** to download raw metrics.
4. Visit **Notifications**: Verify automated `SIMULATED` email and SMS transaction logs recorded without requiring third-party credentials.

---

### 1.7 Step 6: Running Automated Tests

Run the complete test suite to ensure everything is functioning properly:

#### 1. Backend Automated Tests (pytest)
Runs 21 unit and integration tests including authentication, concurrency guards, token counters, rescheduling, cancellation, notifications, and reports:
```bash
# From repository root (with virtualenv active)
pytest -v
# Or on Windows explicitly:
.\.venv\Scripts\pytest.exe -v
```
*(All 21 tests should pass).*

#### 2. Frontend Automated Tests (Vitest)
Runs frontend component tests, route guards, and queue board rendering:
```bash
# From repository root
npm --prefix frontend test
# Or from inside frontend/:
cd frontend
npm test
```
*(All 7 tests should pass).*

#### 3. Frontend Production Build Check
Verifies that Vite builds the optimized production bundle without syntax or type errors:
```bash
npm --prefix frontend run build
```

---

### 1.8 Troubleshooting & Common Fixes

| Issue | Likely Cause | Solution |
| :--- | :--- | :--- |
| `Access denied for user 'root'@'localhost'` | Incorrect MySQL password in `.env` | Update `DB_PASSWORD` in `.env` to match your local MySQL root password. |
| `Unknown database 'hospital_queue_db'` | Schema SQL was not executed | Run `mysql -u root -p < backend/database/schema.sql` to recreate tables. |
| `Can't connect to MySQL server on '127.0.0.1'` | MySQL service is stopped | Start the MySQL service from Windows Services (`services.msc`), brew service on Mac, or `systemctl start mysql` on Linux. |
| `Port 5000 is already in use` | Another instance of Flask or AirPlay is running | Terminate the process using port 5000 or set `FLASK_RUN_PORT=5001` in `.env`. |
| `Port 5173 is already in use` | Another Vite process is open | Vite will automatically suggest port 5174; press `y` to accept or close existing instances. |
| `ModuleNotFoundError: No module named 'flask'` | Python virtualenv is not activated | Run `.\.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` before running `python backend/run.py`. |
| `CORS Error in Browser Console` | Backend is not running or CORS is misconfigured | Verify Flask backend is running on `http://127.0.0.1:5000` and `CORS_ORIGINS=*` in `.env`. |

---

## 2. Seed Credentials

| Role | Email | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@hospital.test` | `Admin@123` | Master data (doctors, departments, schedules), daily reports, CSV export, notifications log |
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

## 5. Comprehensive Documentation Links

- [docs/DEVELOPER_MANUAL.md](file:///d:/projects/Smart%20Hospital%20Appointment%20and%20Patient%20Queue%20Management%20System/docs/DEVELOPER_MANUAL.md) — Step-by-step developer guide for manual end-to-end testing
- [docs/SRS.md](file:///d:/projects/Smart%20Hospital%20Appointment%20and%20Patient%20Queue%20Management%20System/docs/SRS.md) — Software Requirements Specification
- [docs/ER_AND_UML_DIAGRAMS.md](file:///d:/projects/Smart%20Hospital%20Appointment%20and%20Patient%20Queue%20Management%20System/docs/ER_AND_UML_DIAGRAMS.md) — Mermaid ER, Use-Case, Sequence, and State Diagrams
- [docs/ARCHITECTURE.md](file:///d:/projects/Smart%20Hospital%20Appointment%20and%20Patient%20Queue%20Management%20System/docs/ARCHITECTURE.md) — System Architecture & REST API Reference Table
- [docs/TEST_PLAN_AND_CASES.md](file:///d:/projects/Smart%20Hospital%20Appointment%20and%20Patient%20Queue%20Management%20System/docs/TEST_PLAN_AND_CASES.md) — Test Cases & Execution Matrix
- [docs/USER_MANUAL.md](file:///d:/projects/Smart%20Hospital%20Appointment%20and%20Patient%20Queue%20Management%20System/docs/USER_MANUAL.md) — Step-by-step role guides
- [docs/DEPLOYMENT_NOTES.md](file:///d:/projects/Smart%20Hospital%20Appointment%20and%20Patient%20Queue%20Management%20System/docs/DEPLOYMENT_NOTES.md) — Production setup & Nginx configuration
