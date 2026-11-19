# Deployment Notes

## Project 25: Smart Hospital Appointment and Patient Queue Management System

---

## 1. Cloud Deployment on Render (Render PostgreSQL + Flask Web Service + React Static Site)

The repository includes a complete Render Blueprint ([render.yaml](file:///d:/projects/Smart%20Hospital%20Appointment%20and%20Patient%20Queue%20Management%20System/render.yaml)) and PostgreSQL 14+ SQL scripts ([backend/database/postgres_schema.sql](file:///d:/projects/Smart%20Hospital%20Appointment%20and%20Patient%20Queue%20Management%20System/backend/database/postgres_schema.sql) and [backend/database/postgres_seed.sql](file:///d:/projects/Smart%20Hospital%20Appointment%20and%20Patient%20Queue%20Management%20System/backend/database/postgres_seed.sql)).

### 1.1 Option A — One-Click Render Blueprint Deployment (`render.yaml`)

1. Push this repository to GitHub / GitLab.
2. In the [Render Dashboard](https://dashboard.render.com/), click **New +** -> **Blueprint**.
3. Connect your repository. Render automatically detects `render.yaml` at the repo root and provisions:
   - **`smart-hospital-db`** (Render PostgreSQL database `hospital_queue_db`)
   - **`smart-hospital-api`** (Python Flask Web Service running `gunicorn app:app --bind 0.0.0.0:$PORT` with `rootDir: backend` and health check `/api/health`)
   - **`smart-hospital-web`** (React Static Site built from `frontend` with `npm install && npm run build`, publishing `dist`, and client-side SPA routing rewrite `/* -> /index.html`)

### 1.2 Option B — Manual Render Service-by-Service Setup

#### Step 1: Create Render PostgreSQL Database
1. Click **New +** -> **PostgreSQL**.
2. Set:
   - **Name**: `smart-hospital-db`
   - **Database**: `hospital_queue_db`
   - **User**: `hospital_queue_user`
3. Copy the **Internal Database URL** (for the Render Web Service) and **External Database URL** (for running schema/seed from your local terminal).

#### Step 2: Load PostgreSQL Schema & Seed Data
Using `psql` with the **External Database URL** from Render:
```bash
psql "<EXTERNAL_DATABASE_URL>" -f backend/database/postgres_schema.sql
psql "<EXTERNAL_DATABASE_URL>" -f backend/database/postgres_seed.sql
```
*(Alternatively, open the Render Web Service **Shell** or connect via PGAdmin / DBeaver and execute `postgres_schema.sql` followed by `postgres_seed.sql`.)*

#### Step 3: Create Render Web Service (Flask Backend)
1. Click **New +** -> **Web Service** and select your repository.
2. Configure:
   - **Name**: `smart-hospital-api`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`
   - **Health Check Path**: `/api/health`
3. Add **Environment Variables**:

| Key | Value | Notes |
| :--- | :--- | :--- |
| `PYTHON_VERSION` | `3.11.9` | Python 3.11+ runtime |
| `FLASK_ENV` | `production` | Enables `ProductionConfig` |
| `DATABASE_URL` | `<Internal Database URL>` | Render `postgres://` or `postgresql://` URL (auto-normalized to `postgresql+psycopg2://`) |
| `SECRET_KEY` | `<strong-random-secret>` | Flask session secret |
| `JWT_SECRET_KEY` | `<strong-random-jwt-secret>` | PyJWT signing secret |
| `JWT_EXPIRY_HOURS` | `8` | 8-hour token validity |
| `HOSPITAL_TIMEZONE` | `Asia/Kolkata` | Authoritative hospital timezone |
| `CORS_ORIGINS` | `https://smart-hospital-web.onrender.com` | Your Render Static Site origin (or `*`) |
| `SMTP_HOST` | *(optional)* | Leave empty to use `SIMULATED` notification fallback |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USERNAME` | *(optional)* | SMTP username |
| `SMTP_PASSWORD` | *(optional)* | SMTP password |
| `SMTP_USE_TLS` | `true` | Enable STARTTLS |
| `SMTP_FROM` | `noreply@hospital.test` | Sender address |

#### Step 4: Create Render Static Site (React Frontend)
1. Click **New +** -> **Static Site** and select your repository.
2. Configure:
   - **Name**: `smart-hospital-web`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
3. Add **Environment Variable**:
   - `VITE_API_URL` = `https://<your-backend-service>.onrender.com/api`
4. Configure **Redirects / Rewrites** (for React Router SPA paths):
   - **Source**: `/*`
   - **Destination**: `/index.html`
   - **Action**: `Rewrite`
   *(Note: `frontend/public/_redirects` and `render.yaml` also include this rule automatically.)*

#### Step 5: Post-Deploy Verification Checklist
1. **Health Endpoint**: Open `https://<your-backend-service>.onrender.com/api/health` and confirm:
   ```json
   {
     "database": "connected",
     "service": "Smart Hospital Appointment and Patient Queue Management System",
     "status": "ok",
     "timezone": "Asia/Kolkata"
   }
   ```
2. **SPA Direct Route Refresh**: Navigate to `https://<your-static-site>.onrender.com/queue` and refresh the browser tab (`F5`) to confirm the `/* -> /index.html` rewrite rule prevents 404s.
3. **Seed Account Login**: Sign in at `/login` with `admin@hospital.test` / `Admin@123`, `doctor1@hospital.test` / `Doctor@123`, or `patient1@hospital.test` / `Patient@123`.
4. **Simulated Notifications**: Book a new appointment or register a walk-in and check `/notifications` to verify `SIMULATED` email and SMS logs are recorded without requiring an external SMTP server.

---

## 2. Local / Self-Hosted Setup (MySQL 8.0+ or PostgreSQL)

### 2.1 System Requirements
- **Operating System**: Linux (Ubuntu 22.04+ / Debian 12+), macOS, or Windows 10/11
- **Python**: Version 3.11 or higher
- **Node.js**: Version 20.x or 22.x LTS
- **Database**: PostgreSQL 14+ (via `DATABASE_URL`) or MySQL Server 8.0+ (InnoDB engine, `utf8mb4` character set)

### 2.2 Local MySQL 8.0+ Database Setup
1. Connect to your MySQL 8.0 instance and load the schema and seed data:
   ```bash
   mysql -u root -p < backend/database/schema.sql
   mysql -u root -p < backend/database/seed.sql
   ```

### 2.3 Local Backend Environment & Execution
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Install Python dependencies and start the server:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate
   pip install -r backend/requirements.txt
   python backend/run.py
   ```
   Or run with Gunicorn from inside `backend/`:
   ```bash
   cd backend
   gunicorn app:app --bind 0.0.0.0:5000
   ```

### 2.4 Local Frontend Build & Nginx Reverse Proxy
1. Build the static bundle:
   ```bash
   cd frontend
   npm install
   npm run build
   ```
2. Sample Nginx configuration for self-hosted Linux servers:
```nginx
server {
    listen 80;
    server_name hospital.example.com;

    root /var/www/hospital-queue/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:5000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```
