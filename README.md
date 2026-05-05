# Studentwellfare Backend

FastAPI backend for the Android-first student protection app.

## Stack

- FastAPI
- SQLAlchemy
- SQLite for local development
- `uv` for dependency and environment management

## Environment

Runtime values are loaded from [backend/.env](/home/azad/ddev/learning/studentwellfare/backend/.env:1).
Use [backend/.env.example](/home/azad/ddev/learning/studentwellfare/backend/.env.example:1) as the template.

Main keys:

- `APP_NAME`
- `DATABASE_URL`
- `BACKEND_CORS_ORIGINS`
- `SEED_PARENT_NAME`
- `SEED_PARENT_EMAIL`
- `SEED_PARENT_PASSWORD`
- `SEED_STUDENT_ID`
- `SEED_STUDENT_NAME`
- `SEED_ORGANIZATION_ID`
- `SEED_PAIRING_CODE`
- `ALERT_EMAIL_ENABLED`
- `ALERT_EMAIL_FROM`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `FCM_ENABLED`
- `FCM_SERVER_KEY`

## Local Run

```bash
cd backend
uv sync
uv run uvicorn studentwellfare_api.main:app --host 0.0.0.0 --port 8000 --reload
```

The API seeds the configured parent, student, and pairing code on startup if they do not already exist.

## Current Scope

- Parent login
- Pairing code creation and verification
- Device registration
- Student dashboard
- Rules fetch
- Device heartbeat
- Alert creation and list APIs
- Alert mark-as-read API

## Main Routes

- `POST /auth/login`
- `POST /pairing/create-code`
- `POST /pairing/verify-code`
- `GET /students/{student_id}/dashboard`
- `GET /students/{student_id}/alerts`
- `PATCH /alerts/{alert_id}/read`
- `POST /alerts`
- `POST /devices/{device_id}/heartbeat`
