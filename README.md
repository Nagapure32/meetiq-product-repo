# MeetIQ Productivity Platform

FastAPI backend and Next.js frontend for the MeetIQ productivity platform.

## Environment

Secrets and local configuration live in `.env`.

```text
.env
.env.example
```

`.env` is ignored by git. Keep real secrets there only. Use `.env.example` as the safe template for required variables.

Core variables:

```text
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_JWT_SECRET
DATABASE_URL
BOT_INTERNAL_API_KEY
MICROSOFT_TENANT_ID
MICROSOFT_CLIENT_ID
MICROSOFT_CLIENT_SECRET
TEAMS_BOT_BASE_URL
AZURE_SPEECH_KEY
AZURE_STORAGE_CONNECTION_STRING
```

## Apps

```text
backend/   FastAPI API
frontend/  Next.js app
docs/      Architecture and API contracts
```

## Backend

The backend scaffold is in `backend/`.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Initial API checks:

```text
GET /health
GET /api/v1/health
GET /internal/bot/calendar-users
```

Internal bot APIs require `BOT_INTERNAL_API_KEY`.

## Supabase

Setup steps are in:

```text
docs/supabase-setup.md
```
