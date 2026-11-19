# Developer Manual: Manual Testing Guide & End-to-End Walkthrough

## Project 25: Smart Hospital Appointment and Patient Queue Management System

This manual provides a step-by-step testing protocol for developers to test, verify, and demonstrate all features of the application from end to end using both the web UI and API endpoints.

---

## 1. Environment Setup & Starting the Servers

### 1.1 Prerequisites
- MySQL 8.0+ running on `127.0.0.1:3306`
- Python 3.11+ (in your virtual environment)
- Node.js 20+

### 1.2 Initialize the Database with Seed Data
Open a terminal in the project root:
```bash
# Windows PowerShell / CMD
Get-Content backend\database\schema.sql | mysql -u root -p
Get-Content backend\database\seed.sql | mysql -u root -p

# Linux / macOS
mysql -u root -p < backend/database/schema.sql
mysql -u root -p < backend/database/seed.sql
```

### 1.3 Verify `.env` File
Ensure you have a `.env` file at the root (copied from `.env.example`):
```ini
FLASK_ENV=development
SECRET_KEY=dev-secret-key
JWT_SECRET_KEY=dev-jwt-secret-key
HOSPITAL_TIMEZONE=Asia/Kolkata
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=hospital_queue_db
```

### 1.4 Start Backend Server (Terminal 1)
```bash
# Activate virtual environment
.\.venv\Scripts\activate   # Linux/macOS: source .venv/bin/activate

# Start the Flask API server (runs on http://127.0.0.1:5000)
python backend/run.py
```
> Verify health check: Open browser or curl `http://127.0.0.1:5000/api/health`. You should see `{"status": "ok", "database": "connected"}`.

### 1.5 Start Frontend Dev Server (Terminal 2)
```bash
cd frontend
npm run dev
```
> Open your browser at `http://127.0.0.1:5173`.

---

## 2. Seed Credentials Quick Reference

| Role | Email | Password | Default Landing Page |
| :--- | :--- | :--- | :--- |
| **Admin / Receptionist** | `admin@hospital.test` | `Admin@123` | `/admin` |
| **Doctor 1 (Cardiology)** | `doctor1@hospital.test` | `Doctor@123` | `/doctor` |
| **Doctor 2 (General Medicine)** | `doctor2@hospital.test` | `Doctor@123` | `/doctor` |
| **Doctor 3 (Orthopedics)** | `doctor3@hospital.test` | `Doctor@123` | `/doctor` |
| **Patient 1** | `patient1@hospital.test` | `Patient@123` | `/patient` |
| **Patient 2** | `patient2@hospital.test` | `Patient@123` | `/patient` |
| **Patient 3** | `patient3@hospital.test` | `Patient@123` | `/patient` |

---

## 3. Comprehensive Manual Testing Scenarios (Step-by-Step)

### Scenario 1: Authentication, Validation, and Route Guards
1. **Unauthenticated Access Protection**:
   - In an incognito tab, directly open `http://127.0.0.1:5173/patient`.
   - **Verification**: You must be automatically redirected to `/login`.
2. **Patient Self-Registration**:
   - Click **Create Patient Account** (or visit `/register`).
   - Try submitting with a 4-character password (`test`).
   - **Verification**: UI alert: *"Password must be at least 8 characters long."*
   - Enter full details:
     - Name: `Dev Tester`
     - Email: `devtester@hospital.test`
     - Phone: `9988776655`
     - Password: `Password@123`
   - Click **Create Patient Account**.
   - **Verification**: User is logged in and redirected to `/patient`. In the top navbar, you will see `Dev Tester (PATIENT)`.
3. **Role Guard Enforcement**:
   - While logged in as `Dev Tester` (PATIENT), try manually typing `http://127.0.0.1:5173/admin` into your browser address bar.
   - **Verification**: The route guard blocks access and redirects you back to `/patient`.
4. **Logout and Relogin**:
   - Click **Logout** in the navbar. You will be redirected to `/login`.
   - Log back in with `devtester@hospital.test` / `Password@123`.

---

### Scenario 2: Patient Booking & Slot Calculation
1. **Browse Doctors & Slots**:
   - On the **Patient Dashboard** (`/patient`), select:
     - Department: `Cardiology`
     - Doctor: `Dr. Aarav Sharma (DOC1)`
     - Date: Pick tomorrow's date.
   - **Verification**: The slots grid loads. You will see buttons like `09:00`, `09:15`, `09:30`, etc.
   - You should see `Effective Capacity: 12 | Remaining: 12`.
2. **Book an Available Slot**:
   - Click slot `09:00`.
   - Enter Reason: *"Heart palpitations"*.
   - Click **Confirm Online Booking**.
   - **Verification**:
     - Green success alert appears: *"Appointment booked! Token Number: DOC1-001 (Dr. Aarav Sharma at 09:00...)"*.
     - The slot button `09:00` turns disabled with `(Booked)`.
     - In **My Appointments** below, the new appointment is listed with status `BOOKED` and token `DOC1-001`.
3. **Duplicate Booking Prevention (Database Constraint Test)**:
   - Try clicking `09:00` again. Notice it is disabled.
   - Even if forced via API (`POST /api/appointments`), the backend will return `409 Conflict: Slot 09:00 is already booked`.

---

### Scenario 3: Walk-In Registration & Queue Board
1. **Admin Walk-In Booking**:
   - Logout and log in as `admin@hospital.test` / `Admin@123`. You land on `/admin`.
   - On the **Walk-in Registration** tab:
     - Doctor: `Dr. Aarav Sharma (DOC1)`
     - Patient Full Name: `Rajesh Sharma (Walk-In)`
     - Phone: `9876543299`
     - Leave **Slot Time** blank (to test automatic next-free-slot assignment).
     - Reason: *"Severe fever"*.
   - Click **Confirm Walk-in & Issue Token**.
   - **Verification**:
     - Success alert shows: *"Walk-in booked successfully! Token: DOC1-002 at 09:15"*.
     - Walk-ins are assigned initial status `CONFIRMED`.
