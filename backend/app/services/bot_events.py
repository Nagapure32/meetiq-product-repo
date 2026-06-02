from datetime import UTC, datetime

from app.db.supabase import supabase_gateway
from app.internal.schemas import BotEventRequest, BotHeartbeatRequest


async def record_bot_heartbeat(payload: BotHeartbeatRequest) -> datetime:
    received_at = datetime.now(UTC)
    await supabase_gateway.upsert(
        "bot_heartbeats",
        {
            "bot_instance_id": payload.bot_instance_id,
            "version": payload.version,
            "status": payload.status,
            "last_seen_at": received_at.isoformat(),
            "payload": payload.payload,
        },
        on_conflict="bot_instance_id",
    )
    return received_at


async def record_bot_event(payload: BotEventRequest) -> datetime:
    received_at = datetime.now(UTC)
    await supabase_gateway.insert(
        "bot_events",
        {
            "bot_instance_id": payload.bot_instance_id,
            "user_id": payload.user_id,
            "meeting_id": payload.meeting_id,
            "event_type": payload.event_type,
            "severity": payload.severity,
            "message": payload.message,
            "payload": payload.payload,
            "created_at": received_at.isoformat(),
        },
    )
    return received_at

