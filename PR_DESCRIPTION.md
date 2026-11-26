# Pull Request: Revert Cloud/Render Deployment and Restore Clean Local Development Mode

## Branch
`chore/revert-render-deployment-to-local` -> `main`

## Summary of Changes
This PR cancels cloud/Render deployment support for **Project 25: Smart Hospital Appointment and Patient Queue Management System (Simple Variant)** and restores the repository and configuration cleanly back to **local development mode**.

### 1. Removed Cloud Deployment Artifacts
- **Deleted `render.yaml`**: Removed Render Blueprint specification.
- **Deleted `frontend/public/_redirects`**: Removed cloud SPA rewrite file.
- **Deleted PostgreSQL Deployment Scripts**: Removed `backend/database/postgres_schema.sql` and `backend/database/postgres_seed.sql`.
- **Deleted Render Readiness Test**: Removed `backend/tests/test_render_postgres_readiness.py`.

### 2. Restored Backend & Database Configuration for Local Development
- **Dependencies (`backend/requirements.txt`)**: Removed deployment-only packages `gunicorn` and `psycopg2-binary`, keeping the clean local Flask + PyMySQL stack.
- **Config (`backend/app/config.py`)**: Restored standard local MySQL connection builder (`build_mysql_uri`), local test DB configuration, and clean CORS handling without cloud PostgreSQL URL rewriting.
- **Factory (`backend/app/__init__.py`)**: Cleaned up application factory and removed Render WSGI path workarounds.
- **Environment (`.env.example`)**: Restored straightforward local MySQL and Flask environment variables.

### 3. Restored Frontend Configuration
- **API Client (`frontend/src/api/client.js`)**: Restored direct `VITE_API_BASE_URL` fallback defaulting to `/api` for local development.
- **Environment (`frontend/.env.example`)**: Restored standard local development documentation.
- **Vitest Suite (`frontend/src/test/staff_and_queue.test.jsx`)**: Reverted Render URL resolution tests.

### 4. Updated Documentation
- **`README.md`**: Restored local quickstart focus with MySQL 8.0+, Python virtualenv, and Vite dev server commands.
- **`docs/DEPLOYMENT_NOTES.md`**: Restored self-hosted/Nginx and local WSGI setup guide.

---

## Verification & Test Results

### Backend Unit & Integration Tests (pytest)
- Ran: `.\.venv\Scripts\pytest.exe -v`
- **Result**: **21 passed** across all backend test modules (`test_auth.py`, `test_booking.py`, `test_queue.py`, `test_reschedule_cancel.py`, `test_notifications_reports.py`).

### Frontend Tests (Vitest)
- Ran: `npm --prefix frontend test`
- **Result**: **7 passed** across all UI suites.

### Frontend Production Build
- Ran: `npm --prefix frontend run build`
- **Result**: **Success** (zero errors).

---

## Local Startup Instructions

### 1. Database Setup
```bash
mysql -u root -p < backend/database/schema.sql
mysql -u root -p < backend/database/seed.sql
```

### 2. Backend Server
```bash
.\.venv\Scripts\activate
python backend/run.py
# Server running at: http://127.0.0.1:5000
```

### 3. Frontend Dev Server
```bash
cd frontend
npm install
npm run dev
# Vite dev server running at: http://127.0.0.1:5173
```
