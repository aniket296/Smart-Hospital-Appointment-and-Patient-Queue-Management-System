# Deployment Notes

## Project 25: Smart Hospital Appointment and Patient Queue Management System

---

## 1. System Requirements

- **Operating System**: Linux (Ubuntu 22.04+ / Debian 12+), macOS, or Windows 10/11
- **Python**: Version 3.11 or higher
- **Node.js**: Version 20.x or 22.x LTS (compatible with 26.x)
- **Database**: MySQL Server 8.0+ (InnoDB engine, `utf8mb4` character set)
- **Web Server / Reverse Proxy**: Nginx or Apache (for production deployments)

---

## 2. MySQL Database Setup

1. Connect to your MySQL 8.0 instance:
   ```bash
   mysql -u root -p
   ```

2. Execute the schema script:
   ```sql
   SOURCE backend/database/schema.sql;
   ```

3. (Optional for development/staging) Load seed data:
   ```sql
   SOURCE backend/database/seed.sql;
   ```

---

## 3. Backend Environment & Execution

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Configure `.env` values:
   ```ini
   FLASK_ENV=production
   SECRET_KEY=generate-a-strong-random-secret
   JWT_SECRET_KEY=generate-a-strong-jwt-random-secret
   JWT_EXPIRY_HOURS=8
   HOSPITAL_TIMEZONE=Asia/Kolkata

   DB_HOST=127.0.0.1
   DB_PORT=3306
   DB_USER=hospital_app_user
   DB_PASSWORD=strong_password
   DB_NAME=hospital_queue_db
   TEST_DB_NAME=hospital_queue_test_db

   # SMTP Configuration (optional; defaults gracefully to simulated mode)
   SMTP_HOST=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USERNAME=apikey
   SMTP_PASSWORD=your_api_key
   SMTP_USE_TLS=true
   SMTP_FROM=noreply@hospital.example.com
   ```

3. Install Python dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate
   pip install -r backend/requirements.txt
   ```

4. Run the production WSGI server (e.g. Gunicorn):
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 backend.run:app
   ```

---

## 4. Frontend Build & Static Serving

1. Navigate to `frontend`:
   ```bash
   cd frontend
   npm install
   npm run build
   ```

2. The optimized production build is generated in `frontend/dist/`.
3. Configure Nginx to serve `frontend/dist/` and proxy `/api/` to `http://127.0.0.1:5000/api/`.

### Sample Nginx Configuration
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
