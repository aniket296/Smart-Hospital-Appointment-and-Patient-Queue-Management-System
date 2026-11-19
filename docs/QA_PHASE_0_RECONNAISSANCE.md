# Phase 0 Reconnaissance & Coverage Inventory
## Project 25: Smart Hospital Appointment and Patient Queue Management System

**Target URL:** `http://127.0.0.1:5173` | **Backend API:** `http://127.0.0.1:5000/api` | **Environment:** Local

---

### 1. Routes & Pages Inventory

| Route Path | Page Name | Access Scope | Template Category |
| :--- | :--- | :--- | :--- |
| `/login` | Sign In Page | Public / Guest | Form / Auth Card |
| `/register` | Patient Self-Registration | Public / Guest | Form / Auth Card |
| `/queue` | Outpatient Live Queue Board | Public / Authenticated | Hero Serving Card + Real-Time Table |
| `/patient` | Patient Dashboard | Role: `PATIENT` | Multi-Column Dashboard (Booking Grid + Table) |
| `/doctor` | Doctor Console | Role: `DOCTOR` | Active Consultation Hero + Queue Table |
| `/admin` | Administration & Reception | Role: `ADMIN` | Tabbed Management (Walk-In, Appts, Doctors, Depts) |
| `/notifications` | Notification Logs | Role: `PATIENT`, `DOCTOR`, `ADMIN` | Audit Trail Table with Pagination |
| `/reports` | Analytics & Daily Reports | Role: `ADMIN` | KPI Cards + Chart.js Grid (Doughnut, Bar, Line) + CSV |
| `/*` (Fallback) | Role Home Redirect | Any | Dynamic Redirection |

---

### 2. Reusable Component Inventory

1. **Global Header & Navigation (`Navbar.jsx`)**:
   - Brand logo link
   - Role-conditional route links (`/queue`, `/patient`, `/doctor`, `/admin`, `/notifications`, `/reports`)
   - User profile badge (`Name (ROLE)`)
   - Auth buttons (Login/Register or Logout)
2. **Access Control Route Guard (`ProtectedRoute.jsx`)**:
   - Redirection to `/login` for unauthenticated visitors
   - Redirection to default role home for unauthorized roles
3. **Data Display Cards & Tables**:
   - KPI Summary Cards (`.card.text-center`)
   - Interactive Slot Selection Grid (`.slots-grid`, `.slot-btn`, `.slot-selected`, `.slot-disabled`)
   - Outpatient Live Queue Hero (`.current-serving-hero`, `.large-token`)
   - Responsive Data Tables (`.data-table`, `.table-responsive`)
   - Status Badges (`.status-badge`, `.status-booked`, `.status-confirmed`, `.status-in_consultation`, `.status-completed`, `.status-cancelled`, `.status-no_show`)
   - Token Badges (`.token-pill`, `.token-hero-badge`)
4. **Interactive Forms & Controls**:
   - Authentication forms with client & server-side validation error banners (`.alert-error`)
   - Success status alerts (`.alert-success`)
   - Walk-In patient registration form with optional slot auto-assignment
   - Doctor & schedule creation modal-style tab forms
   - Date pickers & department dropdown selectors
5. **Visual Chart Canvases (`ReportsPage.jsx`)**:
   - Chart.js Doughnut Chart (Appointment Status Breakdown)
   - Chart.js Bar Chart (Doctor Volume)
   - Chart.js Line Chart (Hourly Patient Arrival Flow)

---

### 3. Critical User Flows

- **Flow 1**: Patient Self-Registration -> Dashboard Arrival -> Slot Grid Selection -> Online Booking Confirmation (`DOC1-XXX`)
- **Flow 2**: Reception Walk-In Registration -> Auto-Slot Assignment -> Daily Queue Arrival Confirmation
- **Flow 3**: Doctor Consultation Queue -> Call Next Patient (`IN_CONSULTATION`) -> Mark Completed (`COMPLETED`) -> Live Queue Board Auto-Refresh
- **Flow 4**: Administrator Analytics -> Date Filtering -> KPI Review -> Chart Inspection -> CSV Export Download
- **Flow 5**: Notification Audit Trail -> Verification of `EMAIL` (SMTP / Simulated) and `SMS` (Simulated) alerts
