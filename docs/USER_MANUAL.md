# User Manual

## Project 25: Smart Hospital Appointment and Patient Queue Management System

---

## 1. System Roles and Logins

| Role | Default Email | Password | Primary Console |
| :--- | :--- | :--- | :--- |
| **Administrator / Receptionist** | `admin@hospital.test` | `Admin@123` | `/admin`, `/queue`, `/reports` |
| **Doctor (Cardiology)** | `doctor1@hospital.test` | `Doctor@123` | `/doctor`, `/queue` |
| **Doctor (General Medicine)** | `doctor2@hospital.test` | `Doctor@123` | `/doctor`, `/queue` |
| **Doctor (Orthopedics)** | `doctor3@hospital.test` | `Doctor@123` | `/doctor`, `/queue` |
| **Patient 1** | `patient1@hospital.test` | `Patient@123` | `/patient`, `/queue`, `/notifications` |
| **Patient 2** | `patient2@hospital.test` | `Patient@123` | `/patient`, `/queue`, `/notifications` |
| **Patient 3** | `patient3@hospital.test` | `Patient@123` | `/patient`, `/queue`, `/notifications` |

---

## 2. Patient User Guide

### 2.1 Self-Registration
1. Navigate to `/register`.
2. Fill in your full name, valid email address, phone number, and a password with at least 8 characters.
3. Click **Create Patient Account**. You will be logged in and redirected to your **Patient Dashboard**.

### 2.2 Booking an Outpatient Appointment
1. In your **Patient Dashboard** (`/patient`):
   - Choose a department or select all departments.
   - Choose your preferred doctor.
   - Pick an appointment date (up to 30 days in advance).
   - Click an available time slot in the slot grid (e.g., `09:15`).
   - Enter an optional reason for visit (e.g., "Routine health review").
   - Click **Confirm Online Booking**.
2. A confirmation banner will display your issued sequential daily token number (e.g., `DOC1-002`).
3. Your appointment appears in your **My Appointments** table with status `BOOKED`.

### 2.3 Viewing Notifications and Tracking Queue
- Visit `/notifications` to review SMS and email confirmation receipts.
- Visit `/queue` to watch the real-time public queue board as doctors call patients into consultation.

---

## 3. Doctor User Guide

### 3.1 Managing Daily Clinic Queue
1. Log in with your doctor credentials (`doctor1@hospital.test` / `Doctor@123`).
2. You will be redirected to the **Doctor Console** (`/doctor`).
3. The top banner shows your currently active patient in consultation.
4. When ready for the next patient:
   - Click **Call Next Patient** (or click **Call** on the first `CONFIRMED` patient in the daily queue table).
   - The appointment transitions to `IN_CONSULTATION`.
5. When the consultation concludes:
   - Click **Mark Completed**. The status transitions to `COMPLETED` and the doctor's queue becomes ready for the next patient.
6. If a scheduled patient fails to appear on or after the appointment date:
   - Click **No Show** to record the terminal `NO_SHOW` status.

---

## 4. Administrator / Receptionist User Guide

### 4.1 Walk-In Patient Registration
1. In the **Admin Dashboard** (`/admin`), stay on the **Walk-in Registration** tab.
2. Select the assigned doctor.
3. Enter the patient's full name, phone number, and optional email.
4. Leave the slot time blank to auto-assign the next free slot at or after current hospital time, or specify a desired slot time (e.g., `10:30`).
5. Click **Confirm Walk-in & Issue Token**. The visit is registered with status `CONFIRMED`.

### 4.2 Confirming Online Booked Patients
1. Under **Today's Appointments** or the **All Appointments** tab:
2. When an online-booked patient arrives at reception, click **Confirm Arrival**.
3. Status changes to `CONFIRMED`, making them visible and callable in the doctor's active queue.

### 4.3 Managing Departments, Doctors, and Schedules
- **Departments tab**: Add new clinical departments with descriptions.
- **Doctors & Schedules tab**:
  - Add new doctors with unique doc codes (e.g., `DOC4`), room numbers, and default slot durations.
  - Configure weekday schedules (`0 = Monday ... 6 = Sunday`) with start/end times and daily patient capacity (`max_patients`).

### 4.4 Analytics and Daily Reports
1. Navigate to `/reports`.
2. Inspect KPI metric cards (Total Appointments, Online vs Walk-In).
3. View the **Status Doughnut Chart**, **Appointments per Doctor Bar Chart**, and **Hourly Distribution Line Chart**.
4. Click **Download CSV Export** to generate a spreadsheet file with all visit details.
