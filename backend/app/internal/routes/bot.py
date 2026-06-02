from fastapi import APIRouter, Depends

from app.internal.security import require_bot_api_key
from app.internal.schemas import (
    BotApprovalDecisionRequest,
    BotApprovalUpsertRequest,
    BotCalendarUser,
    BotEventRequest,
    BotHeartbeatRequest,
    BotMeetingStatusRequest,
    BotMeetingUpsertRequest,
    BotTranscriptRequest,
)
from app.services.approvals import upsert_bot_approval
from app.services.bot_calendar_users import list_enabled_calendar_users
from app.services.bot_events import record_bot_event, record_bot_heartbeat
from app.services.bot_reporting import (
    record_bot_approval_decision,
    record_bot_transcript,
    update_bot_meeting_status,
    upsert_bot_meeting,
)

router = APIRouter(dependencies=[Depends(require_bot_api_key)])


@router.get("/calendar-users", response_model=list[BotCalendarUser])
async def list_calendar_users() -> list[BotCalendarUser]:
    return await list_enabled_calendar_users()


@router.post("/heartbeats")
async def record_heartbeat(payload: BotHeartbeatRequest) -> dict[str, str]:
    received_at = await record_bot_heartbeat(payload)
    return {
        "status": "accepted",
        "bot_instance_id": payload.bot_instance_id,
        "received_at": received_at.isoformat(),
    }


@router.post("/events")
async def record_event(payload: BotEventRequest) -> dict[str, str]:
    received_at = await record_bot_event(payload)
    return {
        "status": "accepted",
        "event_type": payload.event_type,
        "received_at": received_at.isoformat(),
    }


@router.post("/meetings/upsert")
async def upsert_meeting(payload: BotMeetingUpsertRequest) -> dict[str, str]:
    row = await upsert_bot_meeting(payload)
    return {
        "status": "accepted",
        "meeting_id": row["id"],
    }


@router.post("/meetings/{meeting_id}/status")
async def update_meeting_status(
    meeting_id: str,
    payload: BotMeetingStatusRequest,
) -> dict[str, str]:
    row = await update_bot_meeting_status(meeting_id, payload)
    return {
        "status": "accepted",
        "meeting_id": row["id"],
    }


@router.post("/transcripts")
async def record_transcript(payload: BotTranscriptRequest) -> dict[str, str | int]:
    rows = await record_bot_transcript(payload)
    return {
        "status": "accepted",
        "meeting_id": payload.meeting_id,
        "segments_recorded": len(rows),
    }


@router.post("/approvals/upsert")
async def upsert_approval(payload: BotApprovalUpsertRequest) -> dict[str, str]:
    row = await upsert_bot_approval(payload)
    return {
        "status": "accepted",
        "approval_id": row["id"],
        "bot_approval_id": row["bot_approval_id"],
    }


@router.post("/approvals/{approval_id}/decision")
async def record_approval_decision(
    approval_id: str,
    payload: BotApprovalDecisionRequest,
) -> dict[str, str]:
    row = await record_bot_approval_decision(approval_id, payload)
    return {
        "status": "accepted",
        "approval_id": row["id"],
        "decision": row["status"],
    }
