from datetime import UTC, datetime
from typing import Any

from app.core.config import settings
from app.db.supabase import supabase_gateway


async def get_bot_health() -> dict[str, Any]:
    heartbeats = await _safe_get(
        "bot_heartbeats",
        {
            "select": "bot_instance_id,version,status,last_seen_at,payload",
            "order": "last_seen_at.desc",
            "limit": "1",
        },
    )
    events = await _safe_get(
        "bot_events",
        {
            "select": "id,event_type,severity,message,created_at",
            "order": "created_at.desc",
            "limit": "1",
        },
    )

    heartbeat = heartbeats[0] if heartbeats else None
    last_seen = _parse_datetime(heartbeat.get("last_seen_at")) if heartbeat else None
    age_seconds = int((datetime.now(UTC) - last_seen).total_seconds()) if last_seen else None

    return {
        "platform_api_configured": bool(settings.supabase_url and settings.supabase_service_role_key),
        "bot": {
            "status": _status_from_age(age_seconds),
            "bot_instance_id": heartbeat.get("bot_instance_id") if heartbeat else None,
            "version": heartbeat.get("version") if heartbeat else None,
            "last_seen_at": heartbeat.get("last_seen_at") if heartbeat else None,
            "age_seconds": age_seconds,
        },
        "latest_event": events[0] if events else None,
        "checks": [
            {
                "name": "Supabase database",
                "status": "connected" if settings.supabase_url else "missing_config",
            },
            {
                "name": "Microsoft Graph",
                "status": "configured"
                if settings.supabase_url
                else "pending",
            },
            {
                "name": "Teams bot heartbeat",
                "status": _status_from_age(age_seconds),
            },
        ],
    }


async def list_bot_events() -> list[dict[str, Any]]:
    return await _safe_get(
        "bot_events",
        {
            "select": "id,bot_instance_id,user_id,meeting_id,event_type,severity,message,payload,created_at",
            "order": "created_at.desc",
            "limit": "50",
        },
    )


async def _safe_get(path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        return await supabase_gateway.get(path, params=params)
    except Exception:
        return []


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _status_from_age(age_seconds: int | None) -> str:
    if age_seconds is None:
        return "not_connected"
    if age_seconds <= 180:
        return "online"
    if age_seconds <= 900:
        return "stale"
    return "offline"

