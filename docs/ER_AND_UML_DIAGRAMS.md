# ER and UML Diagrams

## Project 25: Smart Hospital Appointment and Patient Queue Management System

---

## 1. Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    USERS {
        int id PK
        varchar name
        varchar email UK
        varchar password_hash
        enum role "PATIENT, DOCTOR, ADMIN"
        boolean is_active
        datetime created_at
    }

    PATIENTS {
        int id PK
        int user_id FK, UK "Nullable for Walk-Ins"
        varchar full_name
        varchar phone
        varchar email
        date date_of_birth
        varchar gender
        datetime created_at
    }

    DEPARTMENTS {
        int id PK
        varchar name UK
        text description
    }

    DOCTORS {
        int id PK
        int user_id FK, UK
        int department_id FK
        varchar doc_code UK "e.g. DOC1"
        varchar specialization
        varchar room_number
        int default_slot_duration_minutes
        boolean is_active
    }

    DOCTOR_SCHEDULES {
        int id PK
        int doctor_id FK
        tinyint day_of_week "0=Mon .. 6=Sun"
        time start_time
        time end_time
        int slot_duration_minutes
        int max_patients
        boolean is_active
    }

    APPOINTMENTS {
        int id PK
        int patient_id FK
        int doctor_id FK
        date appointment_date
        time slot_time
        enum booking_type "ONLINE, WALK_IN"
        enum status "BOOKED, CONFIRMED, IN_CONSULTATION, COMPLETED, CANCELLED, NO_SHOW"
        varchar token_number
        varchar previous_token
        varchar reason
        int created_by_user_id FK
        datetime created_at
        datetime updated_at
        varchar active_slot_key UK "STORED generated column"
    }

    DOCTOR_TOKEN_COUNTERS {
        int doctor_id PK, FK
        date token_date PK
        int last_seq
    }

    APPOINTMENT_STATUS_HISTORY {
        int id PK
        int appointment_id FK
        varchar old_status
        varchar new_status
        int changed_by_user_id FK
        datetime changed_at
        varchar note
    }

    NOTIFICATION_LOGS {
        int id PK
        int user_id FK
        int patient_id FK
        int appointment_id FK
        enum channel "EMAIL, SMS"
        varchar event_type
        varchar recipient
        varchar subject
        text message
        enum delivery_mode "SMTP_SENT, SIMULATED"
        varchar status
        text error_message
        datetime created_at
    }

    USERS ||--o| PATIENTS : "has profile"
    USERS ||--o| DOCTORS : "has profile"
    DEPARTMENTS ||--o{ DOCTORS : "contains"
    DOCTORS ||--o{ DOCTOR_SCHEDULES : "configures"
    PATIENTS ||--o{ APPOINTMENTS : "books"
    DOCTORS ||--o{ APPOINTMENTS : "attends"
    USERS ||--o{ APPOINTMENTS : "created_by"
    DOCTORS ||--o{ DOCTOR_TOKEN_COUNTERS : "tracks daily seq"
    APPOINTMENTS ||--o{ APPOINTMENT_STATUS_HISTORY : "logs transitions"
    USERS ||--o{ APPOINTMENT_STATUS_HISTORY : "changed_by"
    APPOINTMENTS ||--o{ NOTIFICATION_LOGS : "triggers"
    PATIENTS ||--o{ NOTIFICATION_LOGS : "receives"
    USERS ||--o{ NOTIFICATION_LOGS : "receives"
```

---

## 2. Use-Case Overview Diagram

```mermaid
flowchart LR
    Patient["Patient Actor"]
    Doctor["Doctor Actor"]
    Admin["Admin / Receptionist Actor"]

    subgraph System["Smart Hospital Queue Management System"]
        UC1["Register & Login"]
        UC2["Browse Doctors & Available Slots"]
        UC3["Book Online Appointment"]
        UC4["Reschedule / Cancel Own Appointment"]
        UC5["View Live Polling Queue Board"]
        UC6["View Own Notifications"]
        UC7["Manage Doctor Queue & Consultation Status"]
        UC8["Manage Departments, Doctors & Schedules"]
        UC9["Register Walk-In & Auto-Assign Slot"]
        UC10["Confirm / Manage All Appointments"]
        UC11["View Daily Reports & Export CSV"]
    end

    Patient --> UC1
    Patient --> UC2
    Patient --> UC3
    Patient --> UC4
    Patient --> UC5
    Patient --> UC6

    Doctor --> UC1
    Doctor --> UC5
    Doctor --> UC7

    Admin --> UC1
    Admin --> UC2
    Admin --> UC5
    Admin --> UC8
    Admin --> UC9
    Admin --> UC10
    Admin --> UC11
```

---

## 3. Sequence Diagram: Online Booking & Token Issuance

```mermaid
sequenceDiagram
    actor P as Patient
    participant UI as React Frontend
    participant API as Flask API
    participant DB as MySQL 8.0
    participant NS as NotificationService

    P->>UI: Select Doctor, Date & Open Slot
    UI->>API: POST /api/appointments (doctor_id, appointment_date, slot_time, reason)
    API->>API: Validate JWT (PATIENT) & date/time in HOSPITAL_TIMEZONE
    API->>DB: BEGIN TRANSACTION
    API->>DB: Verify active schedule & check daily max_patients cap
    API->>DB: INSERT INTO doctor_token_counters ... ON DUPLICATE KEY UPDATE last_seq = last_seq + 1
    DB-->>API: Next sequence number (e.g. 4 -> DOC1-004)
    API->>DB: INSERT INTO appointments (status='BOOKED', token_number='DOC1-004')
    Note over DB: Unique index on active_slot_key guards against race conditions
    API->>DB: INSERT INTO appointment_status_history (NULL -> 'BOOKED')
    API->>DB: COMMIT
    API->>NS: send_booking_notification(appointment)
    NS->>DB: Log EMAIL (SMTP_SENT or SIMULATED) & SMS (SIMULATED)
    API-->>UI: 201 Created (appointment JSON with token DOC1-004)
    UI-->>P: Display Booking Confirmation & Token Number
```

---

## 4. Activity / State Diagram: Appointment Queue Lifecycle

```mermaid
stateDiagram-v2
    [*] --> BOOKED : Online Booking (Patient)
    [*] --> CONFIRMED : Walk-In Booking (Admin)

    BOOKED --> CONFIRMED : Admin confirms arrival
    BOOKED --> CANCELLED : Patient (own) or Admin cancels
    BOOKED --> NO_SHOW : Doctor (own) or Admin (on/after date)

    CONFIRMED --> IN_CONSULTATION : Doctor (own) or Admin calls token (max 1 active per doctor)
    CONFIRMED --> CANCELLED : Patient (own) or Admin cancels
    CONFIRMED --> NO_SHOW : Doctor (own) or Admin (on/after date)

    IN_CONSULTATION --> COMPLETED : Doctor (own) or Admin completes visit

    COMPLETED --> [*]
    CANCELLED --> [*]
    NO_SHOW --> [*]
```