2. **Reception Arrival Confirmation**:
   - Under **Today's Appointments** on the admin console, find token `DOC1-001` (status `BOOKED`).
   - Click **Confirm Arrival**.
   - **Verification**: Status transitions from `BOOKED` to `CONFIRMED`.
3. **Live Queue Board (Public Display)**:
   - In a separate browser tab, navigate to `http://127.0.0.1:5173/queue`.
   - Set the date filter to tomorrow (the date of the booked appointments).
   - **Verification**:
     - Under **Upcoming Patients**, both `DOC1-001` (09:00) and `DOC1-002` (09:15) appear with status `CONFIRMED`.
     - The top banner shows *"NOW CONSULTING: No token currently in consultation"*.

---

### Scenario 4: Doctor Queue Console & Consultation Lifecycle
1. **Doctor Console**:
   - Open another window or tab, log in as `doctor1@hospital.test` / `Doctor@123`. You land on `/doctor`.
   - Set the date picker to the appointment date.
   - **Verification**: You see `DOC1-001` and `DOC1-002` in the daily queue table.
2. **Calling the Next Patient**:
   - Click **Call Next Patient (DOC1-001)**.
   - **Verification**:
     - `DOC1-001` moves to the **Active Consultation** banner at the top with status `IN_CONSULTATION`.
     - Switch to the **Queue Board** tab: Notice within 6 seconds (polling), the top hero automatically updates to show **DOC1-001 | Rajesh Sharma / Dev Tester** as `NOW CONSULTING` in Room 101!
3. **Enforcing Single Consultation Guard**:
   - In the Doctor Console, while `DOC1-001` is still in consultation, try calling `DOC1-002`. Notice the Call button is hidden while another patient is active. If triggered via API, the backend returns `400 DOCTOR_BUSY`.
4. **Completing Consultation**:
   - Click **Mark Completed** on `DOC1-001`.
   - **Verification**:
     - `DOC1-001` status transitions to `COMPLETED`.
     - The Active Consultation card returns to empty state.
     - You can now call `DOC1-002`.

---

### Scenario 5: Rescheduling & Cancellation
1. **Rescheduling via API (or Patient/Admin action)**:
   - Open PowerShell or terminal:
   ```bash
   # Get JWT token for patient1
   $token = (curl -s -X POST http://127.0.0.1:5000/api/auth/login -H "Content-Type: application/json" -d '{"email":"patient1@hospital.test","password":"Patient@123"}' | ConvertFrom-Json).token

   # Reschedule appointment on the same date to slot 10:00 (keeps same token DOC1-001)
   curl -X PATCH http://127.0.0.1:5000/api/appointments/1/reschedule -H "Authorization: Bearer $token" -H "Content-Type: application/json" -d '{"doctor_id": 1, "appointment_date": "2026-11-20", "slot_time": "10:00"}'
   ```
   - **Verification**: The appointment slot moves to `10:00`, the old slot `09:00` is freed, and the token number remains `DOC1-001`.
2. **Cancellation**:
   ```bash
   curl -X POST http://127.0.0.1:5000/api/appointments/1/cancel -H "Authorization: Bearer $token" -H "Content-Type: application/json" -d '{"reason": "Cannot attend"}'
   ```
   - **Verification**: Status transitions to `CANCELLED`. In MySQL, `active_slot_key` becomes `NULL`, freeing the slot for new bookings. The token `DOC1-001` is retired and never assigned again.

---

### Scenario 6: Notification Audit Trail
1. **View Logs**:
   - Log in as `admin@hospital.test` / `Admin@123` and navigate to `/notifications`.
   - **Verification**:
     - You see an audit table containing all dispatched alerts (`BOOKING_CREATED`, `STATUS_UPDATED`, etc.).
     - Both `EMAIL` and `SMS` channels are logged.
     - Because external SMTP is unconfigured in development, `delivery_mode` correctly shows `SIMULATED` with the note *"SMTP_HOST not configured; simulated delivery"*, proving the application safely fallbacks without crashing.

---

### Scenario 7: Reports, Visual Analytics & CSV Export
1. **Analytics Dashboard**:
   - While logged in as `admin@hospital.test`, navigate to `/reports`.
   - Select the target date.
   - **Verification**:
     - Metric cards display **Total Appointments**, **Online Bookings**, and **Walk-In Bookings**.
     - **Status Doughnut Chart** displays status counts.
     - **Doctor Bar Chart** shows volume per doctor code (`DOC1`, `DOC2`, etc.).
     - **Hourly Distribution Line Chart** shows patient distribution over time.
2. **Download CSV Export**:
   - Click the **Download CSV Export** button.
   - **Verification**: A file named `daily_appointments_YYYY-MM-DD.csv` is downloaded. Open it in Excel, Notepad, or VS Code to confirm columns:
     `Appointment ID, Token Number, Patient Name, Doctor Name, Department, Slot Time, Booking Type, Status, Reason`.

---

## 4. Automated Sanity Check Commands for Developers

Before deploying or submitting any changes, execute this one-liner to verify all backend and frontend checks pass:

```bash
# 1. Run all 21 backend unit, concurrency, and integration tests
.\.venv\Scripts\pytest.exe -v

# 2. Run all frontend Vitest tests
npm --prefix frontend test

# 3. Test frontend production build
npm --prefix frontend run build
```

**Expected Result**:
- Pytest: `21 passed` (0 errors, 0 warnings)
- Vitest: `7 passed` across all component suites
- Vite Build: `✓ built in ~1.0s` without bundle errors
