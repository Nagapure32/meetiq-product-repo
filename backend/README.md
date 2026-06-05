# MeetIQ Backend

FastAPI backend for the MeetIQ productivity platform.

## Local Setup

From `productivity-platform/backend`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install pytest ruff
```

Run the API:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend reads environment variables from the repo root `.env` file.

## Initial Endpoints

```text
GET /health
GET /api/v1/health
GET /internal/bot/calendar-users
POST /internal/bot/heartbeats
POST /internal/bot/events
```

Internal bot endpoints require:

```http
Authorization: Bearer <BOT_INTERNAL_API_KEY>
```
